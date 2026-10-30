# -*- coding: utf-8 -*-
"""
金泰四大文化与视听资源库 · 全自动增量同步引擎（支持本地常驻守护 / 手动一键同步 / GitHub Actions 云端定时同步）
用法:
  python sync_all_4_sites.py                # 同步全部 4 个网站（本地全套仓库）并自动推送到 GitHub Pages + 刷新国内 CDN 缓存
  python sync_all_4_sites.py --only shengcang --repo-dir .   # 单仓模式（供 GitHub Actions 在各自仓库内每 30 分钟自动调用）
  python sync_all_4_sites.py --only documentary --repo-dir .
  python sync_all_4_sites.py --only zhonghua --repo-dir .
"""
import argparse
import concurrent.futures
import hashlib
import http.client
import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

if getattr(sys, "stdout", None) is not None and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GATE_HASH = "6e95ff3e55611d24803014d9de77b401f191f198f9372577e58f9aa2e51771d3"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
CF_CHALLENGE_RE = re.compile(r"<script>\(function\(\)\{function c\(\)\{var b=a\.contentDocument.*?__CF\$cv\$params.*?</script>", re.S)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def strip_cf_challenge(html_text: str) -> str:
    return CF_CHALLENGE_RE.sub("", html_text)


def fetch_bytes(url: str, retries: int = 3, timeout: int = 25):
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404, 410):
                return e.code, b""
            if attempt == retries - 1:
                return e.code, b""
            time.sleep(0.4 * (attempt + 1))
        except Exception:
            if attempt == retries - 1:
                return 0, b""
            time.sleep(0.5 * (attempt + 1))
    return 0, b""


def make_gate_script(site_title: str) -> str:
    safe_title = site_title.replace("'", "\\'")
    js = f"""(function(){{
var H='{GATE_HASH}';
var k='jt_gate';
function getSaved(){{
  try{{if(localStorage.getItem(k)===H)return true;}}catch(e){{}}
  try{{if(sessionStorage.getItem(k)===H)return true;}}catch(e){{}}
  return false;
}}
function saveOk(){{
  try{{localStorage.setItem(k,H);}}catch(e){{}}
  try{{sessionStorage.setItem(k,H);}}catch(e){{}}
}}
if(getSaved()){{
  document.documentElement.setAttribute('data-jt-ok','1');
  return;
}}
window.__JT_LOCKED__=true;
var st=document.createElement('style');
st.id='jt_gate_css';
st.textContent='html:not([data-jt-ok="1"]) body{{display:none!important}}';
document.documentElement.appendChild(st);
document.documentElement.style.visibility='hidden';
var obs=null;
if(typeof MutationObserver!=='undefined'){{
  obs=new MutationObserver(function(muts){{
    for(var i=0;i<muts.length;i++){{
      var ns=muts[i].addedNodes;
      for(var j=0;j<ns.length;j++){{
        var n=ns[j];
        if(!n||!n.tagName)continue;
        var tg=n.tagName.toUpperCase();
        if(tg==='SCRIPT'&&n.id!=='jt-unified-gate'){{
          n.type='javascript/blocked';
          if(n.hasAttribute('src'))n.removeAttribute('src');
          if(n.parentNode)n.parentNode.removeChild(n);
        }}else if(tg==='LINK'&&/preload/i.test(n.getAttribute('rel')||'')){{
          if(n.parentNode)n.parentNode.removeChild(n);
        }}
      }}
    }}
  }});
  obs.observe(document.documentElement,{{childList:true,subtree:true}});
}}
function shaPure(ascii){{
  function rr(v,a){{return(v>>>a)|(v<<(32-a));}}
  var bytes=[],i,j;
  if(typeof TextEncoder!=='undefined'){{
    bytes=Array.from(new TextEncoder().encode(ascii));
  }}else{{
    for(i=0;i<ascii.length;i++){{
      var c=ascii.charCodeAt(i);
      if(c<128)bytes.push(c);
      else if(c<2048)bytes.push(192|(c>>6),128|(c&63));
      else bytes.push(224|(c>>12),128|((c>>6)&63),128|(c&63));
    }}
  }}
  var bitLen=bytes.length*8;
  bytes.push(0x80);
  while((bytes.length%64)!==56)bytes.push(0);
  var hi=Math.floor(bitLen/4294967296),lo=bitLen>>>0;
  bytes.push((hi>>>24)&255,(hi>>>16)&255,(hi>>>8)&255,hi&255,(lo>>>24)&255,(lo>>>16)&255,(lo>>>8)&255,lo&255);
  var K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
  var H0=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
  for(i=0;i<bytes.length;i+=64){{
    var W=new Array(64);
    for(j=0;j<16;j++)W[j]=((bytes[i+j*4]<<24)|(bytes[i+j*4+1]<<16)|(bytes[i+j*4+2]<<8)|bytes[i+j*4+3])>>>0;
    for(j=16;j<64;j++){{
      var s0=rr(W[j-15],7)^rr(W[j-15],18)^(W[j-15]>>>3);
      var s1=rr(W[j-2],17)^rr(W[j-2],19)^(W[j-2]>>>10);
      W[j]=(W[j-16]+s0+W[j-7]+s1)>>>0;
    }}
    var a=H0[0],b=H0[1],c=H0[2],d=H0[3],e=H0[4],f=H0[5],g=H0[6],h=H0[7];
    for(j=0;j<64;j++){{
      var S1=rr(e,6)^rr(e,11)^rr(e,25),ch=(e&f)^((~e)&g),t1=(h+S1+ch+K[j]+W[j])>>>0;
      var S0=rr(a,2)^rr(a,13)^rr(a,22),maj=(a&b)^(a&c)^(b&c),t2=(S0+maj)>>>0;
      h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;
    }}
    H0[0]=(H0[0]+a)>>>0;H0[1]=(H0[1]+b)>>>0;H0[2]=(H0[2]+c)>>>0;H0[3]=(H0[3]+d)>>>0;
    H0[4]=(H0[4]+e)>>>0;H0[5]=(H0[5]+f)>>>0;H0[6]=(H0[6]+g)>>>0;H0[7]=(H0[7]+h)>>>0;
  }}
  return H0.map(function(x){{return('00000000'+x.toString(16)).slice(-8);}}).join('');
}}
async function sha(s){{
  try{{
    if(window.crypto&&crypto.subtle&&typeof TextEncoder!=='undefined'){{
      var b=new TextEncoder().encode(s);
      var d=await crypto.subtle.digest('SHA-256',b);
      return Array.from(new Uint8Array(d)).map(function(x){{return x.toString(16).padStart(2,'0');}}).join('');
    }}
  }}catch(e){{}}
  return shaPure(s);
}}
function lockDom(){{
  if(obs){{try{{obs.disconnect();}}catch(e){{}}obs=null;}}
  document.querySelectorAll('script[src]').forEach(function(s){{
    s.onload=s.onerror=null;
    if(s.parentNode)s.parentNode.removeChild(s);
  }});
  if(!document.body){{
    var bd=document.createElement('body');
    document.documentElement.appendChild(bd);
  }}
  document.body.className='';
  document.body.style.cssText='margin:0;background:#f4f2ed;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px';
  document.body.innerHTML='<div id="jt_lock_box" style="font:19pt/1.65 Microsoft YaHei,PingFang SC,sans-serif;padding:36px 26px;color:#1d3338;width:min(680px,100%);background:#fff;border:2px solid #284b45;border-radius:14px;text-align:center;box-shadow:0 10px 28px rgba(0,0,0,.08)"><div style="font-size:22.5pt;font-weight:bold;color:#1d3338;margin-bottom:10px">{safe_title}</div><div style="font-size:15.5pt;color:#4a5d54;margin-bottom:22px">请输入统一访问密码进入系统（手机微信 / 浏览器验证一次，四站自动通用）</div><div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;max-width:500px;margin:0 auto"><input id="jt_pw_box" type="password" placeholder="请输入访问密码" autocomplete="current-password" style="flex:1;min-width:210px;font:17pt Microsoft YaHei,sans-serif;padding:11px 14px;border:1.5px solid #6f857b;border-radius:8px;background:#fff;color:#263a40"><button id="jt_pw_btn" type="button" style="font:bold 17pt Microsoft YaHei,sans-serif;padding:11px 26px;background:#284b45;color:#fff;border:none;border-radius:8px;cursor:pointer">验证进入</button></div><div id="jt_pw_err" style="font-size:15pt;color:#8a1c1c;min-height:28px;margin-top:12px"></div></div>';
  document.documentElement.setAttribute('data-jt-ok','1');
  document.documentElement.style.visibility='visible';
  var inp=document.getElementById('jt_pw_box'),btn=document.getElementById('jt_pw_btn'),err=document.getElementById('jt_pw_err');
  async function tryIn(){{
    var v=(inp.value||'').trim();
    if(!v){{err.textContent='请输入访问密码';return;}}
    var h=await sha(v);
    if(h===H){{saveOk();location.reload();}}
    else{{err.textContent='密码不正确，请核对后重试';inp.value='';inp.focus();}}
  }}
  if(btn)btn.onclick=tryIn;
  if(inp){{
    inp.onkeydown=function(e){{if(e.key==='Enter')tryIn();}};
    setTimeout(function(){{try{{inp.focus();}}catch(e){{}}}},60);
  }}
}}
if(document.readyState==='loading'){{
  document.addEventListener('DOMContentLoaded',lockDom,{{once:true}});
}}else{{
  lockDom();
}}
}})();"""
    return f'<script id="jt-unified-gate">{js}</script>'


def check_html_js_syntax(html_path: Path):
    txt = html_path.read_text(encoding="utf-8")
    for m in re.finditer(r"(<script(?![^>]*\bsrc=)[^>]*>)(.*?)</script>", txt, re.S | re.I):
        tag, code = m.group(1), m.group(2)
        if "json" in tag.lower() or "importmap" in tag.lower() or not code.strip():
            continue
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
            tf.write(code)
            tp = tf.name
        r = subprocess.run(["node", "--check", tp], capture_output=True, text=True)
        Path(tp).unlink(missing_ok=True)
        if r.returncode != 0:
            raise RuntimeError(f"JS syntax error in {html_path}: {r.stderr}")


def patch_vite_preload_js(js_text: str) -> str:
    js_text = re.sub(
        r'function\s*\(([A-Za-z_$][\w$]*)\)\s*\{\s*return\s*["\']\/["\']\s*\+\s*\1\s*\}',
        r'function(\1){return(window.__JT_BASE__||"./")+\1}',
        js_text,
    )
    js_text = re.sub(
        r'\(\s*([A-Za-z_$][\w$]*)\s*\)\s*=>\s*["\']\/["\']\s*\+\s*\1\b',
        r'(\1)=>(window.__JT_BASE__||"./")+\1',
        js_text,
    )
    js_text = re.sub(
        r'\(\s*([A-Za-z_$][\w$]*)\s*\)\s*=>\s*`\/\$\{\1\}`',
        r'(\1)=>`${window.__JT_BASE__||"./"}${\1}`',
        js_text,
    )
    return js_text


def discover_and_download_vinext_assets(base_url: str, html_text: str, site_dir: Path):
    queue = set()
    for m in re.findall(r'["\'](/(?:_next/static|images)/[^"\'\\?#]+|/favicon\.[A-Za-z0-9]+)', html_text):
        queue.add(m)
    downloaded = set()
    while queue:
        batch = sorted(queue - downloaded)
        if not batch:
            break
        def dl_one(rel):
            url = base_url + urllib.parse.quote(rel, safe="/:@!$&'()*+,;=-._~")
            st, data = fetch_bytes(url)
            return rel, st, data
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
            for rel, st, data in ex.map(dl_one, batch):
                downloaded.add(rel)
                if st != 200:
                    continue
                local_p = site_dir / rel.lstrip("/")
                local_p.parent.mkdir(parents=True, exist_ok=True)
                if rel.endswith(".js"):
                    jt = data.decode("utf-8", errors="ignore")
                    for dep in re.findall(r'["\'](_next/static/[^"\'\\?#]+)["\']', jt):
                        queue.add("/" + dep)
                    cur_dir = os.path.dirname(rel).replace("\\", "/")
                    for sib in re.findall(r'(?:from|import)\s*\(?[`"\'](\./[^`"\'\\?#]+)[`"\']', jt):
                        norm = os.path.normpath(cur_dir + "/" + sib).replace("\\", "/")
                        if not norm.startswith("/"):
                            norm = "/" + norm
                        queue.add(norm)
                    for img in re.findall(r'[`"\'](/images/[^`"\'\\?#]+)[`"\']', jt):
                        queue.add(img)
                    jt_patched = patch_vite_preload_js(jt)
                    # Also rewrite "/images/xxx.png" to relative "./images/xxx.png" inside JS bundles
                    jt_patched = re.sub(r'(["\'])/images/([^"\']+\.(?:png|jpg|jpeg|webp|svg))', r'\1./images/\2', jt_patched)
                    local_p.write_bytes(jt_patched.encode("utf-8"))
                elif rel.endswith(".css"):
                    ct = data.decode("utf-8", errors="ignore")
                    for u in re.findall(r'url\(["\']?(/(?:_next/static|images|fonts)/[^"\')?#]+)', ct):
                        queue.add(u)
                    local_p.write_bytes(data)
                else:
                    local_p.write_bytes(data)


def rewrite_vinext_html(html_text: str, gate_tag: str, shim_tag: str) -> str:
    out = strip_cf_challenge(html_text)
    out = out.replace('"/_next/static/', '"./_next/static/')
    out = out.replace("'/_next/static/", "'./_next/static/")
    out = out.replace('\\"/_next/static/', '\\"./_next/static/')
    out = out.replace('href="/favicon.svg"', 'href="./favicon.svg"')
    out = out.replace('"/images/', '"./images/')
    out = out.replace('\\"/images/', '\\"./images/')
    out = out.replace('"/collection-workflow.md"', '"./collection-workflow.md"')
    out = out.replace('\\"/collection-workflow.md\\"', '\\"./collection-workflow.md\\"')
    out = out.replace('"/reconciliation-template.csv"', '"./reconciliation-template.csv"')
    out = out.replace('\\"/reconciliation-template.csv\\"', '\\"./reconciliation-template.csv\\"')
    m = re.search(r"<head\b[^>]*>", out, flags=re.I)
    if not m:
        raise RuntimeError("Missing <head> in HTML")
    return out[:m.end()] + gate_tag + shim_tag + out[m.end():]


def purge_jsdelivr(repo_name: str, rel_paths: list[str]):
    for rp in rel_paths[:20]:
        u = f"https://purge.jsdelivr.net/gh/aikingtai-ctrl/{repo_name}@main/{rp.lstrip('/')}"
        try:
            urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=8).read()
        except Exception:
            pass


def git_push_if_changed(repo_dir: Path, repo_name: str, msg: str, auto_push: bool) -> list[str]:
    if not (repo_dir / ".git").is_dir():
        return []
    subprocess.run(["git", "add", "-A"], cwd=str(repo_dir), check=True)
    st = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo_dir), capture_output=True, text=True, check=True)
    lines = [ln.strip() for ln in st.stdout.splitlines() if ln.strip()]
    if not lines:
        return []
    changed_files = [ln.split(None, 1)[-1].strip('"') for ln in lines]
    if auto_push:
        subprocess.run(["git", "commit", "-m", msg], cwd=str(repo_dir), check=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=str(repo_dir), capture_output=True)
        subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=str(repo_dir), check=True, timeout=300)
        purge_jsdelivr(repo_name, changed_files)
    return changed_files


# ------------------------------------------------------------------------------
# 1. Shengcang Incremental Sync
# ------------------------------------------------------------------------------
SC_SHIM = """<style>a[href*="signin-with-chatgpt"]{display:none!important}</style><script id="jintai-shengcang-shim">(function(){
var BASE=new URL('.',location.href).pathname;if(BASE.slice(-1)!=='/')BASE+='/';window.__JT_BASE__=BASE;
var IS_GH=/github\\.io$/i.test(location.hostname||'');
var CDNS=['https://testingcf.jsdelivr.net/gh/aikingtai-ctrl/shengcang-sound-library@main/','https://gcore.jsdelivr.net/gh/aikingtai-ctrl/shengcang-sound-library@main/'];
function resolveMedia(rel){if(!rel||typeof rel!=='string')return rel;var clean=rel.replace(/^\\.\\//,'').replace(/^\\//,'');if(!/^(audio|images)\\//.test(clean))return rel;return IS_GH?(CDNS[0]+clean):(BASE+clean);}
window.addEventListener('error',function(ev){var el=ev.target;if(!el||!el.tagName)return;var tag=el.tagName.toUpperCase();if(tag!=='AUDIO'&&tag!=='SOURCE'&&tag!=='IMG')return;var cur=el.getAttribute('src')||el.src||'';var m=cur.match(/(?:shengcang-sound-library@main\\/|\\/)((?:audio|images)\\/[^?#]+)/);if(!m)return;var clean=m[1];var step=parseInt(el.getAttribute('data-jt-fb')||'0',10);var cands=IS_GH?[CDNS[1]+clean,BASE+clean]:[CDNS[0]+clean,CDNS[1]+clean];if(step<cands.length){el.setAttribute('data-jt-fb',String(step+1));el.src=cands[step];if(tag==='AUDIO'&&typeof el.load==='function')el.load();}},true);
document.addEventListener('click',function(ev){var a=ev.target&&ev.target.closest?ev.target.closest('a'):null;if(!a)return;var hr=a.getAttribute('href')||'';if(hr.indexOf('signin-with-chatgpt')!==-1){ev.preventDefault();return;}if(/^\\/(audio|images)\\//.test(hr)){a.setAttribute('href',resolveMedia(hr));}},true);
var _dbPromise=null;var origFetch=window.fetch.bind(window);window.__jtOrigFetch=origFetch;
function getSoundsDB(){if(_dbPromise)return _dbPromise;var cb='?t='+Math.floor(Date.now()/300000);var urls=IS_GH?[CDNS[0]+'data/sounds.json'+cb,CDNS[1]+'data/sounds.json'+cb,BASE+'data/sounds.json'+cb]:[BASE+'data/sounds.json'+cb,CDNS[0]+'data/sounds.json'+cb];_dbPromise=(async function(){for(var i=0;i<urls.length;i++){try{var r=await origFetch(urls[i]);if(r.ok){var d=await r.json();var arr=Array.isArray(d)?d:(d.sounds||[]);arr.forEach(function(it){if(it.src)it.src=resolveMedia(it.src);if(Array.isArray(it.variants))it.variants.forEach(function(v){if(v&&v.src)v.src=resolveMedia(v.src);});});return Array.isArray(d)?{sounds:arr,raw:arr}:{sounds:arr,raw:d};}}catch(e){}}return {sounds:[],raw:{sounds:[]}};})();return _dbPromise;}
window.fetch=async function(input,init){var urlStr=typeof input==='string'?input:(input&&input.url?input.url:String(input));var u;try{u=new URL(urlStr,location.origin);}catch(e){return origFetch(input,init);}var p=u.pathname;var idxApi=p.indexOf('/api/sounds');if(idxApi!==-1){var method=((init&&init.method)||(input&&input.method)||'GET').toUpperCase();if(method!=='GET')return new Response(JSON.stringify({error:'国内直连只读镜像节点'}),{status:400,headers:{'Content-Type':'application/json;charset=utf-8'}});if(u.searchParams.get('community')==='1')return new Response(JSON.stringify({sounds:[]}),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});var db=await getSoundsDB();var after=p.slice(idxApi+'/api/sounds'.length);if(after&&after!=='/'){var sid=decodeURIComponent(after.replace(/^\\//,''));var found=db.sounds.find(function(x){return String(x.id)===sid;});if(found)return new Response(JSON.stringify(found),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});return new Response(JSON.stringify({error:'Not found'}),{status:404,headers:{'Content-Type':'application/json;charset=utf-8'}});}return new Response(JSON.stringify(db.raw),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});}if(/^\\/(audio|images)\\//.test(p)&&u.origin===location.origin)return origFetch(resolveMedia(p),init);return origFetch(input,init);};
})();</script>"""


def sync_shengcang(site_dir: Path, auto_push: bool = True) -> dict:
    base = "https://shengcang-sound-library.fondcream1.chatgpt.site"
    st_h, b_h = fetch_bytes(base + "/")
    st_a, b_a = fetch_bytes(base + "/api/sounds")
    if st_h != 200 or st_a != 200:
        return {"site": "shengcang", "status": "upstream_skipped", "http": [st_h, st_a]}

    clean_html = strip_cf_challenge(b_h.decode("utf-8"))
    api_data = json.loads(b_a.decode("utf-8"))
    norm_sounds = json.dumps(api_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    fp = sha256_bytes(clean_html.encode("utf-8") + b"|" + norm_sounds)

    state_p = site_dir / ".sync_state.json"
    if state_p.is_file():
        try:
            if json.loads(state_p.read_text(encoding="utf-8")).get("fingerprint") == fp:
                return {"site": "shengcang", "status": "up-to-date"}
        except Exception:
            pass

    discover_and_download_vinext_assets(base, clean_html, site_dir)
    (site_dir / "data").mkdir(parents=True, exist_ok=True)
    (site_dir / "data" / "sounds.json").write_bytes(norm_sounds)

    items = api_data["sounds"] if isinstance(api_data, dict) and "sounds" in api_data else api_data
    audio_paths = set()
    for it in items:
        if it.get("src"):
            audio_paths.add(it["src"])
        for v in (it.get("variants") or []):
            if isinstance(v, dict) and v.get("src"):
                audio_paths.add(v["src"])

    def dl_aud(ap):
        lp = site_dir / ap.lstrip("/")
        if lp.is_file() and lp.stat().st_size > 100:
            return True
        lp.parent.mkdir(parents=True, exist_ok=True)
        s, b = fetch_bytes(base + urllib.parse.quote(ap, safe="/"), retries=4, timeout=40)
        if s == 200 and b:
            lp.write_bytes(b)
            return True
        return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        list(ex.map(dl_aud, sorted(audio_paths)))

    final_html = rewrite_vinext_html(clean_html, make_gate_script("金泰 AI · 声仓（影视声音素材库）"), SC_SHIM)
    (site_dir / "index.html").write_bytes(final_html.encode("utf-8"))
    check_html_js_syntax(site_dir / "index.html")
    state_p.write_text(json.dumps({"fingerprint": fp, "sounds_count": len(items)}, indent=2), encoding="utf-8")

    changed = git_push_if_changed(site_dir, "shengcang-sound-library", f"sync(auto): upstream shengcang ({len(items)} sounds)", auto_push)
    return {"site": "shengcang", "status": "updated" if changed else "up-to-date", "changed_files": len(changed), "sounds": len(items)}


# ------------------------------------------------------------------------------
# 2. Documentary Classroom Library Incremental Sync
# ------------------------------------------------------------------------------
DOC_SHIM = """<style>a[href*="signin-with-chatgpt"]{display:none!important}</style><script id="jintai-doc-shim">(function(){
var BASE=new URL('.',location.href).pathname;if(BASE.slice(-1)!=='/')BASE+='/';window.__JT_BASE__=BASE;
var IS_GH=/github\\.io$/i.test(location.hostname||'');
var CDNS=['https://testingcf.jsdelivr.net/gh/aikingtai-ctrl/documentary-classroom-library@main/','https://gcore.jsdelivr.net/gh/aikingtai-ctrl/documentary-classroom-library@main/'];
document.addEventListener('click',function(ev){var a=ev.target&&ev.target.closest?ev.target.closest('a'):null;if(!a)return;var hr=a.getAttribute('href')||'';if(hr.indexOf('signin-with-chatgpt')!==-1){ev.preventDefault();return;}if(hr==='/collection-workflow.md'||hr==='/reconciliation-template.csv')a.setAttribute('href',BASE+hr.slice(1));},true);
var _dbPromise=null;var origFetch=window.fetch.bind(window);
function getDocDB(){if(_dbPromise)return _dbPromise;var cb='?t='+Math.floor(Date.now()/300000);var urls=IS_GH?[CDNS[0]+'data/library_full.json'+cb,CDNS[1]+'data/library_full.json'+cb,BASE+'data/library_full.json'+cb]:[BASE+'data/library_full.json'+cb,CDNS[0]+'data/library_full.json'+cb];_dbPromise=(async function(){for(var i=0;i<urls.length;i++){try{var r=await origFetch(urls[i]);if(r.ok){var d=await r.json();(d.films||[]).forEach(function(f){var parts=[f.id,f.title,f.originalTitle,(f.aliases||[]).join(' '),f.year,f.country,f.director,f.region,f.period,f.topic,f.method,f.form,f.summary,f.teaching,f.research,(f.courses||[]).join(' '),(f.knowledge||[]).join(' ')];f._q=parts.filter(Boolean).join(' ').toLowerCase();var ym=String(f.year||'').match(/\\d{4}/);f._yr=ym?parseInt(ym[0],10):9999;f._dec=ym?String(Math.floor(parseInt(ym[0],10)/10)*10):'';});return d;}}catch(e){}}return {stats:{total:1841,published:0,pending:1163,formal:null},target:20000,countedAt:'',facets:{region:[],topic:[],decades:[]},films:[]};})();return _dbPromise;}
window.fetch=async function(input,init){var urlStr=typeof input==='string'?input:(input&&input.url?input.url:String(input));var u;try{u=new URL(urlStr,location.origin);}catch(e){return origFetch(input,init);}if(u.pathname.indexOf('/api/library')!==-1){var method=((init&&init.method)||(input&&input.method)||'GET').toUpperCase();if(method!=='GET')return new Response(JSON.stringify({error:'国内直连只读教学节点'}),{status:400,headers:{'Content-Type':'application/json;charset=utf-8'}});var db=await getDocDB();if(u.searchParams.get('export')==='1')return new Response(JSON.stringify(db),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});var fid=u.searchParams.get('id');if(fid){var found=(db.films||[]).find(function(x){return String(x.id)===String(fid);});if(found)return new Response(JSON.stringify({film:found}),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});return new Response(JSON.stringify({error:'未找到该影片记录'}),{status:404,headers:{'Content-Type':'application/json;charset=utf-8'}});}var q=(u.searchParams.get('q')||'').trim().toLowerCase();var terms=q?q.split(/\\s+/).filter(Boolean):[];var dec=u.searchParams.get('decade')||'';var reg=u.searchParams.get('region')||'';var top=u.searchParams.get('topic')||'';var sort=u.searchParams.get('sort')||'year';var page=Math.max(1,parseInt(u.searchParams.get('page')||'1',10)||1);var pageSize=24;var list=(db.films||[]).filter(function(f){if(dec&&f._dec!==dec)return false;if(reg&&f.region!==reg)return false;if(top&&f.topic!==top)return false;if(terms.length){for(var i=0;i<terms.length;i++){if(f._q.indexOf(terms[i])===-1)return false;}}return true;}).slice();if(sort==='title')list.sort(function(a,b){return (a.title||'').localeCompare(b.title||'','zh-CN');});else list.sort(function(a,b){return (a._order-b._order);});var total=list.length;var pages=Math.max(1,Math.ceil(total/pageSize));if(page>pages)page=pages;var slice=list.slice((page-1)*pageSize,page*pageSize);return new Response(JSON.stringify({user:null,films:slice,stats:db.stats,target:db.target,countedAt:db.countedAt,facets:db.facets,pagination:{page:page,pageSize:pageSize,total:total,pages:pages}}),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});}return origFetch(input,init);};
})();</script>"""


def sync_documentary(site_dir: Path, auto_push: bool = True) -> dict:
    base = "https://documentary-classroom-library.fondcream1.chatgpt.site"
    st_h, b_h = fetch_bytes(base + "/")
    st_p1, b_p1 = fetch_bytes(base + "/api/library?page=1")
    if st_h != 200 or st_p1 != 200:
        return {"site": "documentary", "status": "upstream_skipped", "http": [st_h, st_p1]}

    clean_html = strip_cf_challenge(b_h.decode("utf-8"))
    p1 = json.loads(b_p1.decode("utf-8"))
    fp_meta = json.dumps({"stats": p1.get("stats"), "countedAt": p1.get("countedAt"), "facets": p1.get("facets"), "p1_ids": [f.get("id") for f in p1.get("films", [])]}, sort_keys=True)
    fp = sha256_bytes(clean_html.encode("utf-8") + b"|" + fp_meta.encode("utf-8"))

    state_p = site_dir / ".sync_state.json"
    if state_p.is_file():
        try:
            if json.loads(state_p.read_text(encoding="utf-8")).get("fingerprint") == fp:
                return {"site": "documentary", "status": "up-to-date"}
        except Exception:
            pass

    discover_and_download_vinext_assets(base, clean_html, site_dir)
    for extra in ["/collection-workflow.md", "/reconciliation-template.csv"]:
        se, be = fetch_bytes(base + extra)
        if se == 200 and be:
            (site_dir / extra.lstrip("/")).write_bytes(be)

    # Load existing cached full film records so unchanged films don't need 678 roundtrips unless modified
    cached_by_id = {}
    lib_p = site_dir / "data" / "library_full.json"
    if lib_p.is_file():
        try:
            old_db = json.loads(lib_p.read_text(encoding="utf-8"))
            for f in old_db.get("films", []):
                if f.get("id"):
                    cached_by_id[f["id"]] = f
        except Exception:
            pass

    total_pages = p1["pagination"]["pages"]
    def fetch_pg(pg):
        if pg == 1:
            return 1, p1["films"]
        s, b = fetch_bytes(f"{base}/api/library?page={pg}")
        return pg, (json.loads(b.decode("utf-8"))["films"] if s == 200 and b else [])

    summaries = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        for _, flist in sorted(ex.map(fetch_pg, range(1, total_pages + 1)), key=lambda x: x[0]):
            summaries.extend(flist)

    def resolve_film(idx_item):
        idx, item = idx_item
        fid = item["id"]
        old = cached_by_id.get(fid)
        if old and old.get("title") == item.get("title") and old.get("summary") == item.get("summary") and "segments" in old:
            cp = dict(old)
            cp["_order"] = idx
            return cp
        s, b = fetch_bytes(f"{base}/api/library?id={urllib.parse.quote(fid)}", retries=4)
        full = (json.loads(b.decode("utf-8")).get("film") or item) if (s == 200 and b) else dict(item)
        full["_order"] = idx
        return full

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        full_films = list(ex.map(resolve_film, enumerate(summaries)))

    bundle = {
        "stats": p1["stats"],
        "target": p1["target"],
        "countedAt": p1["countedAt"],
        "facets": p1["facets"],
        "films": full_films,
    }
    (site_dir / "data").mkdir(parents=True, exist_ok=True)
    lib_p.write_bytes(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    final_html = rewrite_vinext_html(clean_html, make_gate_script("金泰 AI · 纪录片教学资源库"), DOC_SHIM)
    (site_dir / "index.html").write_bytes(final_html.encode("utf-8"))
    check_html_js_syntax(site_dir / "index.html")
    state_p.write_text(json.dumps({"fingerprint": fp, "published": len(full_films)}, indent=2), encoding="utf-8")

    changed = git_push_if_changed(site_dir, "documentary-classroom-library", f"sync(auto): upstream documentary library ({len(full_films)} films)", auto_push)
    return {"site": "documentary", "status": "updated" if changed else "up-to-date", "changed_files": len(changed), "films": len(full_films)}


# ------------------------------------------------------------------------------
# 3. Zhonghua Civilization Atlas Incremental Sync
# ------------------------------------------------------------------------------
ZH_SHIM = """<script id="jintai-zhonghua-cdn-shim">(function(){
var IS_GH=/github\\.io$/i.test(location.hostname||'');
var CDNS=['https://testingcf.jsdelivr.net/gh/aikingtai-ctrl/zhonghua-civilization-atlas@main/','https://gcore.jsdelivr.net/gh/aikingtai-ctrl/zhonghua-civilization-atlas@main/'];
var FALLBACK_SVG='data:image/svg+xml;utf8,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360"><rect width="480" height="360" fill="#f3efe6"/><rect x="16" y="16" width="448" height="328" fill="none" stroke="#c8bda8" stroke-width="1.5"/><text x="240" y="168" text-anchor="middle" fill="#5c5040" font-family="Microsoft YaHei,sans-serif" font-size="18">馆藏文物考证条目</text><text x="240" y="202" text-anchor="middle" fill="#8b7d6b" font-family="Microsoft YaHei,sans-serif" font-size="14">点击卡片查阅馆方详细著录与原图出处</text></svg>');
var _extMap=null;
function findOrigUrlByPreview(relPath){
  if(!_extMap){
    _extMap={};
    try{
      var pools=[];
      if(window.ARCHIVE_DATA&&Array.isArray(window.ARCHIVE_DATA.records))pools.push(window.ARCHIVE_DATA.records);
      if(Array.isArray(window.EXPANSION_CANDIDATES))pools.push(window.EXPANSION_CANDIDATES);
      if(window.EXPANSION_CANDIDATES&&Array.isArray(window.EXPANSION_CANDIDATES.items))pools.push(window.EXPANSION_CANDIDATES.items);
      pools.forEach(function(arr){arr.forEach(function(r){if(!r)return;var k=r.localImage||r.previewUrl;var u=r.imageUrl||r.originalImageUrl;if(k&&u)_extMap[k.replace(/^\\.\\//,'')]=u;});});
    }catch(e){}
  }
  return _extMap[relPath]||'';
}
window.addEventListener('error',function(ev){
  var el=ev.target;if(!el||el.tagName!=='IMG')return;
  var cur=el.getAttribute('src')||el.src||'';if(!cur||cur.indexOf('data:image/')===0)return;
  var step=parseInt(el.getAttribute('data-jt-fb')||'0',10);
  if(step>=4){el.src=FALLBACK_SVG;return;}
  el.setAttribute('data-jt-fb',String(step+1));
  var mRel=cur.match(/((?:assets|images)\\/[^?#]+)/);
  if(mRel&&cur.indexOf('wsrv.nl')===-1){
    var rel=mRel[1];
    if(IS_GH&&step===0){el.src=CDNS[0]+rel;return;}
    if(IS_GH&&step===1){el.src=CDNS[1]+rel;return;}
    var orig=findOrigUrlByPreview(rel);
    if(orig){el.src='https://wsrv.nl/?url='+encodeURIComponent(orig)+'&w=960&output=webp';return;}
  }
  if(/^https?:\\/\\//i.test(cur)&&cur.indexOf('wsrv.nl')===-1){
    el.src='https://wsrv.nl/?url='+encodeURIComponent(cur)+'&w=960&output=webp';return;
  }
  el.src=FALLBACK_SVG;
},true);
})();</script>"""


def norm_zh_rel(base_doc: str, raw_ref: str):
    if not raw_ref:
        return None
    r = raw_ref.strip()
    if r.startswith(("http://", "https://", "//", "data:", "mailto:", "javascript:", "#")):
        return None
    r = r.split("#", 1)[0].split("?", 1)[0].strip()
    if not r:
        return None
    if r.startswith("/"):
        norm = r.lstrip("/")
    else:
        parent = os.path.dirname(base_doc).replace("\\", "/")
        norm = os.path.normpath((parent + "/" + r) if parent else r).replace("\\", "/")
    if norm.startswith("..") or norm.startswith("/"):
        return None
    return norm


def sync_zhonghua(site_dir: Path, auto_push: bool = True) -> dict:
    host = "zhonghua-civilization-atlas.fondcream1.chatgpt.site"
    base = f"https://{host}/"

    # Quick probe on index.html + data.js + daily-batch.js + app.js
    probe_files = ["index.html", "data.js", "daily-batch.js", "app.js", "song-data.js", "liao-data.js"]
    probe_parts = []
    for pf in probe_files:
        st_p, b_p = fetch_bytes(base + ("" if pf == "index.html" else pf))
        if pf == "index.html" and st_p != 200:
            return {"site": "zhonghua", "status": "upstream_skipped", "http": st_p}
        if st_p == 200:
            if pf.endswith(".html"):
                b_p = strip_cf_challenge(b_p.decode("utf-8", "ignore")).encode("utf-8")
            probe_parts.append(sha256_bytes(b_p))
    quick_fp = "|".join(probe_parts)

    state_p = site_dir / ".sync_state.json"
    if state_p.is_file():
        try:
            if json.loads(state_p.read_text(encoding="utf-8")).get("quick_fp") == quick_fp:
                return {"site": "zhonghua", "status": "up-to-date"}
        except Exception:
            pass

    text_exts = {".html", ".css", ".js", ".json", ".md", ".svg", ".txt"}
    asset_exts = {".webp", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".woff", ".woff2"}
    to_visit = {"index.html"}
    visited = set()
    discovered_media = set()
    gate_tag = make_gate_script("金泰 AI · 中华文明影像库")

    while to_visit:
        batch = sorted(to_visit - visited)
        if not batch:
            break
        def dl_doc(rel):
            u = base + ("" if rel == "index.html" else urllib.parse.quote(rel, safe="/"))
            s, b = fetch_bytes(u, retries=3, timeout=30)
            return rel, s, b
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
            res = list(ex.map(dl_doc, batch))
        for rel, s, b in res:
            visited.add(rel)
            if s != 200 or not b:
                continue
            ext = os.path.splitext(rel)[1].lower()
            txt = b.decode("utf-8", errors="ignore")
            if ext == ".html":
                clean_h = strip_cf_challenge(txt)
                clean_h = re.sub(r'<script id="jt-unified-gate">.*?</script>', '', clean_h, flags=re.S)
                clean_h = re.sub(r'<script id="jintai-zhonghua-cdn-shim">.*?</script>', '', clean_h, flags=re.S)
                patched_h, n = re.subn(r"(<head\b[^>]*>)", r"\1" + gate_tag + ZH_SHIM, clean_h, count=1, flags=re.I)
                if n == 1:
                    lp = site_dir / rel
                    lp.parent.mkdir(parents=True, exist_ok=True)
                    lp.write_bytes(patched_h.encode("utf-8"))
                    check_html_js_syntax(lp)
                for ref in re.findall(r'(?:src|href)=["\']([^"\']+)["\']', clean_h, flags=re.I):
                    nr = norm_zh_rel(rel, ref)
                    if nr:
                        rext = os.path.splitext(nr)[1].lower()
                        if rext in text_exts:
                            to_visit.add(nr)
                        elif rext in asset_exts:
                            discovered_media.add(nr)
            else:
                # Never overwrite gigantic >90MB files (GitHub limit)
                if len(b) < 90 * 1024 * 1024:
                    lp = site_dir / rel
                    lp.parent.mkdir(parents=True, exist_ok=True)
                    if not lp.is_file() or lp.read_bytes() != b:
                        lp.write_bytes(b)
                if ext == ".css":
                    for ref in re.findall(r'url\(["\']?([^"\')]+)["\']?\)', txt, flags=re.I):
                        nr = norm_zh_rel(rel, ref)
                        if nr:
                            discovered_media.add(nr)
                elif ext in (".js", ".json"):
                    for m in re.finditer(r'["\'`]((?:\./)?(?:assets|images|research-[A-Za-z0-9_-]+)/[^"\'`\s?#]+|(?:[A-Za-z0-9_-]+\.html))(?:\?[^"\'`\s#]*)?["\'`]', txt):
                        nr = norm_zh_rel(rel, m.group(1))
                        if nr:
                            rext = os.path.splitext(nr)[1].lower()
                            if rext == ".html":
                                to_visit.add(nr)
                            elif rext in asset_exts:
                                discovered_media.add(nr)

    missing_media = sorted(m for m in discovered_media if not (site_dir / m).is_file())
    if missing_media:
        tls_local = threading.local()
        ctx = ssl.create_default_context()
        def dl_media(rel):
            conn = getattr(tls_local, "conn", None)
            for _ in range(2):
                try:
                    if conn is None:
                        conn = http.client.HTTPSConnection(host, 443, timeout=15, context=ctx)
                        tls_local.conn = conn
                    conn.request("GET", "/" + urllib.parse.quote(rel, safe="/"), headers={"User-Agent": UA, "Connection": "keep-alive"})
                    resp = conn.getresponse()
                    data = resp.read()
                    if resp.status == 200 and data and len(data) < 25 * 1024 * 1024:
                        lp = site_dir / rel
                        lp.parent.mkdir(parents=True, exist_ok=True)
                        lp.write_bytes(data)
                    return
                except Exception:
                    tls_local.conn = None
                    conn = None

        with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
            list(ex.map(dl_media, missing_media))

    state_p.write_text(json.dumps({"quick_fp": quick_fp, "docs": len(visited), "new_media": len(missing_media)}, indent=2), encoding="utf-8")
    changed = git_push_if_changed(site_dir, "zhonghua-civilization-atlas", f"sync(auto): upstream zhonghua atlas ({len(visited)} docs)", auto_push)
    return {"site": "zhonghua", "status": "updated" if changed else "up-to-date", "changed_files": len(changed), "new_media": len(missing_media)}


def sync_history_site1() -> dict:
    hist_mgr = Path(r"C:\Users\KingT\jintai-internal\中国历史文化图库\每日更新\管理\ensure_domestic_compact_index.py")
    pub = Path(r"C:\Users\KingT\jintai-internal\中国历史文化图库\每日更新\publish_checkout_20261012")
    if not hist_mgr.is_file() or not pub.is_dir():
        return {"site": "history", "status": "skipped_not_local"}
    subprocess.run([sys.executable, str(hist_mgr)], check=True)
    st = subprocess.run(["git", "-C", str(pub), "status", "--porcelain", "index.html", "browser.html", "d1_idx", "d2_idx"], capture_output=True, text=True)
    if st.stdout.strip():
        # Update guard snapshot & push
        sync_ext = hist_mgr.parent / "sync_external_and_verify.py"
        subprocess.run([sys.executable, str(sync_ext)], check=True)
        subprocess.run(["git", "-C", str(pub), "add", "index.html", "browser.html", "d1_idx", "d2_idx"], check=True)
        subprocess.run(["git", "-C", str(pub), "commit", "-m", "sync(auto): refresh domestic compact index & WeChat gate"], check=True)
        subprocess.run(["git", "-C", str(pub), "push", "origin", "HEAD:main"], check=True, timeout=180)
        return {"site": "history", "status": "updated"}
    return {"site": "history", "status": "up-to-date"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["all", "history", "shengcang", "documentary", "zhonghua"], default="all")
    ap.add_argument("--repo-dir", type=str, default="")
    ap.add_argument("--no-push", action="store_true")
    args = ap.parse_args()

    auto_push = not args.no_push
    root = Path(r"C:\Users\KingT\Documents\Claude产出\2026-10-30_四大网站国内直连部署")

    results = []
    if args.only in ("all", "history") and not args.repo_dir:
        results.append(sync_history_site1())
    if args.only in ("all", "shengcang"):
        d = Path(args.repo_dir) if args.repo_dir else (root / "01_shengcang-sound-library")
        results.append(sync_shengcang(d, auto_push=auto_push))
    if args.only in ("all", "documentary"):
        d = Path(args.repo_dir) if args.repo_dir else (root / "02_documentary-classroom-library")
        results.append(sync_documentary(d, auto_push=auto_push))
    if args.only in ("all", "zhonghua"):
        d = Path(args.repo_dir) if args.repo_dir else (root / "03_zhonghua-civilization-atlas")
        results.append(sync_zhonghua(d, auto_push=auto_push))

    print(json.dumps({"synced_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
