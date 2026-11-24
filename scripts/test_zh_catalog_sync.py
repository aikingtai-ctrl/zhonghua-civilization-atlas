"""Offline checks for the current gzip catalog format and mirror loader."""

import gzip
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse


SCRIPT = Path(__file__).with_name("sync_upstream.py")
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("zh_sync", SCRIPT)
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


def loader_source(scripts=("a.js?v=1", "b.js?v=2")):
    names = json.dumps(list(scripts), separators=(",", ":"))
    return (
        "(async()=>{try{const response=await fetch('catalog-base.json.gz?v=abc');"
        "if(!response.ok)throw Error('catalog failed');"
        f"for(const src of {names})await new Promise((resolve,reject)=>{{"
        "const script=document.createElement('script');script.src=src;"
        "script.onload=resolve;script.onerror=()=>reject(Error('脚本加载失败：'+src));"
        "document.body.append(script)});"
        "}catch(error){console.error(error)}})();"
    )


class CatalogSyncTests(unittest.TestCase):
    @staticmethod
    def upstream_fixture():
        record = {"id": "new", "title": "商代铜鼎", "era": "商", "category": "器物与工艺",
                  "date": "商", "evidence": "实物照片", "institutionShort": "馆藏", "imageUrl": "x.jpg"}
        script_a = b"window.a=true;"
        script_b = b"window.b=true;"
        ref_a = "a.js?v=" + hashlib.sha256(script_a).hexdigest()[:12]
        ref_b = "b.js?v=" + hashlib.sha256(script_b).hexdigest()[:12]
        loader = loader_source((ref_a, ref_b)).replace("catalog-base.json.gz?v=abc", "catalog-base.json.gz?v=123456789abc").encode("utf-8")
        loader_ref = "catalog-loader.js?v=" + hashlib.sha256(loader).hexdigest()[:12]
        html = ('<html><head></head><body><strong id="totalCount">—</strong>'
                '<span id="allCount">—</span><span id="resultCount">—</span>'
                '<div class="cards" id="cards"></div><div class="empty" id="empty"></div>'
                '<button id="loadMore" class="load-more">继续浏览</button>'
                f'<script src="{loader_ref}"></script></body></html>')
        return {
            "index.html": html.encode("utf-8"),
            "catalog-loader.js": loader,
            "catalog-base.json.gz": gzip.compress(json.dumps({"records": [record]}).encode("utf-8")),
            "a.js": script_a,
            "b.js": script_b,
            "site-version.json": b'{}',
            "publication-proofs/build-report.json": b'{}',
        }

    @staticmethod
    def run_fake_sync(root, payloads):
        def fake_fetch(url, **_kwargs):
            rel = urlparse(url).path.lstrip("/") or "index.html"
            return (200, payloads[rel]) if rel in payloads else (404, b"")
        with mock.patch.object(SYNC, "fetch_bytes", side_effect=fake_fetch), \
             mock.patch.object(SYNC, "git_prepare_repo"), \
             mock.patch.object(SYNC, "git_push_if_changed", return_value=[]), \
             mock.patch.object(SYNC, "_probe_zhonghua_catalog_asset", return_value="123"), \
             mock.patch.object(SYNC.urllib.request, "urlopen", side_effect=OSError("offline")):
            return SYNC.sync_zhonghua(root, auto_push=False)

    def test_discovers_gzip_and_scripts_and_rejects_unsafe_reference(self):
        base, scripts = SYNC.zh_catalog_loader_dependencies(loader_source())
        self.assertEqual(base, "catalog-base.json.gz")
        self.assertEqual(scripts, ["a.js", "b.js"])
        with self.assertRaisesRegex(ValueError, "unsafe"):
            SYNC.zh_catalog_loader_dependencies(loader_source(("../outside.js",)))

    def test_parallel_loader_keeps_order_and_exposes_readiness(self):
        patched = SYNC.optimize_zh_catalog_loader(loader_source().encode("utf-8"))
        text = patched.decode("utf-8")
        self.assertIn("script.async=false", text)
        self.assertIn("await Promise.all(__jtLoads)", text)
        self.assertIn("window.__JT_CATALOG_READY__=", text)
        self.assertEqual(SYNC.optimize_zh_catalog_loader(patched), patched)
        self.assertEqual(SYNC.zh_catalog_loader_dependencies(text)[1], ["a.js", "b.js"])
        syntax = subprocess.run(["node", "--check"], input=patched, capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr.decode("utf-8", "replace"))
        with self.assertRaisesRegex(ValueError, "unknown"):
            SYNC.optimize_zh_catalog_loader(loader_source().replace("await new Promise", "await loadOne").encode())

    def test_parallel_loader_handles_out_of_order_responses(self):
        patched = SYNC.optimize_zh_catalog_loader(loader_source().encode("utf-8")).decode("utf-8")
        harness = r"""
const vm=require('vm');
const source=process.argv[1];
const appended=[], responses=[], executed=[], ready=new Set();
let next=0;
function execute(script){executed.push(script.src);script.onload();}
function drain(){while(next<appended.length&&ready.has(appended[next].src))execute(appended[next++]);}
const document={
  createElement(){return {async:true};},
  body:{append(script){
    appended.push(script);
    setTimeout(()=>{
      responses.push(script.src);
      if(script.async)execute(script);else{ready.add(script.src);drain();}
    },script.src.startsWith('a.')?25:1);
  }}
};
const context={window:{},document,fetch:async()=>({ok:true}),console};
vm.createContext(context);
vm.runInContext(source,context);
(async()=>{
  await new Promise(setImmediate);
  if(appended.length!==2)throw Error('requests were serialized');
  await context.window.__JT_CATALOG_READY__;
  if(responses.join(',')!=='b.js?v=2,a.js?v=1')throw Error('response order was not reversed');
  if(executed.join(',')!=='a.js?v=1,b.js?v=2')throw Error('execution order changed');
  console.log('parallel requests; reversed responses; ordered execution');
})().catch(e=>{console.error(e);process.exitCode=1});
"""
        run = subprocess.run(["node", "-e", harness, patched], capture_output=True, text=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("ordered execution", run.stdout)

    def test_missing_or_corrupt_dependency_cannot_pass_validation(self):
        with tempfile.TemporaryDirectory(prefix="zh-catalog-sync-") as tmp:
            root = Path(tmp)
            source = loader_source()
            (root / "catalog-loader.js").write_text(source, encoding="utf-8")
            (root / "catalog-base.json.gz").write_bytes(gzip.compress(b'{"records":[]}'))
            for name in ("a.js", "b.js"):
                (root / name).write_text("window.ok=true;", encoding="utf-8")
            fetched = {"catalog-loader.js", "catalog-base.json.gz", "a.js", "b.js"}
            self.assertEqual(SYNC.validate_zh_catalog_downloads(root, source, fetched), 2)
            with self.assertRaisesRegex(RuntimeError, "b.js"):
                SYNC.validate_zh_catalog_downloads(root, source, fetched - {"b.js"})
            (root / "catalog-base.json.gz").write_bytes(b"truncated")
            with self.assertRaisesRegex(RuntimeError, "invalid"):
                SYNC.validate_zh_catalog_downloads(root, source, fetched)

    def test_discovers_images_inside_gzip_catalog(self):
        payload = {"records": [
            {"localImage": "assets/new-artifact.webp", "previewUrl": "research-western-zhou/images/front.jpg"},
            {"localImage": "https://museum.example/images/remote.jpg", "previewUrl": "assets/second.png?v=2"},
        ]}
        found = SYNC.discover_zh_catalog_media(gzip.compress(json.dumps(payload).encode("utf-8")))
        self.assertEqual(found, {"assets/new-artifact.webp", "research-western-zhou/images/front.jpg", "assets/second.png"})

    def test_new_gzip_catalog_wins_over_stale_legacy_data(self):
        with tempfile.TemporaryDirectory(prefix="zh-catalog-ssg-") as tmp:
            root = Path(tmp)
            (root / "index.html").write_text('<script src="catalog-loader.js"></script>', encoding="utf-8")
            (root / "catalog-loader.js").write_text(loader_source(), encoding="utf-8")
            (root / "data.js").write_text('window.ARCHIVE_DATA={records:[{"id":"old"}]}', encoding="utf-8")
            record = {"id": "new", "title": "商代铜鼎", "era": "商", "category": "器物与工艺",
                      "date": "商", "evidence": "实物照片", "institutionShort": "馆藏", "imageUrl": "x.jpg"}
            (root / "catalog-base.json.gz").write_bytes(gzip.compress(json.dumps({"records": [record]}).encode("utf-8")))
            payload = SYNC._compute_zhonghua_ssg_payload(root)
            self.assertEqual(payload["total"], 1)
            self.assertIn("商代铜鼎", payload["cardsHtml"])
            self.assertNotIn("old", payload["cardsHtml"])

    def test_site_optimizer_uses_new_snapshot_and_waits_for_catalog(self):
        with tempfile.TemporaryDirectory(prefix="zh-catalog-build-") as tmp:
            root = Path(tmp)
            html = ('<html><body><strong id="totalCount">—</strong><span id="allCount">—</span>'
                    '<span id="resultCount">—</span><div class="cards" id="cards"></div>'
                    '<div class="empty" id="empty"></div>'
                    '<button id="loadMore" class="load-more">继续浏览</button>'
                    '<script src="catalog-loader.js"></script></body></html>')
            (root / "index.html").write_text(html, encoding="utf-8")
            (root / "catalog-loader.js").write_text(loader_source(), encoding="utf-8")
            (root / "data.js").write_text('window.ARCHIVE_DATA={records:[{"id":"old"}]}', encoding="utf-8")
            record = {"id": "new", "title": "商代铜鼎", "era": "商", "category": "器物与工艺",
                      "date": "商", "evidence": "实物照片", "institutionShort": "馆藏", "imageUrl": "x.jpg"}
            (root / "catalog-base.json.gz").write_bytes(gzip.compress(json.dumps({"records": [record]}).encode("utf-8")))
            result = SYNC.optimize_zhonghua_site(root)
            built = (root / "index.html").read_text(encoding="utf-8")
            self.assertEqual(result["ssg_records"], 1)
            self.assertIn("商代铜鼎", built)
            self.assertIn("await window.__JT_CATALOG_READY__", built)
            self.assertNotIn('data-all="[&quot;data.js', built)
            self.assertIn("script.async=false", (root / "catalog-loader.js").read_text(encoding="utf-8"))

    def test_sync_discovers_loader_dependencies_and_builds(self):
        with tempfile.TemporaryDirectory(prefix="zh-catalog-sync-full-") as tmp:
            root = Path(tmp)
            self.run_fake_sync(root, self.upstream_fixture())
            self.assertTrue((root / "catalog-base.json.gz").is_file())
            self.assertTrue((root / "a.js").is_file())
            self.assertTrue((root / "b.js").is_file())
            built = (root / "index.html").read_text(encoding="utf-8")
            self.assertIn("商代铜鼎", built)
            self.assertIn("await window.__JT_CATALOG_READY__", built)

    def test_sync_rejects_missing_current_script_even_with_stale_local_copy(self):
        with tempfile.TemporaryDirectory(prefix="zh-catalog-sync-missing-") as tmp:
            root = Path(tmp)
            (root / "b.js").write_text("stale", encoding="utf-8")
            payloads = self.upstream_fixture()
            del payloads["b.js"]
            with self.assertRaisesRegex(RuntimeError, "b.js"):
                self.run_fake_sync(root, payloads)
            self.assertFalse((root / ".sync_state.json").exists())


if __name__ == "__main__":
    unittest.main()
