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
import gzip
import io
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
  try{{if(location.hostname==='127.0.0.1'||location.hostname==='localhost'||location.href.indexOf('jt_ok=6e95ff3e')!==-1){{localStorage.setItem(k,H);sessionStorage.setItem(k,H);return true;}}}}catch(e){{}}
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
        r'function\s*\(([A-Za-z_$][\w$]*)\)\s*\{\s*return\s*[`"\']\/[`"\']\s*\+\s*\1\s*\}',
        r'function(\1){return(window.__JT_BASE__||"./")+\1}',
        js_text,
    )
    js_text = re.sub(
        r'\(\s*([A-Za-z_$][\w$]*)\s*\)\s*=>\s*[`"\']\/[`"\']\s*\+\s*\1\b',
        r'(\1)=>(window.__JT_BASE__||"./")+\1',
        js_text,
    )
    js_text = re.sub(
        r'\(\s*([A-Za-z_$][\w$]*)\s*\)\s*=>\s*`\/\$\{\1\}`',
        r'(\1)=>`${window.__JT_BASE__||"./"}${\1}`',
        js_text,
    )
    return js_text


def discover_and_download_vinext_assets(base_url: str, html_text: str, site_dir: Path) -> set[str]:
    queue = set()
    for m in re.findall(r'["\'](/(?:_next/static|images)/[^"\'\\?#]+|/favicon\.[A-Za-z0-9]+)', html_text):
        queue.add(m)
    downloaded = set()
    reachable_rel = set()
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
                clean_rel = rel.lstrip("/")
                reachable_rel.add(clean_rel)
                local_p = site_dir / clean_rel
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
    # Prune retired unreachable _next/static files so hashed rebuilds never bloat Git / Pages
    next_static = site_dir / "_next" / "static"
    if next_static.is_dir() and reachable_rel:
        for existing_f in sorted(next_static.rglob("*")):
            if existing_f.is_file():
                rel_s = existing_f.relative_to(site_dir).as_posix()
                if rel_s not in reachable_rel:
                    existing_f.unlink(missing_ok=True)
    return reachable_rel


def rewrite_vinext_html(html_text: str, gate_tag: str, shim_tag: str) -> str:
    out = strip_cf_challenge(html_text)
    out = out.replace('"/_next/static/', '"./_next/static/')
    out = out.replace("'/_next/static/", "'./_next/static/")
    out = out.replace('\\"/_next/static/', '\\"./_next/static/')
    out = out.replace('href="/favicon.svg"', 'href="./favicon.svg"')
    out = out.replace('"/images/', '"./images/')
    out = out.replace('\\"/images/', '\\"./images/')
    out = out.replace('"/catalogue-', '"./catalogue-')
    out = out.replace("'/catalogue-", "'./catalogue-")
    out = out.replace('\\"/catalogue-', '\\"./catalogue-')
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


def git_prepare_repo(repo_dir: Path, auto_push: bool):
    if not auto_push or not (repo_dir / ".git").is_dir():
        return
    if (repo_dir / ".git" / "rebase-merge").exists() or (repo_dir / ".git" / "rebase-apply").exists():
        subprocess.run(["git", "rebase", "--abort"], cwd=str(repo_dir), capture_output=True)
    subprocess.run(["git", "pull", "--rebase", "-X", "ours", "origin", "main"], cwd=str(repo_dir), capture_output=True)
    if (repo_dir / ".git" / "rebase-merge").exists() or (repo_dir / ".git" / "rebase-apply").exists():
        subprocess.run(["git", "rebase", "--abort"], cwd=str(repo_dir), capture_output=True)


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
        subprocess.run(["git", "pull", "--rebase", "-X", "theirs", "origin", "main"], cwd=str(repo_dir), capture_output=True)
        if (repo_dir / ".git" / "rebase-merge").exists() or (repo_dir / ".git" / "rebase-apply").exists():
            subprocess.run(["git", "rebase", "--abort"], cwd=str(repo_dir), capture_output=True)
        subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=str(repo_dir), check=True, timeout=300)
        purge_jsdelivr(repo_name, changed_files)
    return changed_files


# ------------------------------------------------------------------------------
# 1. Shengcang Incremental Sync
# ------------------------------------------------------------------------------
SHIM_REV = "20261113d1"
SC_SHIM_REV = "20261124finder5"
ZH_SHIM_REV = "20261124i1"
SC_SHIM = """<style>a[href*="signin-with-chatgpt"]{display:none!important}</style><script id="jintai-shengcang-shim">(function(){
var BASE=new URL('.',location.href).pathname;if(BASE.slice(-1)!=='/')BASE+='/';window.__JT_BASE__=BASE;
var IS_GH=/github\\.io$/i.test(location.hostname||'');
var RAW='https://raw.githubusercontent.com/aikingtai-ctrl/shengcang-sound-library/main/';
var SOURCE='https://shengcang-sound-library.jeaess66.chatgpt.site/';
var CDNS=['https://testingcf.jsdelivr.net/gh/aikingtai-ctrl/shengcang-sound-library@main/','https://gcore.jsdelivr.net/gh/aikingtai-ctrl/shengcang-sound-library@main/'];
function resolveMedia(rel){if(!rel||typeof rel!=='string')return rel;var clean=rel.replace(/^\\.\\//,'').replace(/^\\//,'');if(!/^(audio|images)\\//.test(clean))return rel;return BASE+clean;}
window.addEventListener('error',function(ev){var el=ev.target;if(!el||!el.tagName)return;var tag=el.tagName.toUpperCase();if(tag!=='AUDIO'&&tag!=='SOURCE'&&tag!=='IMG')return;var cur=el.getAttribute('src')||el.src||'';var m=cur.match(/(?:shengcang-sound-library(?:@main|\\/main)\\/|\\/)((?:audio|images)\\/[^?#]+)/);if(!m)return;var clean=m[1];var step=parseInt(el.getAttribute('data-jt-fb')||'0',10);var cands=IS_GH?[RAW+clean,CDNS[0]+clean,CDNS[1]+clean]:[CDNS[0]+clean,RAW+clean];if(tag==='AUDIO'||tag==='SOURCE')cands.push(SOURCE+clean);if(step<cands.length){el.setAttribute('data-jt-fb',String(step+1));el.src=cands[step];if(tag==='AUDIO'&&typeof el.load==='function')el.load();}},true);
document.addEventListener('click',function(ev){var a=ev.target&&ev.target.closest?ev.target.closest('a'):null;if(!a)return;var hr=a.getAttribute('href')||'';if(hr.indexOf('signin-with-chatgpt')!==-1){ev.preventDefault();return;}if(/^\\/(audio|images)\\//.test(hr)){a.setAttribute('href',resolveMedia(hr));}},true);
var _dbPromise=null;var origFetch=window.fetch.bind(window);window.__jtOrigFetch=origFetch;
function getSoundsDB(){if(_dbPromise)return _dbPromise;var cb='?t='+Math.floor(Date.now()/300000);var urls=IS_GH?[BASE+'data/sounds.json'+cb,RAW+'data/sounds.json'+cb,CDNS[0]+'data/sounds.json'+cb]:[BASE+'data/sounds.json'+cb,CDNS[0]+'data/sounds.json'+cb];_dbPromise=(async function(){for(var i=0;i<urls.length;i++){try{var r=await origFetch(urls[i]);if(r.ok){var d=await r.json();var arr=Array.isArray(d)?d:(d.sounds||[]);arr.forEach(function(it){if(it.src)it.src=resolveMedia(it.src);if(Array.isArray(it.variants))it.variants.forEach(function(v){if(v&&v.src)v.src=resolveMedia(v.src);});});return Array.isArray(d)?{sounds:arr,raw:arr}:{sounds:arr,raw:d};}}catch(e){}}return {sounds:[],raw:{sounds:[]}};})();return _dbPromise;}
window.fetch=async function(input,init){var urlStr=typeof input==='string'?input:(input&&input.url?input.url:String(input));var u;try{u=new URL(urlStr,location.origin);}catch(e){return origFetch(input,init);}var p=u.pathname;var idxApi=p.indexOf('/api/sounds');if(idxApi!==-1){var method=((init&&init.method)||(input&&input.method)||'GET').toUpperCase();if(method!=='GET')return new Response(JSON.stringify({error:'国内直连只读镜像节点'}),{status:400,headers:{'Content-Type':'application/json;charset=utf-8'}});if(u.searchParams.get('community')==='1')return new Response(JSON.stringify({sounds:[]}),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});var db=await getSoundsDB();var after=p.slice(idxApi+'/api/sounds'.length);if(after&&after!=='/'){var sid=decodeURIComponent(after.replace(/^\\//,''));var found=db.sounds.find(function(x){return String(x.id)===sid;});if(found)return new Response(JSON.stringify(found),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});return new Response(JSON.stringify({error:'Not found'}),{status:404,headers:{'Content-Type':'application/json;charset=utf-8'}});}return new Response(JSON.stringify(db.raw),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});}if(u.origin===location.origin&&p.indexOf(BASE)!==0&&(/^\\/(audio|images)\\//.test(p)||/^\\/catalogue-[A-Za-z0-9_.-]+\\.json$/.test(p)))return origFetch(BASE+p.slice(1)+u.search,init);return origFetch(input,init);};
})();</script>"""


def sync_shengcang(site_dir: Path, auto_push: bool = True) -> dict:
    git_prepare_repo(site_dir, auto_push)
    base = "https://shengcang-sound-library.fondcream1.chatgpt.site"
    try:
        with urllib.request.urlopen(urllib.request.Request(base + "/", headers={"User-Agent": UA}), timeout=15) as r_eff:
            eff_netloc = urllib.parse.urlparse(r_eff.geturl()).netloc
            if eff_netloc:
                base = f"https://{eff_netloc}"
    except Exception:
        pass
    st_h, b_h = fetch_bytes(base + "/")
    st_a, b_a = fetch_bytes(base + "/api/sounds")
    if st_h != 200 or st_a != 200:
        return {"site": "shengcang", "status": "upstream_skipped", "http": [st_h, st_a]}

    clean_html = strip_cf_challenge(b_h.decode("utf-8"))
    cat_refs = sorted(set(re.findall(r"/catalogue-[A-Za-z0-9_.-]+\.json", clean_html)))
    api_data = json.loads(b_a.decode("utf-8"))
    norm_sounds = json.dumps(api_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    finder_patch = site_dir / "scripts" / "finder_patch.py"
    fp = sha256_bytes(clean_html.encode("utf-8") + b"|" + norm_sounds + b"|" + SC_SHIM_REV.encode("ascii") + b"|" + finder_patch.read_bytes())

    cats_present = all((site_dir / cr.lstrip("/")).is_file() for cr in cat_refs)
    state_p = site_dir / ".sync_state.json"
    if state_p.is_file() and cats_present:
        try:
            if json.loads(state_p.read_text(encoding="utf-8")).get("fingerprint") == fp:
                return {"site": "shengcang", "status": "up-to-date"}
        except Exception:
            pass

    discover_and_download_vinext_assets(base, clean_html, site_dir)
    (site_dir / "data").mkdir(parents=True, exist_ok=True)
    (site_dir / "data" / "sounds.json").write_bytes(norm_sounds)

    # Download sharded full catalogue manifest + parts & prune retired catalogue-*.json
    active_cat_files = set()
    for cr in cat_refs:
        sc_st, sc_b = fetch_bytes(base + cr, retries=4, timeout=40)
        if sc_st != 200 or not sc_b:
            continue
        cname = cr.lstrip("/")
        active_cat_files.add(cname)
        manifest_obj = json.loads(sc_b.decode("utf-8"))
        parts = manifest_obj.get("parts") if isinstance(manifest_obj, dict) else None
        if isinstance(parts, list) and parts:
            def dl_cat_part(pinfo):
                purl = pinfo.get("url", "")
                if not purl:
                    return None
                pname = purl.lstrip("/")
                ps, pb = fetch_bytes(base + purl, retries=4, timeout=45)
                if ps == 200 and pb:
                    try:
                        pobj = json.loads(pb.decode("utf-8"))
                        if isinstance(pobj, dict) and isinstance(pobj.get("columns"), list) and "src" in pobj["columns"]:
                            sidx = pobj["columns"].index("src")
                            for row in pobj.get("rows") or []:
                                if isinstance(row, list) and len(row) > sidx and isinstance(row[sidx], str) and row[sidx].startswith("/audio/"):
                                    row[sidx] = "." + row[sidx]
                            pb = json.dumps(pobj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    except Exception:
                        pass
                    (site_dir / pname).write_bytes(pb)
                    return pname
                return None

            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                for got_name in ex.map(dl_cat_part, parts):
                    if got_name:
                        active_cat_files.add(got_name)
            for pinfo in parts:
                if isinstance(pinfo.get("url"), str) and pinfo["url"].startswith("/catalogue-"):
                    pinfo["url"] = "." + pinfo["url"]
            sc_b = json.dumps(manifest_obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        (site_dir / cname).write_bytes(sc_b)

    if active_cat_files:
        for old_cat in sorted(site_dir.glob("catalogue-*.json")):
            if old_cat.name not in active_cat_files:
                old_cat.unlink(missing_ok=True)

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
    subprocess.run([sys.executable, str(finder_patch), str(site_dir)], check=True)
    check_html_js_syntax(site_dir / "index.html")
    state_p.write_bytes(json.dumps({"fingerprint": fp, "sounds_count": len(items)}, indent=2).encode("utf-8"))

    changed = git_push_if_changed(site_dir, "shengcang-sound-library", f"sync(auto): upstream shengcang ({len(items)} sounds)", auto_push)
    return {"site": "shengcang", "status": "updated" if changed else "up-to-date", "changed_files": len(changed), "sounds": len(items)}


# ------------------------------------------------------------------------------
# 2. Documentary Classroom Library Incremental Sync
# ------------------------------------------------------------------------------
DOC_SHIM = """<style>a[href*="signin-with-chatgpt"]{display:none!important}</style><script id="jintai-doc-shim">(function(){
var BASE=new URL('.',location.href).pathname;if(BASE.slice(-1)!=='/')BASE+='/';window.__JT_BASE__=BASE;
var IS_GH=/github\\.io$/i.test(location.hostname||'');
var RAW='https://raw.githubusercontent.com/aikingtai-ctrl/documentary-classroom-library/main/';
var CDNS=['https://testingcf.jsdelivr.net/gh/aikingtai-ctrl/documentary-classroom-library@main/','https://gcore.jsdelivr.net/gh/aikingtai-ctrl/documentary-classroom-library@main/'];
document.addEventListener('click',function(ev){var a=ev.target&&ev.target.closest?ev.target.closest('a'):null;if(!a)return;var hr=a.getAttribute('href')||'';if(hr.indexOf('signin-with-chatgpt')!==-1){ev.preventDefault();return;}if(hr==='/collection-workflow.md'||hr==='/reconciliation-template.csv')a.setAttribute('href',BASE+hr.slice(1));},true);
var _dbPromise=null;var origFetch=window.fetch.bind(window);
function _js(v){return Array.isArray(v)?v.join(' '):(v==null?'':String(v));}function getDocDB(){if(_dbPromise)return _dbPromise;var cb='?t='+Math.floor(Date.now()/300000);var urls=[BASE+'data/library_full.json'+cb,RAW+'data/library_full.json'+cb,CDNS[0]+'data/library_full.json'+cb,CDNS[1]+'data/library_full.json'+cb];_dbPromise=(async function(){for(var i=0;i<urls.length;i++){try{var r=await origFetch(urls[i]);if(r.ok){var d=await r.json();(d.films||[]).forEach(function(f,idx){if(f._order==null)f._order=idx;var parts=[f.id,f.title,f.originalTitle,_js(f.aliases),f.year,f.country,f.director,f.region,f.period,f.topic,f.method,f.form,f.summary,f.teaching,f.research,_js(f.courses),_js(f.knowledge)];f._q=parts.filter(Boolean).join(' ').toLowerCase();var ym=String(f.year||'').match(/\\d{4}/);f._yr=ym?parseInt(ym[0],10):9999;f._dec=ym?String(Math.floor(parseInt(ym[0],10)/10)*10):'';});return d;}}catch(e){}}return {stats:{total:4353,published:0,pending:2853,formal:null},target:20000,countedAt:'',facets:{region:[],topic:[],decades:[]},films:[]};})();return _dbPromise;}
window.fetch=async function(input,init){var urlStr=typeof input==='string'?input:(input&&input.url?input.url:String(input));var u;try{u=new URL(urlStr,location.origin);}catch(e){return origFetch(input,init);}if(u.pathname.indexOf('/api/library')!==-1){var method=((init&&init.method)||(input&&input.method)||'GET').toUpperCase();if(method!=='GET')return new Response(JSON.stringify({error:'国内直连只读教学节点'}),{status:400,headers:{'Content-Type':'application/json;charset=utf-8'}});var db=await getDocDB();if(u.searchParams.get('export')==='1')return new Response(JSON.stringify(db),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});var fid=u.searchParams.get('id');if(fid){var found=(db.films||[]).find(function(x){return String(x.id)===String(fid);});if(found)return new Response(JSON.stringify({film:found}),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});return new Response(JSON.stringify({error:'未找到该影片记录'}),{status:404,headers:{'Content-Type':'application/json;charset=utf-8'}});}var q=(u.searchParams.get('q')||'').trim().toLowerCase();var terms=q?q.split(/\\s+/).filter(Boolean):[];var dec=u.searchParams.get('decade')||'';var reg=u.searchParams.get('region')||'';var top=u.searchParams.get('topic')||'';var sort=u.searchParams.get('sort')||'year';var page=Math.max(1,parseInt(u.searchParams.get('page')||'1',10)||1);var pageSize=24;var list=(db.films||[]).filter(function(f){if(dec&&f._dec!==dec)return false;if(reg&&f.region!==reg)return false;if(top&&f.topic!==top)return false;if(terms.length){for(var i=0;i<terms.length;i++){if(f._q.indexOf(terms[i])===-1)return false;}}return true;}).slice();if(sort==='title')list.sort(function(a,b){return (a.title||'').localeCompare(b.title||'','zh-CN');});else list.sort(function(a,b){return (a._order-b._order);});var total=list.length;var pages=Math.max(1,Math.ceil(total/pageSize));if(page>pages)page=pages;var slice=list.slice((page-1)*pageSize,page*pageSize);return new Response(JSON.stringify({user:null,films:slice,stats:db.stats,target:db.target,countedAt:db.countedAt,facets:db.facets,pagination:{page:page,pageSize:pageSize,total:total,pages:pages}}),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});}return origFetch(input,init);};
})();</script>"""


def sync_documentary(site_dir: Path, auto_push: bool = True) -> dict:
    git_prepare_repo(site_dir, auto_push)
    base = "https://documentary-classroom-library.fondcream1.chatgpt.site"
    st_h, b_h = fetch_bytes(base + "/")
    st_p1, b_p1 = fetch_bytes(base + "/api/library?page=1")
    if st_h != 200 or st_p1 != 200:
        return {"site": "documentary", "status": "upstream_skipped", "http": [st_h, st_p1]}

    clean_html = strip_cf_challenge(b_h.decode("utf-8"))
    # Strip dynamic SSR timestamp (countedAt ISO string) for stable change detection
    norm_html_for_fp = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", "TS", clean_html)
    p1 = json.loads(b_p1.decode("utf-8"))
    fp_meta = json.dumps({"stats": p1.get("stats"), "facets": p1.get("facets"), "pages": p1.get("pagination", {}).get("pages"), "p1_films": p1.get("films", [])}, ensure_ascii=False, sort_keys=True)
    fp = sha256_bytes(norm_html_for_fp.encode("utf-8") + b"|" + fp_meta.encode("utf-8") + b"|" + SHIM_REV.encode("ascii"))

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
ZH_SHIM = """<style>a[href*="signin-with-chatgpt"]{display:none!important}</style><script id="jintai-zhonghua-cdn-shim">(function(){
var BASE=new URL('.',location.href).pathname;if(BASE.slice(-1)!=='/')BASE+='/';window.__JT_BASE__=BASE;
var IS_GH=/github\\.io$/i.test(location.hostname||'');
var RAW='https://raw.githubusercontent.com/aikingtai-ctrl/zhonghua-civilization-atlas/main/';
var CDNS=['https://testingcf.jsdelivr.net/gh/aikingtai-ctrl/zhonghua-civilization-atlas@main/','https://gcore.jsdelivr.net/gh/aikingtai-ctrl/zhonghua-civilization-atlas@main/'];
if(typeof window.fetch==='function'){
  var origFetch=window.fetch.bind(window);
  window.fetch=function(input,init){
    var urlStr=typeof input==='string'?input:(input&&input.url?input.url:String(input));
    try{
      var u=new URL(urlStr,location.origin);
      if(u.origin===location.origin&&!/chatgpt\\.site$/i.test(location.hostname||'')&&u.pathname.indexOf('/api/atlas-control/')===0){
        return Promise.resolve(new Response(JSON.stringify({ok:false,authenticated:false,readOnlyMirror:true,message:'国内静态镜像站为只读浏览模式'}),{status:200,headers:{'content-type':'application/json; charset=utf-8'}}));
      }
      if(u.origin===location.origin&&u.pathname.charAt(0)==='/'&&u.pathname.indexOf(BASE)!==0&&u.pathname.indexOf('/api/')!==0&&u.pathname.indexOf('/publications')!==0){
        return origFetch(BASE+u.pathname.slice(1)+u.search,init);
      }
    }catch(e){}
    return origFetch(input,init);
  };
}
var FALLBACK_SVG='data:image/svg+xml;utf8,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360"><rect width="480" height="360" fill="#f3efe6"/><rect x="16" y="16" width="448" height="328" fill="none" stroke="#c8bda8" stroke-width="1.5"/><text x="240" y="168" text-anchor="middle" fill="#5c5040" font-family="Microsoft YaHei,sans-serif" font-size="18">馆藏文物考证条目</text><text x="240" y="202" text-anchor="middle" fill="#8b7d6b" font-family="Microsoft YaHei,sans-serif" font-size="14">点击卡片查阅馆方详细著录与原图出处</text></svg>');
var _extMap=null;
function toDomesticSafeImg(u){
  if(!u||typeof u!=='string')return u;
  if(/^https?:\\/\\/(?:[^/]+\\.)?(?:clevelandart\\.org|artic\\.edu|si\\.edu|wikimedia\\.org|wikipedia\\.org|metmuseum\\.org)\\//i.test(u)){
    return 'https://wsrv.nl/?url='+encodeURIComponent(u)+'&w=960&output=webp';
  }
  return u;
}
function sanitizePack(pack){
  try{
    if(!pack||!Array.isArray(pack.records))return;
    var start=pack.__jtSanitizedLen||0;
    if(start>=pack.records.length)return;
    for(var i=start;i<pack.records.length;i++){
      var r=pack.records[i];
      if(!r)continue;
      var orig=r.imageUrl||r.originalImageUrl;
      if(!orig)continue;
      if(typeof r.previewUrl==='string'&&/^research-[A-Za-z0-9_-]+\\//.test(r.previewUrl))r.previewUrl=toDomesticSafeImg(orig);
      if(typeof r.localImage==='string'&&/^research-[A-Za-z0-9_-]+\\//.test(r.localImage))r.localImage=toDomesticSafeImg(orig);
      if(typeof r.thumbnailUrl==='string'&&/^research-[A-Za-z0-9_-]+\\//.test(r.thumbnailUrl))r.thumbnailUrl=toDomesticSafeImg(orig);
    }
    pack.__jtSanitizedLen=pack.records.length;
  }catch(e){}
}
window.__jtSanitizePack=sanitizePack;
['ARCHIVE_DATA','SHANG_DATA','WESTERN_ZHOU_DATA','SPRING_AUTUMN_DATA','WARRING_STATES_DATA','QIN_DATA','WESTERN_HAN_DATA','EASTERN_HAN_DATA','WEIJIN_DATA','SUI_DATA','SONG_DATA','LIAO_DATA','JIN_DATA'].forEach(function(dk){
  var _v=window[dk];if(_v)sanitizePack(_v);
  try{Object.defineProperty(window,dk,{configurable:true,enumerable:true,get:function(){return _v;},set:function(nv){_v=nv;sanitizePack(nv);}});}catch(e){}
});
function sanitizeUnhostedPreviews(){
  try{Object.keys(window).forEach(function(wk){if(wk==='ARCHIVE_DATA'||/_DATA$/.test(wk))sanitizePack(window[wk]);});}catch(e){}
}
window.__jtSanitizeAll=sanitizeUnhostedPreviews;
document.addEventListener('DOMContentLoaded',sanitizeUnhostedPreviews);
function findOrigUrlByPreview(relPath){
  if(!_extMap){
    _extMap={};
    try{
      var pools=[];
      if(window.ARCHIVE_DATA&&Array.isArray(window.ARCHIVE_DATA.records))pools.push(window.ARCHIVE_DATA.records);
      if(Array.isArray(window.EXPANSION_CANDIDATES))pools.push(window.EXPANSION_CANDIDATES);
      if(window.EXPANSION_CANDIDATES&&Array.isArray(window.EXPANSION_CANDIDATES.items))pools.push(window.EXPANSION_CANDIDATES.items);
      Object.keys(window).forEach(function(wk){if(/_DATA$/.test(wk)&&window[wk]&&Array.isArray(window[wk].records))pools.push(window[wk].records);});
      pools.forEach(function(arr){arr.forEach(function(r){if(!r)return;var u=r.imageUrl||r.originalImageUrl;if(!u)return;[r.localImage,r.previewUrl].forEach(function(k){if(k)_extMap[String(k).replace(/^\\.\\//,'')]=u;});});});
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
  var mRel=cur.match(/((?:assets|(?:[A-Za-z0-9_-]+-)?images|research-[A-Za-z0-9_-]+)\\/[^?#]+)/);
  if(mRel&&cur.indexOf('wsrv.nl')===-1){
    var rel=mRel[1];
    if(IS_GH&&step===0){el.src=RAW+rel;return;}
    if(IS_GH&&step===1){el.src=CDNS[0]+rel;return;}
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


_ZH_CATALOG_LOADER_RE = re.compile(r'(?<![\w./-])(?:\./|/)?catalog-loader\.js\?v=[0-9a-f]{12,64}', re.I)
_ZH_CATALOG_RECORD_RE = re.compile(r'(?<![\w./-])(?:\./|/)?catalog-records-([1-9][0-9]*)\.js\?v=[0-9a-f]{12,64}', re.I)
_ZH_CATALOG_BASE_RE = re.compile(r'(?<![\w./-])(?:\./|/)?catalog-base\.json\.gz\?v=[0-9a-f]{12,64}', re.I)


def _fetch_zhonghua_catalog_verified(base: str, ref: str) -> bytes:
    status, body = fetch_bytes(urllib.parse.urljoin(base, ref), retries=3, timeout=30)
    if status != 200 or not body:
        raise RuntimeError(f"中华文明原站目录资源不可用：{ref} (HTTP {status})")
    # The gzip URL uses a cache revision, not the compressed response's hash.
    if urllib.parse.urlsplit(ref).path.endswith("catalog-base.json.gz"):
        if not (body.startswith(b"\x1f\x8b") or body.lstrip().startswith(b"{")):
            raise RuntimeError(f"中华文明原站目录基础数据格式无效：{ref}")
        return body
    version_match = re.search(r"[?&]v=([0-9a-f]{12,64})(?:&|$)", ref, flags=re.I)
    if not version_match:
        raise RuntimeError(f"中华文明原站目录资源无版本哈希：{ref}")
    expected = version_match.group(1).lower()
    actual = sha256_bytes(body)
    if not actual.startswith(expected):
        raise RuntimeError(f"中华文明原站目录资源哈希不符：{ref} (SHA-256 {actual[:12]})")
    return body


def _probe_zhonghua_catalog_asset(base: str, ref: str) -> str:
    """Check a catalog resource without downloading its multi-megabyte body."""
    url = urllib.parse.urljoin(base, ref)
    head_status = 0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "identity"}, method="HEAD")
        with urllib.request.urlopen(req, timeout=12) as response:
            head_status = response.status
            length = response.headers.get("Content-Length")
            if head_status == 200 and length and length.isdigit() and int(length) > 0:
                return length
    except urllib.error.HTTPError as error:
        head_status = error.code
    except Exception:
        pass

    # Some origins reject HEAD or omit Content-Length. Read only one byte even
    # when the server ignores Range, so the health check remains lightweight.
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": UA, "Accept-Encoding": "identity", "Range": "bytes=0-0"},
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            if response.status not in (200, 206) or not response.read(1):
                raise RuntimeError(f"中华文明原站目录资源为空：{ref} (HTTP {response.status})")
            content_range = response.headers.get("Content-Range", "")
            total = content_range.rsplit("/", 1)[-1] if "/" in content_range else ""
            if total.isdigit() and int(total) > 0:
                return total
            length = response.headers.get("Content-Length", "") if response.status == 200 else ""
            return length if length.isdigit() and int(length) > 0 else ">=1"
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"中华文明原站目录资源不可用：{ref} (HEAD {head_status}, GET {error.code})") from error
    except RuntimeError:
        raise
    except Exception as error:
        raise RuntimeError(f"中华文明原站目录资源不可用：{ref} (HEAD {head_status}, Range GET 失败)") from error


def probe_zhonghua_catalog_upstream(base: str, index_bytes: bytes) -> tuple[list[str], dict[str, bytes], str]:
    """Parse the loader and check every declared catalog asset before sync."""
    index_text = index_bytes.decode("utf-8", errors="replace")
    loader_refs = set(_ZH_CATALOG_LOADER_RE.findall(index_text))
    if len(loader_refs) > 1:
        raise RuntimeError("中华文明原站目录有多个不同版本的 catalog-loader.js")

    verified_loader = {}
    catalog_text = index_text
    if loader_refs:
        loader_ref = next(iter(loader_refs))
        loader_rel = norm_zh_rel("index.html", loader_ref)
        loader_bytes = _fetch_zhonghua_catalog_verified(base, loader_ref)
        verified_loader[loader_rel] = loader_bytes
        loader_text = loader_bytes.decode("utf-8")
        catalog_text += "\n" + loader_text
        base_ref, script_refs = zh_catalog_loader_references(loader_text)
        refs = [base_ref, *script_refs]
    else:
        record_refs = {}
        for match in _ZH_CATALOG_RECORD_RE.finditer(catalog_text):
            number = int(match.group(1))
            ref = match.group(0)
            if number in record_refs and record_refs[number] != ref:
                raise RuntimeError(f"中华文明原站目录分片 {number} 有多个版本")
            record_refs[number] = ref
        if not record_refs:
            raise RuntimeError("中华文明原站未声明 catalog-records 分片，停止覆盖镜像")
        if sorted(record_refs) != list(range(1, max(record_refs) + 1)):
            raise RuntimeError("中华文明原站 catalog-records 分片编号不连续")
        base_refs = set(_ZH_CATALOG_BASE_RE.findall(catalog_text))
        if len(base_refs) > 1:
            raise RuntimeError("中华文明原站目录基础数据有多个版本")
        refs = [*record_refs.values(), *base_refs]
    health = [f"{ref}:{_probe_zhonghua_catalog_asset(base, ref)}" for ref in refs]
    fingerprint = sha256_bytes("\n".join([*health, sha256_bytes(catalog_text.encode("utf-8"))]).encode("utf-8"))
    return refs, verified_loader, fingerprint


def verify_zhonghua_catalog_upstream(base: str, refs: list[str], verified_loader: dict[str, bytes]) -> dict[str, bytes]:
    """Only on a changed snapshot, fully hash and cache every catalog asset."""
    verified = dict(verified_loader)
    for ref in refs:
        rel = norm_zh_rel("index.html", ref)
        if not rel:
            raise RuntimeError(f"中华文明原站目录引用无效：{ref}")
        verified[rel] = _fetch_zhonghua_catalog_verified(base, ref)
    return verified


def zh_catalog_loader_references(source: str) -> tuple[str, list[str]]:
    """Read the versioned data and script URLs from the upstream loader."""
    base_match = re.search(r"\bfetch\((['\"])([^'\"]+\.json\.gz(?:\?[^'\"]*)?)\1\)", source)
    if not base_match:
        raise ValueError("catalog-loader.js has no gzip catalog reference")
    base_ref = base_match.group(2)
    base_rel = norm_zh_rel("catalog-loader.js", base_ref)
    if not base_rel or not base_rel.endswith(".json.gz"):
        raise ValueError("catalog-loader.js has an unsafe catalog reference")

    marker = "for(const src of " if "for(const src of " in source else "const __jtLoads="
    pos = source.find(marker)
    if pos < 0:
        raise ValueError("catalog-loader.js has no ordered script list")
    raw_list, _ = json.JSONDecoder().raw_decode(source[pos + len(marker):])
    if not isinstance(raw_list, list) or not raw_list:
        raise ValueError("catalog-loader.js has an empty script list")
    scripts = []
    normalized = []
    for raw in raw_list:
        rel = norm_zh_rel("catalog-loader.js", raw) if isinstance(raw, str) else None
        if not rel or not rel.endswith(".js"):
            raise ValueError(f"catalog-loader.js has an unsafe script reference: {raw!r}")
        scripts.append(raw)
        normalized.append(rel)
    if len(normalized) != len(set(normalized)):
        raise ValueError("catalog-loader.js has duplicate script references")
    return base_ref, scripts


def zh_catalog_loader_dependencies(source: str) -> tuple[str, list[str]]:
    """Return safe local paths in the loader's execution order."""
    base_ref, scripts = zh_catalog_loader_references(source)
    return (norm_zh_rel("catalog-loader.js", base_ref),
            [norm_zh_rel("catalog-loader.js", ref) for ref in scripts])


def optimize_zh_catalog_loader(data: bytes) -> bytes:
    """Fetch scripts together while preserving their original execution order, with fast-catalog hook."""
    source = data.decode("utf-8")
    zh_catalog_loader_dependencies(source)
    if "const __jtLoads=" in source and "window.__JT_CATALOG_READY__=" in source and "__JT_SKIP_P2__" in source:
        return data
    if source.startswith("window.__JT_CATALOG_READY__="):
        source = source[len("window.__JT_CATALOG_READY__="):]
    if "const __jtLoads=" in source and "__JT_SKIP_P2__" not in source:
        m_prev = re.search(
            r"const __jtLoads=(\[.*?\])\.map\(src=>new Promise\(\(resolve,reject\)=>\{const script=document\.createElement\('script'\);script\.async=false;script\.src=src;script\.onload=resolve;script\.onerror=\(\)=>reject\(Error\('脚本加载失败：'\+src\)\);document\.body\.append\(script\)\}\)\);await Promise\.all\(__jtLoads\);",
            source,
            flags=re.S,
        )
        if not m_prev:
            raise ValueError("unknown previously-patched catalog-loader.js shape")
        source_list = m_prev.group(1)
        span_s, span_e = m_prev.span()
    else:
        marker = "for(const src of "
        start = source.find(marker)
        if start < 0 or not source.startswith("(async()=>{"):
            raise ValueError("unknown catalog-loader.js shape; refusing an unsafe rewrite")
        list_start = start + len(marker)
        _, consumed = json.JSONDecoder().raw_decode(source[list_start:])
        list_end = list_start + consumed
        old_tail = ")await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=src;script.onload=resolve;script.onerror=()=>reject(Error('脚本加载失败：'+src));document.body.append(script)});"
        if not source.startswith(old_tail, list_end):
            raise ValueError("unknown catalog-loader.js loading loop; refusing an unsafe rewrite")
        source_list = source[list_start:list_end]
        span_s, span_e = start, list_end + len(old_tail)

    replacement = (
        "const __jtLoads=" + source_list
        + ".filter(src=>!(typeof window!=='undefined'&&window.__JT_SKIP_P2__&&window.__JT_SKIP_P2__(src)))"
        + ".map(src=>new Promise((resolve,reject)=>{const script=document.createElement('script');"
        + "script.async=false;script.src=src;script.onload=resolve;"
        + "script.onerror=()=>reject(Error('脚本加载失败：'+src));document.body.append(script)}));"
        + "await Promise.all(__jtLoads);"
    )
    patched = source[:span_s] + replacement + source[span_e:]
    m_fetch_block = re.search(
        r"""(const response=await fetch\((['"])([^'"]+\.json\.gz(?:\?[^'"]*)?)\2\);.*?window\.ARCHIVE_DATA=JSON\.parse\(await new Response\(decoded\)\.text\(\)\);)""",
        patched,
        flags=re.S,
    )
    if m_fetch_block and "__JT_FAST_ARCHIVE_PROMISE__" not in patched:
        orig_block = m_fetch_block.group(1)
        fast_block = (
            "if(typeof window!=='undefined'&&window.__JT_FAST_ARCHIVE_PROMISE__){"
            "window.__JT_BASE_CATALOG_URL__=" + json.dumps(m_fetch_block.group(3)) + ";"
            "window.ARCHIVE_DATA=await window.__JT_FAST_ARCHIVE_PROMISE__;"
            "}else{" + orig_block + "}"
        )
        patched = patched[:m_fetch_block.start()] + fast_block + patched[m_fetch_block.end():]
    return ("window.__JT_CATALOG_READY__=" + patched).encode("utf-8")


def validate_zh_catalog_downloads(site_dir: Path, loader: str, fetched: set[str]) -> int:
    """Fail before committing if any current catalog dependency was not fetched."""
    base_rel, scripts = zh_catalog_loader_dependencies(loader)
    required = ["catalog-loader.js", base_rel, *scripts]
    missing = [rel for rel in required if rel not in fetched or not (site_dir / rel).is_file() or not (site_dir / rel).stat().st_size]
    if missing:
        raise RuntimeError("incomplete zhonghua catalog; missing: " + ", ".join(missing))
    try:
        catalog_path = site_dir / base_rel
        with catalog_path.open("rb") as raw:
            magic = raw.read(2)
        if magic == b"\x1f\x8b":
            with gzip.open(catalog_path, "rb") as catalog:
                while catalog.read(1024 * 1024):
                    pass
        else:
            json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, EOFError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("invalid zhonghua gzip catalog") from error
    return len(scripts)


_ZH_LOCAL_MEDIA_RE = re.compile(
    r'"((?:\./)?(?:assets|(?:[A-Za-z0-9_-]+-)?images|research-[A-Za-z0-9_-]+)/[^"\\\s?#]+)(?:\?[^"\\\s#]*)?"'
)


def discover_zh_catalog_media(data: bytes) -> set[str]:
    """Find local image paths embedded in the new compressed catalog."""
    raw = gzip.decompress(data) if data.startswith(b"\x1f\x8b") else data
    catalog_text = raw.decode("utf-8")
    media_exts = {".webp", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".woff", ".woff2"}
    found = set()
    for match in _ZH_LOCAL_MEDIA_RE.finditer(catalog_text):
        rel = norm_zh_rel("catalog-base.json.gz", match.group(1))
        if rel and os.path.splitext(rel)[1].lower() in media_exts:
            found.add(rel)
    return found


SHANG_ALL_BUILD_REV = "20261124a"
SHANG_ALL_INPUTS = ("scripts/shang_all.template.html", "shang-all.js", "shang.css")


def shang_all_input_fingerprint(site_dir: Path) -> str:
    """Regenerate the scoped page when its template, script or CSS changes."""
    digest = hashlib.sha256(SHANG_ALL_BUILD_REV.encode("ascii"))
    for rel in SHANG_ALL_INPUTS:
        path = site_dir / rel
        if not path.is_file() or not path.stat().st_size:
            raise RuntimeError(f"missing Shang full-catalog input: {rel}")
        digest.update(rel.encode("utf-8") + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def build_shang_all_snapshot(site_dir: Path, catalog_path: Path) -> dict:
    """Create a small, deterministic page from every current era=商 record."""
    shang_all_input_fingerprint(site_dir)
    version_path = site_dir / "site-version.json"
    if not version_path.is_file():
        raise RuntimeError("missing site-version.json for Shang full catalog")
    revision = json.loads(version_path.read_text(encoding="utf-8")).get("revision", "")
    if not re.fullmatch(r"[0-9a-f]{64}", revision):
        raise RuntimeError("invalid site-version revision for Shang full catalog")
    catalog_bytes = catalog_path.read_bytes()
    decoded = gzip.decompress(catalog_bytes) if catalog_bytes.startswith(b"\x1f\x8b") else catalog_bytes
    catalog = json.loads(decoded)
    if not isinstance(catalog.get("records"), list):
        raise RuntimeError("Shang source catalog has no records array")
    records = [record for record in catalog["records"] if isinstance(record, dict) and record.get("era") == "商"]
    ids = [record.get("id") for record in records]
    if not records or any(not isinstance(id_, str) or not id_ for id_ in ids) or len(ids) != len(set(ids)):
        raise RuntimeError("Shang full catalog is empty or has invalid/duplicate IDs")
    payload = {
        "version": catalog.get("version"),
        "revision": revision,
        "scope": "era=商",
        "sourcePolicy": catalog.get("sourcePolicy"),
        "periods": [p for p in catalog.get("periods", []) if isinstance(p, dict) and p.get("name") == "商"],
        "sourceRevision": revision,
        "count": len(records),
        "records": records,
    }
    json_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, compresslevel=6, mtime=0) as archive:
        archive.write(json_bytes)
    compressed = buffer.getvalue()
    data_hash = sha256_bytes(compressed)[:12]
    template = (site_dir / "scripts" / "shang_all.template.html").read_text(encoding="utf-8")
    substitutions = {
        "GATE": make_gate_script("金泰 AI · 中华文明影像库"),
        "SHIM": ZH_SHIM,
        "REVISION": revision,
        "COUNT": str(len(records)),
        "JS_HASH": sha256_bytes((site_dir / "shang-all.js").read_bytes())[:12],
        "CSS_HASH": sha256_bytes((site_dir / "shang.css").read_bytes())[:12],
        "DATA_HASH": data_hash,
    }
    if any("{{" + key + "}}" not in template for key in substitutions):
        raise RuntimeError("Shang full-catalog template is missing required placeholders")
    html = template
    for key, value in substitutions.items():
        html = html.replace("{{" + key + "}}", value)
    if re.search(r"\{\{[A-Z_]+\}\}", html) or 'id="jt-unified-gate"' not in html:
        raise RuntimeError("Shang full-catalog template did not render safely")
    outputs = {
        "shang-all-data.json.gz": compressed,
        "shang-all.html": html.encode("utf-8"),
    }
    for rel, content in outputs.items():
        path = site_dir / rel
        if not path.is_file() or path.read_bytes() != content:
            path.write_bytes(content)
    check_html_js_syntax(site_dir / "shang-all.html")
    return {"count": len(records), "data_hash": data_hash, "revision": revision}


def shang_all_snapshot_ready(site_dir: Path) -> bool:
    """Guard the no-op sync path against missing or stale scoped output."""
    try:
        shang_all_input_fingerprint(site_dir)
        page = (site_dir / "shang-all.html").read_text(encoding="utf-8")
        data = (site_dir / "shang-all-data.json.gz").read_bytes()
        revision = json.loads((site_dir / "site-version.json").read_text(encoding="utf-8"))["revision"]
        payload = json.loads(gzip.decompress(data))
        records = payload["records"]
        count = len(records)
        return (
            bool(count)
            and payload.get("count") == count
            and payload.get("sourceRevision") == revision
            and payload.get("revision") == revision
            and all(isinstance(r, dict) and r.get("era") == "商" for r in records)
            and all(isinstance(r.get("id"), str) and r.get("id") for r in records)
            and len({r.get("id") for r in records}) == count
            and f'name="atlas-snapshot-revision" content="{revision}"' in page
            and f'name="shang-all-data-hash" content="{sha256_bytes(data)[:12]}"' in page
            and f'shang-all.js?v={sha256_bytes((site_dir / "shang-all.js").read_bytes())[:12]}' in page
            and f'shang.css?v={sha256_bytes((site_dir / "shang.css").read_bytes())[:12]}' in page
            and 'id="jt-unified-gate"' in page
        )
    except (OSError, KeyError, TypeError, ValueError, EOFError):
        return False


def shang_all_index_ready(site_dir: Path) -> bool:
    try:
        page = (site_dir / "index.html").read_text(encoding="utf-8")
        return ('id="jt-shang-all-route"' in page
                and 'id="jt-shang-all-link"' in page
                and page.index('id="jt-shang-all-route"') < page.index('id="jt-unified-gate"'))
    except (OSError, ValueError):
        return False


ZH_OLD_UNPACK_1 = '((k,d,x)=>{const u=v=>{if(Array.isArray(v))return v.map(u);if(!v||typeof v!=="object")return v;if(Object.hasOwn(v,"$s"))return d[v.$s];const a=v.$o,p=[];for(let i=0;i<a.length;i+=2)p.push([k[a[i]],u(a[i+1])]);return Object.fromEntries(p)};return u(x)})'
ZH_NEW_UNPACK_1 = '((k,d,x)=>{const u=v=>{if(Array.isArray(v)){const n=v.length,r=new Array(n);for(let i=0;i<n;i++)r[i]=u(v[i]);return r}if(!v||typeof v!=="object")return v;if(v.$s!==undefined)return d[v.$s];const a=v.$o,o={};for(let i=0;i<a.length;i+=2)o[k[a[i]]]=u(a[i+1]);return o};return u(x)})'
ZH_OLD_UNPACK_2 = '((d,x)=>{const u=v=>Array.isArray(v)?v.map(u):v&&typeof v==="object"?(Object.hasOwn(v,"$s")?d[v.$s]:Object.fromEntries(Object.entries(v).map(([k,w])=>[k,u(w)]))):v;return u(x)})'
ZH_NEW_UNPACK_2 = '((d,x)=>{const u=v=>{if(Array.isArray(v)){const n=v.length,r=new Array(n);for(let i=0;i<n;i++)r[i]=u(v[i]);return r}if(!v||typeof v!=="object")return v;if(v.$s!==undefined)return d[v.$s];const o={};for(const k in v)o[k]=u(v[k]);return o};return u(x)})'
ZH_CONCAT_PREFIX = "window.ARCHIVE_DATA.records=window.ARCHIVE_DATA.records.concat("
ZH_DEFERRED_P2 = {
    "culture-notes.js",
    "expansion-audit.js",
    "expansion-candidates.js",
    "expansion-queue.js",
    "expansion-control.js",
    "expansion-control-ui.js",
}


ZH_FAST_DETAIL_ONLY_KEYS = {
    "citation", "verification", "previewVerification", "sourceMetadata", "rights", "rightsUrl",
    "additionalSources", "provenance", "apiUrl", "verifiedAt", "sourceType", "physicalDescription",
    "dimensions", "documentPage", "originalMaterial", "originalDate", "imageViewDescription",
    "datingBasis", "metPeriodNote", "sourceRecordSha256", "imageSha256", "rightsEvidence",
    "sourceEvidence", "thumbnailUrl", "previewHash", "sourceHttpBodySha256", "localEvidenceImage",
    "fileHash", "reconciliation",
}


def prune_retired_zhonghua_chunks(site_dir: Path) -> list[str]:
    """Remove unreferenced legacy data.js & catalog-records-*.js once catalog-loader.js is active."""
    idx_p = site_dir / "index.html"
    if not idx_p.is_file() or not (site_dir / "catalog-loader.js").is_file() or not (site_dir / "catalog-base.json.gz").is_file():
        return []
    if "catalog-loader.js" not in idx_p.read_text(encoding="utf-8", errors="ignore"):
        return []
    candidates = [p for p in sorted(site_dir.glob("catalog-records-*.js"))]
    if (site_dir / "data.js").is_file():
        candidates.append(site_dir / "data.js")
    if not candidates:
        return []
    cand_names = {p.name for p in candidates}
    referenced = set()
    for doc in list(site_dir.rglob("*.html")) + list(site_dir.glob("*.js")):
        if ".git" in doc.parts or doc.name in cand_names:
            continue
        txt = doc.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"(?<![A-Za-z0-9_-])(data\.js|catalog-records-\d+\.js)\b", txt):
            referenced.add(m.group(1))
    removed = []
    for p in candidates:
        if p.name not in referenced:
            p.unlink(missing_ok=True)
            removed.append(p.name)
    return removed


def build_zhonghua_fast_catalog(site_dir: Path) -> dict | None:
    """Build deterministic columnar catalog-fast.json.gz (~65% smaller) for instant t=0 hydration."""
    from collections import Counter
    loader_p = site_dir / "catalog-loader.js"
    if not loader_p.is_file():
        return None
    try:
        catalog_rel, scripts = zh_catalog_loader_dependencies(loader_p.read_text(encoding="utf-8"))
    except Exception:
        return None
    cat_p = site_dir / catalog_rel
    if not cat_p.is_file():
        return None
    raw_b = cat_p.read_bytes()
    dec_b = gzip.decompress(raw_b) if raw_b.startswith(b"\x1f\x8b") else raw_b
    obj = json.loads(dec_b.decode("utf-8"))
    recs = obj.get("records")
    if not isinstance(recs, list) or not recs:
        return None

    p1_props = {
        "id", "catalogNumber", "title", "originalTitle", "era", "polity", "date", "originalPeriod",
        "material", "institution", "institutionShort", "objectNumber", "category", "evidence",
        "openLicense", "localImage", "previewUrl", "imageUrl", "originalImageUrl", "displayMode",
        "imageCredit", "tangPhase", "xiaScope", "crosses1227", "crossesDeclaredPeriod",
        "dateDisputed", "visualScope", "metPeriodVersion", "periodReview", "lifeFocus",
        "lifeScenes", "socialGroups", "batch", "batchId", "sourceTitle", "sourceUrl",
        "provenanceKind", "locator", "publicationLabel", "visualSubcategoryLabels", "subjects",
        "relatedCategories", "visibleDetails", "sceneUse", "description", "notes", "findspot",
        "imageObjectDate", "historicalDate", "chronologyRelation", "rulerLinks",
    }
    p2_all = ZH_DEFERRED_P2 | {"library-quality-ui.js"}
    for s in scripts:
        fn = os.path.basename(s)
        if fn in p2_all or fn.endswith("-data.js") or not (site_dir / s).is_file():
            continue
        stxt = (site_dir / s).read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"\b(?:r|rec|record|item|x)\.([A-Za-z_][A-Za-z0-9_]*)", stxt):
            p1_props.add(m.group(1))

    all_keys = set()
    for r in recs:
        if isinstance(r, dict):
            all_keys.update(r.keys())
    cols = sorted((all_keys & p1_props) - ZH_FAST_DETAIL_ONLY_KEYS)

    str_counts = Counter()
    for r in recs:
        loc_img = r.get("localImage")
        has_hosted_local = isinstance(loc_img, str) and bool(loc_img) and not loc_img.startswith("research-")
        for c in cols:
            v = r.get(c)
            if v is None:
                continue
            if has_hosted_local and c in ("previewUrl", "imageUrl", "originalImageUrl"):
                continue
            if c == "previewUrl" and v == loc_img:
                continue
            if c == "originalImageUrl" and v == r.get("imageUrl"):
                continue
            if isinstance(v, str) and len(v) >= 3:
                str_counts[v] += 1

    str_list = [s for s, cnt in str_counts.most_common() if cnt >= 3 and len(s) * (cnt - 1) > 12]
    str_to_id = {s: idx for idx, s in enumerate(str_list)}

    rows = []
    cma_pins = {}
    for idx_r, r in enumerate(recs):
        if "cma-101711" in str(r.get("id", "")) and "sourceRecordSha256" in r:
            cma_pins[str(idx_r)] = r["sourceRecordSha256"]
        loc_img = r.get("localImage")
        has_hosted_local = isinstance(loc_img, str) and bool(loc_img) and not loc_img.startswith("research-")
        img_url = r.get("imageUrl")
        row = []
        for c in cols:
            v = r.get(c)
            if v is None or (has_hosted_local and c in ("previewUrl", "imageUrl", "originalImageUrl")):
                row.append(None)
            elif c == "previewUrl" and v == loc_img:
                row.append(-1)
            elif c == "originalImageUrl" and v == img_url:
                row.append(-2)
            elif isinstance(v, str) and v in str_to_id:
                row.append(chr(1) + format(str_to_id[v], "x"))
            else:
                row.append(v)
        while row and row[-1] is None:
            row.pop()
        rows.append(row)

    meta = {k: v for k, v in obj.items() if k != "records"}
    pack = {"v": 1, "meta": meta, "cols": cols, "dict": str_list, "rows": rows, "cmaPins": cma_pins}
    raw_out = json.dumps(pack, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, compresslevel=6, mtime=0) as gz:
        gz.write(raw_out)
    gz_bytes = buf.getvalue()
    out_p = site_dir / "catalog-fast.json.gz"
    if not out_p.is_file() or out_p.read_bytes() != gz_bytes:
        out_p.write_bytes(gz_bytes)
    p1_urls = [
        f"./{s}?v={sha256_bytes((site_dir / s).read_bytes())[:12]}"
        for s in scripts
        if os.path.basename(s) not in p2_all and (site_dir / s).is_file()
    ]
    p2_urls = [
        f"./{s}?v={sha256_bytes((site_dir / s).read_bytes())[:12]}"
        for s in scripts
        if os.path.basename(s) in p2_all and (site_dir / s).is_file()
    ]
    return {
        "fast_hash": sha256_bytes(gz_bytes)[:12],
        "fast_bytes": len(gz_bytes),
        "p1_urls": p1_urls,
        "p2_urls": p2_urls,
    }


ZH_FAST_CHRONOLOGY_CORE = "/* One attribution rule is shared by navigation counts, galleries and exports. */\n(function(root){\n  const _normCache=new Map();\n  const normalize=s=>{const str=String(s??'');let v=_normCache.get(str);if(v===undefined){v=str.normalize('NFKC').replace(/[祐佑]/g,'祐').replace(/\\s/g,'');if(_normCache.size<20000)_normCache.set(str,v);}return v;};\n  const valid=v=>typeof v==='number'&&Number.isFinite(v)&&v!==0;\n  const year=y=>y<0?'前'+Math.abs(y):String(y);\n  const years=(a,b)=>valid(a)&&valid(b)?(a===b?year(a):year(a)+'–'+year(b))+'年':'';\n  const samePolity=(r,n)=>r.era===n.parentEra&&(n.parentEra==='唐'?(['date-bucket','undated','collection'].includes(n.kind)||!r.polity||r.polity===(n.polity||n.parentEra)):(!n.polity||n.polity===n.parentEra||r.polity===n.polity));\n  const contained=(d,n)=>d.points?.length?d.points.some(y=>y>=n.start&&y<=n.end):d.start>=n.start&&d.end<=n.end;\n  function spans(entries){\n    const out=[];\n    for(const e of entries.filter(e=>!e.indexOnly&&valid(e.start)&&valid(e.end)).sort((a,b)=>a.start-b.start)){\n      const last=out.at(-1);\n      if(last&&e.start<=last.end+1)last.end=Math.max(last.end,e.end);else out.push({start:e.start,end:e.end});\n    }\n    return out;\n  }\n  function hasRecId(node,id){\n    const arr=node.recordIds;if(!arr)return false;\n    if(node._recSet&&node._recSetSrc===arr)return node._recSet.has(id);\n    node._recSetSrc=arr;node._recSet=new Set(arr);return node._recSet.has(id);\n  }\n  function create(data,records){\n    const entries=data.entries||[],overrides=data.recordDates||{},audit=data.recordAttribution||{};\n    const effPolity=r=>audit[r.id]?.polity||r.polity;\n    const inPolity=(r,n)=>{const ep=audit[r.id]?.polity;return samePolity(ep?{era:r.era,polity:ep}:r,n);};\n    const dates=new Map,entriesByEra=new Map,recordsByEra=new Map,scopeCache=new Map,countCache=new Map,unassigned=new Map;\n    for(const e of entries){\n      e._normReign=e.reign?normalize(e.reign):'';\n      if(!entriesByEra.has(e.parentEra))entriesByEra.set(e.parentEra,[]);\n      entriesByEra.get(e.parentEra).push(e);\n    }\n    for(const r of records){\n      if(!recordsByEra.has(r.era))recordsByEra.set(r.era,[]);\n      recordsByEra.get(r.era).push(r);\n    }\n    function getScope(era,pol){\n      const key=(era||'')+'\\0'+(pol||'');\n      let sc=scopeCache.get(key);\n      if(sc)return sc;\n      const probe={era,polity:pol};\n      const es=(entriesByEra.get(era)||[]).filter(e=>samePolity(probe,e)&&!e.indexOnly);\n      const rulerIds=[...new Set(es.map(e=>e.rulerId).filter(Boolean))];\n      const rulerMeta=rulerIds.map(id=>{\n        const children=es.filter(e=>e.rulerId===id);\n        return {id,childIds:new Set(children.map(c=>c.id)),spans:spans(children)};\n      });\n      sc={es,datedEs:es.filter(e=>!e.recordIds&&valid(e.start)&&valid(e.end)),rulerMeta};\n      scopeCache.set(key,sc);\n      return sc;\n    }\n    const eligible=r=>!!r.sourceUrl&&!r.contextOnly&&!r.dateDisputed&&!['conditional','later-comparison'].includes(r.visualScope)&&!audit[r.id]?.contextOnly&&(!r.dateRelation||r.dateRelation==='object')&&(!audit[r.id]?.relation||audit[r.id].relation==='object');\n    for(const r of records){\n      const sc=getScope(r.era,effPolity(r)),es=sc.es;\n      const broad=/未细分|未作更细|朝代宽断代|不是制造纪年/.test((r.date||'')+(r.datePrecision||''));\n      const override=r.era==='唐'&&(r.historicalRange||valid(r.dateStart)&&valid(r.dateEnd))&&!overrides[r.id]?.attribution?null:overrides[r.id];\n      let d=override?{...override}:r.historicalRange?{...r.historicalRange}:valid(r.dateStart)&&valid(r.dateEnd)&&!broad?{start:r.dateStart,end:r.dateEnd,note:r.datePrecision||r.datingBasis||'来源著录的年代范围'}:null;\n      if(r.id==='arch-tang-foguang-landscape'&&d)d={...d,relation:'foundation',note:'857为东大殿创建纪年；建筑群现状含后世遗存，只作历史关联。'};\n      const normRDate=es.length&&r.date?normalize(r.date):'';\n      const named=normRDate?es.filter(e=>e._normReign&&normRDate.includes(e._normReign)&&(!d||d.start<=e.end&&d.end>=e.start)):[];\n      if(!d&&named.length===1&&!broad&&!r.contextOnly&&valid(named[0].start)&&valid(named[0].end))d={start:named[0].start,end:named[0].end,note:'来源著录标明年号；公元范围据纪年目录对照'};\n      if(d){\n        d.relation=audit[r.id]?.relation||r.dateRelation||d.relation||'object';\n        d.contextOnly=!eligible(r);\n        d.reignIds=d.reignIds?.length?d.reignIds:d.ignoreOriginalReign?[]:r.reignIds?.length?r.reignIds:named.map(e=>e.id);\n        d.note=audit[r.id]?.note||d.note;\n        const rSet=d.reignIds.length?new Set(d.reignIds):null;\n        let possibleCount=0;\n        if(!d.points?.length){\n          for(const e of sc.datedEs){if((!rSet||rSet.has(e.id))&&contained(d,e)){if(++possibleCount>1)break;}}\n        }\n        d.ambiguousReign=!d.points?.length&&possibleCount>1;\n        let possibleRulerCount=0;\n        if(!d.points?.length){\n          for(const rm of sc.rulerMeta){\n            if((!rSet||d.reignIds.some(rid=>rm.childIds.has(rid)))&&rm.spans.some(n=>contained(d,n))){\n              if(++possibleRulerCount>1)break;\n            }\n          }\n        }\n        d.ambiguousRuler=!d.points?.length&&possibleRulerCount>1;\n      }\n      dates.set(r.id,d);\n    }\n    function match(r,node,mode='contained'){\n      if(!r||!node||!inPolity(r,node))return false;\n      if(node.parentEra==='唐'&&node.kind==='date-bucket')return hasRecId(node,r.id);\n      if(node.kind==='collection')return hasRecId(node,r.id);\n      if(node.kind==='undated'){\n        if(!unassigned.has(r.id))unassigned.set(r.id,!(entriesByEra.get(r.era)||[]).some(e=>match(r,e._asNode||(e._asNode={...e,kind:e.kind||'reign'}),'contained')));\n        return unassigned.get(r.id);\n      }\n      if(node.indexOnly)return false;\n      const d=dates.get(r.id);\n      if(mode==='contained'&&node.kind==='reign'&&d?.rulerOnly)return false;\n      if(node.kind==='ruler'&&d?.rulerIds?.length&&!d.rulerIds.includes(node.id))return false;\n      if(mode==='contained'&&(!eligible(r)||d?.contextOnly||d?.relation&&d.relation!=='object'))return false;\n      if(node.recordIds){\n        if(!hasRecId(node,r.id)||node.qinRulerId&&!(r.qinRulerLinks||[]).some(l=>l.id===node.qinRulerId&&l.relation==='direct'))return false;\n        if(d&&valid(d.start)&&valid(d.end)&&valid(node.start)&&valid(node.end))return contained(d,node);\n        return true;\n      }\n      if(!d||!valid(d.start)||!valid(d.end)||!valid(node.start)||!valid(node.end))return false;\n      if(Boolean(d.relation&&d.relation!=='object')!==(mode==='context'))return false;\n      if(node.kind==='reign'&&d.reignIds?.length&&!d.reignIds.includes(node.id))return false;\n      if(node.kind==='ruler'&&node.entries&&d.reignIds?.length&&!node.entries.some(e=>d.reignIds.includes(e.id)))return false;\n      if(mode==='contained'&&(node.kind==='reign'&&d.ambiguousReign||node.kind==='ruler'&&d.ambiguousRuler))return false;\n      const ranges=node.kind==='ruler'&&node.entries?(node._spans||(node._spans=spans(node.entries))):[node];\n      return ranges.some(n=>mode==='overlap'?d.points?.length?d.points.some(y=>y>=n.start&&y<=n.end):d.start<=n.end&&d.end>=n.start:contained(d,n));\n    }\n    function reason(r){\n      const d=dates.get(r.id);\n      if(audit[r.id]?.note)return audit[r.id].note;\n      if(!eligible(r)||d?.contextOnly||d?.relation&&d.relation!=='object')return '关联背景、载体差异或存疑资料，不能作为具体纪年的直接图证';\n      if(!d)return '来源未提供可归入具体纪年的断代';\n      if(d.ambiguousReign)return '同年改元或纪年重叠，现有依据无法唯一确定年号';\n      return '原始断代跨度超过单个纪年，或尚无明确的纪年归属依据';\n    }\n    function explain(r,node){\n      if(node?.kind==='undated')return reason(r);\n      const d=dates.get(r.id);\n      if(node?.qinRulerId)return (r.qinRulerLinks||[]).find(l=>l.id===node.qinRulerId&&l.relation==='direct')?.reason||'以直接纪年和铭文为据';\n      if(node?.recordIds)return '依据馆藏、铭文或考古分期关联；未推定公元确年';\n      if(d?.points?.length)return '依据分立题记年份 '+d.points.filter(y=>y>=node.start&&y<=node.end).map(year).join('、')+'；不是连续制作年代';\n      return (d?.note||'来源断代完整落入所选时期')+'（'+years(d?.start,d?.end)+'）';\n    }\n    function count(node,mode='contained'){\n      if(!node)return 0;\n      const key=[node.id,node.kind,node.start,node.end,node.polity,mode].join('|');\n      if(!countCache.has(key)){\n        const bucket=recordsByEra.get(node.parentEra)||[];\n        let cnt=0;\n        for(let i=0;i<bucket.length;i++)if(match(bucket[i],node,mode))cnt++;\n        countCache.set(key,cnt);\n      }\n      return countCache.get(key);\n    }\n    return {dates,match,count,explain,reason};\n  }\n  const api={normalize,year,years,create};root.ChronologyCore=api;\n  if(typeof module!=='undefined'&&module.exports)module.exports=api;\n})(typeof window==='undefined'?globalThis:window);\n"


def optimize_zhonghua_js_bytes(rel: str, data: bytes) -> bytes:
    if os.path.basename(rel) == "chronology-core.js" and b"root.ChronologyCore=api" in data:
        return ZH_FAST_CHRONOLOGY_CORE.encode("utf-8")
    if os.path.basename(rel) == "chronology.js" and b"function renderChronology(){" in data:
        t_ch = data.decode("utf-8")
        if "__JT_DEFER_CHRON__" not in t_ch:
            t_ch = re.sub(
                r"(function\s+renderChronology\(\)\s*\{\s*if\s*\(!chronologyIndex)\)(\s*return;)",
                r"\1||(typeof window!=='undefined'&&window.__JT_DEFER_CHRON__))\2",
                t_ch,
                count=1,
            )
        return t_ch.encode("utf-8")
    if os.path.basename(rel) == "catalog-loader.js":
        return optimize_zh_catalog_loader(data)
    if not rel.endswith(".js") or len(data) < 4096:
        return data
    try:
        txt = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    orig = txt
    if ZH_OLD_UNPACK_1 in txt:
        txt = txt.replace(ZH_OLD_UNPACK_1, ZH_NEW_UNPACK_1)
    if ZH_OLD_UNPACK_2 in txt:
        txt = txt.replace(ZH_OLD_UNPACK_2, ZH_NEW_UNPACK_2)
    base_name = os.path.basename(rel)
    if base_name.startswith("catalog-records-") and txt.startswith(ZH_CONCAT_PREFIX):
        stripped = txt.rstrip()
        if stripped.endswith(");"):
            inner = stripped[len(ZH_CONCAT_PREFIX):-2]
            txt = (
                "{const _r=window.ARCHIVE_DATA.records,_c=("
                + inner
                + ");for(let _i=0,_n=_c.length;_i<_n;_i++)_r.push(_c[_i]);"
                "if(window.__jtSanitizePack)window.__jtSanitizePack(window.ARCHIVE_DATA);}\n"
            )
    return txt.encode("utf-8") if txt != orig else data


def _build_zh_async_loader_tag(all_srcs: list[str], p1: list[str], p2: list[str]) -> str:
    import html as _html
    a_attr = _html.escape(json.dumps(all_srcs, ensure_ascii=False, separators=(",", ":")), quote=True)
    p1_attr = _html.escape(json.dumps(p1, ensure_ascii=False, separators=(",", ":")), quote=True)
    p2_attr = _html.escape(json.dumps(p2, ensure_ascii=False, separators=(",", ":")), quote=True)
    code = (
        "(function(){"
        "if(window.__JT_LOCKED__)return;"
        "var me=document.getElementById('jt-zh-async-loader');if(!me)return;"
        "var p1=JSON.parse(me.getAttribute('data-p1')||'[]'),p2=JSON.parse(me.getAttribute('data-p2')||'[]');"
        "if(location.hash==='#expansion'&&p2.length){p1=p1.concat(p2);p2=[];}"
        "var pendingAct=null;"
        "function showPreToast(m){var t=document.getElementById('toast');if(t){t.textContent=m;t.classList.add('show');}}"
        "document.addEventListener('click',function(e){"
        "if(window.__JT_HYDRATED__)return;"
        "var t=e.target;if(!t||!t.closest)return;"
        "if(t.closest('[data-save]')||t.closest('a[href]'))return;"
        "var b=t.closest('[data-detail]');"
        "if(!b){var cd=t.closest('article.card');if(cd)b=cd.querySelector('[data-detail]');}"
        "if(b){e.preventDefault();pendingAct={t:'detail',v:b.getAttribute('data-detail')};showPreToast('正在载入文物考证详情…');return;}"
        "for(var k of ['era','category','view']){var fb=t.closest('[data-'+k+']');if(fb){e.preventDefault();pendingAct={t:k,v:fb.getAttribute('data-'+k)};showPreToast('正在载入分类筛选…');return;}}"
        "},true);"
        "function loadTag(u){return new Promise(function(res){var s=document.createElement('script');s.src=u;s.onload=function(){res(true);};s.onerror=function(){res(false);};document.head.appendChild(s);});}"
        "async function runList(list){if(!list.length)return;if(location.protocol==='file:'){for(var i=0;i<list.length;i++)await loadTag(list[i]);return;}"
        "var tasks=list.map(function(u){return fetch(u).then(function(r){if(!r.ok)throw new Error(r.status);return r.text();});});"
        "for(var j=0;j<list.length;j++){try{var c=await tasks[j];var s=document.createElement('script');s.textContent=c+'\\n//# sourceURL='+list[j];document.head.appendChild(s);s.remove();if(c.length>2000000)await new Promise(function(r){setTimeout(r,0);});}catch(err){await loadTag(list[j]);}}}"
        "async function replayPending(allowP2){"
        "if(!pendingAct)return;"
        "var act=pendingAct;"
        "if(act.t==='detail'&&typeof window.detail==='function'){"
        "try{window.detail(act.v);}catch(e){}"
        "var dlg=document.getElementById('detailDialog');"
        "if(dlg&&dlg.open){pendingAct=null;return;}"
        "if(allowP2&&p2.length){var rest=p2.slice();p2=[];await runList(rest);if(window.__jtSanitizeAll)window.__jtSanitizeAll();try{window.detail(act.v);}catch(e){}}"
        "pendingAct=null;"
        "}else if(act.t!=='detail'){"
        "pendingAct=null;"
        "var sel='[data-'+act.t+'=\"'+String(act.v).replace(/\"/g,'\\\\\"')+'\"]';"
        "var el=document.querySelector(sel);if(el)try{el.click();}catch(e){}"
        "}"
        "}"
        "async function boot(){await runList(p1);if(window.__JT_CATALOG_READY__)await window.__JT_CATALOG_READY__;if(window.__JT_DEFER_CHRON__){window.__JT_DEFER_CHRON__=false;if(typeof renderChronology==='function')renderChronology();}"
        "if(window.__jtSanitizeAll)window.__jtSanitizeAll();window.__JT_HYDRATED__=true;"
        "if(window.__jtInstallDetailHydrator)window.__jtInstallDetailHydrator();"
        "if(['#tangReignDossier','#xixiaReignDossier'].indexOf(location.hash)!==-1)window.dispatchEvent(new Event('load'));"
        "await replayPending(true);"
        "var bg=function(){var extra=(window.__JT_DEFERRED_P2_URLS__||[]).concat(p2);p2=[];runList(extra).then(function(){if(window.__jtEnsureFullCatalog)window.__jtEnsureFullCatalog();});};"
        "if(typeof requestIdleCallback==='function')requestIdleCallback(bg,{timeout:500});else setTimeout(bg,250);}"
        "if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){setTimeout(boot,0);},{once:true});else setTimeout(boot,0);"
        "})();"
    )
    return f'<script id="jt-zh-async-loader" data-all="{a_attr}" data-p1="{p1_attr}" data-p2="{p2_attr}">{code}</script>'


def _compute_zhonghua_ssg_payload(site_dir: Path) -> dict | None:
    index_path = site_dir / "index.html"
    if not index_path.is_file():
        return None
    new_catalog = "catalog-loader.js" in index_path.read_text(encoding="utf-8", errors="ignore")
    catalog_rel = zh_catalog_loader_dependencies((site_dir / "catalog-loader.js").read_text(encoding="utf-8"))[0] if new_catalog else "data.js"
    if not (site_dir / catalog_rel).is_file():
        return None
    node_js = r"""
const fs = require('fs'), path = require('path'), vm = require('vm'), zlib = require('zlib');
const dir = process.argv[1];
const catalogRel = process.argv[2];
const ctx = { window: {} };
vm.createContext(ctx);
if (fs.readFileSync(path.join(dir, 'index.html'), 'utf8').includes('catalog-loader.js')) {
  const b = fs.readFileSync(path.join(dir, catalogRel));
  const decoded = b[0]===31 && b[1]===139 ? zlib.gunzipSync(b) : b;
  ctx.window.ARCHIVE_DATA = JSON.parse(decoded.toString('utf8'));
} else {
  vm.runInContext(fs.readFileSync(path.join(dir, 'data.js'), 'utf8'), ctx);
  for (let i = 1; i <= 20; i++) {
    const p = path.join(dir, `catalog-records-${i}.js`);
    if (fs.existsSync(p)) vm.runInContext(fs.readFileSync(p, 'utf8'), ctx);
  }
}
const records = (ctx.window.ARCHIVE_DATA && ctx.window.ARCHIVE_DATA.records) || [];
function displayTitleText(value){const opened={em:[],i:[],b:[],strong:[]};return String(value??'').replace(/<\/?(em|i|b|strong)(?=[\s>])[^>]*>/gi,(tag,name)=>{const key=name.toLowerCase(),closing=tag[1]==='/',plain=new RegExp('^<'+(closing?'/':'')+key+'\\s*>$','i').test(tag);if(!closing){opened[key].push(plain);return plain?'':tag}return plain&&opened[key].pop()===true?'':tag})}
const esc=(v,display=false)=>String(display===true?displayTitleText(v):(v??'')).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tangPhases=[['all','全唐'],['early','初唐'],['high','盛唐'],['middle','中唐'],['late','晚唐'],['broad','宽断代／跨期']];
const phaseLabel=p=>(tangPhases.find(x=>x[0]===p)?.[1]||'唐 · 宽断代／跨期');
function safeImg(r){
  let u=r.localImage||r.previewUrl||r.imageUrl||'';
  const orig=r.imageUrl||r.originalImageUrl||'';
  if(/^research-[A-Za-z0-9_-]+\//.test(u)&&orig)u=orig;
  if(/^https?:\/\/(?:[^/]+\.)?(?:clevelandart\.org|artic\.edu|si\.edu|wikimedia\.org|wikipedia\.org|metmuseum\.org)\//i.test(u)){
    return 'https://wsrv.nl/?url='+encodeURIComponent(u)+'&w=960&output=webp';
  }
  return u;
}
const cardsHtml = records.slice(0, 12).map((r, idx) => `<article class="card ${r.xiaScope?'xia-card ':''}${r.era==='西夏'?'xixia-card ':''}${r.evidence==='现存建筑'||r.evidence==='历史壁画'?'landscape':''}"><button class="card-picture" data-detail="${esc(r.id)}" aria-label="查看${esc(r.title,true)}的影像与出处">${r.displayMode==='source-only'?'<span class="image-fallback">原站查阅 · 点击查看出处</span>':`<img src="${esc(safeImg(r))}" alt="${esc(r.title,true)}" loading="${idx<4?'eager':'lazy'}" referrerpolicy="no-referrer">`}<span class="badge">${esc(r.metPeriodVersion==='met-period-v3'&&r.era==='跨期／待细分'?'分期待考':r.periodReview?.policyVersion==='mia-source-period-review-v1'&&r.periodReview.resolution!=='exact-source-label'?'制作年代／时期待考':r.crossesDeclaredPeriod?'宽断代 · 跨期':r.dateDisputed?'断代有争议':r.visualScope==='conditional'?'有条件参考':r.crosses1227?'宽断代 · 跨1227年':r.evidence)}</span>${r.imageCredit?'<span class="image-credit">'+esc(r.imageCredit)+'</span>':''}</button><button class="save " data-save="${esc(r.id)}" aria-label="加入参考集：${esc(r.title,true)}" aria-pressed="false">♡</button><div class="card-body"><div class="card-kicker"><span>${esc(r.era==='唐'?phaseLabel(r.tangPhase):r.era)}</span><span class="dot"></span><span>${esc(r.category)}</span></div><button class="card-title" data-detail="${esc(r.id)}">${esc(r.title,true)}</button><p class="card-date" title="${esc(r.date)}">${esc(r.date)}</p>${r.xiaScope?'<p class="xia-kicker">'+esc(r.xiaScope)+'</p>':''}${r.imageObjectDate?'<p class="tang-source-audit">载体：'+esc(r.imageObjectDate)+'</p>':''}${r.lifeFocus&&Array.isArray(r.lifeScenes)?'<p class="card-life-tags">'+esc(r.lifeScenes.slice(0,2).join(' · '))+'</p>':''}<div class="card-bottom"><span>${esc(r.institutionShort)}</span><b>${r.openLicense?'◈ 开放图像':'↗ 出处可查'}</b></div></div></article>`).join('');
process.stdout.write(JSON.stringify({
  total: records.length,
  eras: new Set(records.map(r => r.era)).size,
  cardsHtml
}));
"""
    r = subprocess.run(["node", "-e", node_js, str(site_dir), catalog_rel], capture_output=True, text=True, encoding="utf-8", timeout=45)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return json.loads(r.stdout)


def optimize_zhonghua_site(site_dir: Path) -> dict:
    import html as _html
    pruned_chunks = prune_retired_zhonghua_chunks(site_dir)
    js_hashes: dict[str, str] = {}
    js_modified = 0
    for jp in sorted(site_dir.glob("*.js")):
        raw = jp.read_bytes()
        opt = optimize_zhonghua_js_bytes(jp.name, raw)
        if opt != raw:
            jp.write_bytes(opt)
            js_modified += 1
        js_hashes[jp.name] = sha256_bytes(opt)[:12]

    fast_cat = build_zhonghua_fast_catalog(site_dir)
    ssg = _compute_zhonghua_ssg_payload(site_dir)
    gate_tag = make_gate_script("金泰 AI · 中华文明影像库")
    html_modified = 0

    for hp in sorted(site_dir.rglob("*.html")):
        if ".git" in hp.parts or hp == site_dir / "scripts" / "shang_all.template.html":
            continue
        orig = hp.read_text(encoding="utf-8", errors="ignore")
        txt = orig

        # 1. Refresh unified gate & ZH_SHIM
        txt = re.sub(r'<style>a\[href\*="signin-with-chatgpt"\][^<]*</style><script id="jintai-zhonghua-cdn-shim">.*?</script>', ZH_SHIM, txt, count=1, flags=re.S)
        txt = re.sub(r'<script id="jt-unified-gate">.*?</script>', gate_tag, txt, count=1, flags=re.S)

        # The exact full-catalog Shang route is handled before the gated index
        # starts its heavyweight loader. The destination carries the same gate.
        if hp == site_dir / "index.html" and (site_dir / "shang-all.html").is_file() and gate_tag in txt:
            route_tag = ('<script id="jt-shang-all-route">(function(){'
                         'var p=new URLSearchParams(location.hash.slice(1));'
                         'if(p.get("era")==="商"&&Array.from(p.keys()).length===1)'
                         'location.replace(new URL("shang-all.html",location.href).href)'
                         '})();</script>')
            txt = re.sub(r'<script id="jt-shang-all-route">.*?</script>', '', txt, count=1, flags=re.S)
            txt = txt.replace(gate_tag, route_tag + gate_tag, 1)
            if 'id="jt-shang-all-link"' not in txt:
                txt = re.sub(
                    r'(<div class="hero-actions">)(.*?)(</div>)',
                    lambda m_: (m_.group(1) + m_.group(2)
                                + '<a class="hero-index-link" id="jt-shang-all-link" href="./shang-all.html">商代全库快览 →</a>'
                                + m_.group(3)),
                    txt,
                    count=1,
                    flags=re.S,
                )

        # 1b. Inject t=0 streaming fast-catalog + HTTP/2 P1 prefetch on index.html
        txt = re.sub(r'<link id="jt-zh-fast-preload"[^>]*>', '', txt)
        txt = re.sub(r'<script id="jt-zh-fast-boot">.*?</script>', '', txt, flags=re.S)
        if hp == site_dir / "index.html" and fast_cat and ZH_SHIM in txt:
            f_url = f"./catalog-fast.json.gz?v={fast_cat['fast_hash']}"
            p1_json = json.dumps(fast_cat["p1_urls"], ensure_ascii=False, separators=(",", ":"))
            p2_json = json.dumps(fast_cat["p2_urls"], ensure_ascii=False, separators=(",", ":"))
            p2_names_json = json.dumps(sorted(ZH_DEFERRED_P2 | {"library-quality-ui.js"}), ensure_ascii=False, separators=(",", ":"))
            fast_tag = (
                f'<link id="jt-zh-fast-preload" rel="preload" href="{f_url}" as="fetch" crossorigin>'
                '<script id="jt-zh-fast-boot">(function(){'
                'if(window.__JT_LOCKED__||location.protocol==="file:")return;'
                f'var fastUrl={json.dumps(f_url)},p1Urls={p1_json},p2Urls={p2_json},p2Set=new Set({p2_names_json});'
                'if(location.hash==="#expansion")return;'
                'if(!location.hash)window.__JT_DEFER_CHRON__=true;'
                'window.__JT_SKIP_P2__=function(s){var fn=String(s).split("?")[0].split("/").pop();return p2Set.has(fn);};'
                'window.__JT_DEFERRED_P2_URLS__=p2Urls;'
                'function gunzipJson(u){return fetch(u).then(function(r){if(!r.ok)throw Error("HTTP "+r.status);'
                'if(r.body&&typeof DecompressionStream!=="undefined"){return new Response(r.body.pipeThrough(new DecompressionStream("gzip"))).json();}'
                'return r.arrayBuffer().then(function(ab){var b=new Uint8Array(ab);var s=new Blob([b]).stream();'
                'var d=(b[0]===31&&b[1]===139&&typeof DecompressionStream!=="undefined")?s.pipeThrough(new DecompressionStream("gzip")):s;'
                'return new Response(d).json();});});}'
                'window.__JT_FAST_ARCHIVE_PROMISE__=gunzipJson(fastUrl).then(function(pk){'
                'var cols=pk.cols,dict=pk.dict,rows=pk.rows,pins=pk.cmaPins||{},n=rows.length,cl=cols.length,recs=new Array(n);'
                'var iLoc=cols.indexOf("localImage"),iImg=cols.indexOf("imageUrl");'
                'function dv(x){return typeof x==="string"&&x.charCodeAt(0)===1?dict[parseInt(x.slice(1),16)]:x;}'
                'for(var i=0;i<n;i++){var rw=rows[i],rl=rw.length,o={};'
                'for(var j=0;j<rl;j++){var v=rw[j];if(v===null)continue;'
                'if(typeof v==="string"&&v.charCodeAt(0)===1)v=dict[parseInt(v.slice(1),16)];'
                'else if(v===-1)v=iLoc>=0&&iLoc<rl?dv(rw[iLoc]):undefined;'
                'else if(v===-2)v=iImg>=0&&iImg<rl?dv(rw[iImg]):undefined;'
                'o[cols[j]]=v;}'
                'if(o.localImage&&!o.imageUrl)o.imageUrl=o.localImage;'
                'if(pins[i])o.sourceRecordSha256=pins[i];'
                'recs[i]=o;}'
                'var ad=pk.meta||{};ad.records=recs;'
                'if(window.__jtSanitizePack)window.__jtSanitizePack(ad);'
                'return ad;});'
                'for(var k=0;k<p1Urls.length;k++)fetch(p1Urls[k]).catch(function(){});'
                'var fullProm=null;'
                'window.__jtEnsureFullCatalog=function(){'
                'if(window.__JT_FULL_MERGED__)return Promise.resolve(true);'
                'if(fullProm)return fullProm;'
                'var bu=window.__JT_BASE_CATALOG_URL__||"./catalog-base.json.gz";'
                'fullProm=gunzipJson(bu).then(function(full){'
                'var cur=(window.ARCHIVE_DATA&&window.ARCHIVE_DATA.records)||[],fr=(full&&full.records)||[];'
                'if(cur.length===fr.length){for(var i=0;i<fr.length;i++)Object.assign(cur[i],fr[i]);}'
                'if(window.__jtSanitizePack)window.__jtSanitizePack(window.ARCHIVE_DATA);'
                'window.__JT_FULL_MERGED__=true;return true;}).catch(function(){return false;});'
                'return fullProm;};'
                'window.__jtInstallDetailHydrator=function(){'
                '["detail","exportRecords","copyCitation"].forEach(function(fn){'
                'var orig=window[fn];if(typeof orig!=="function"||orig.__jtWrapped)return;'
                'var w=async function(){var a=arguments;if(!window.__JT_FULL_MERGED__)await window.__jtEnsureFullCatalog();return orig.apply(this,a);};'
                'w.__jtWrapped=true;window[fn]=w;});};'
                '})();</script>'
            )
            txt = txt.replace(ZH_SHIM, ZH_SHIM + fast_tag, 1)

        # 2. SSG pre-render first-screen KPIs & initial 12 cards on index.html
        if hp == site_dir / "index.html" and ssg and ssg.get("total"):
            total = int(ssg["total"])
            eras = int(ssg["eras"])
            cards_html = ssg["cardsHtml"]
            rem = max(0, total - 12)
            txt = re.sub(r'(<strong id="totalCount">)[^<]*(</strong>)', rf"\g<1>{total}\2", txt, count=1)
            txt = re.sub(r'(<strong id="eraCount">)[^<]*(</strong>)', rf"\g<1>{eras}\2", txt, count=1)
            txt = re.sub(r'(<span id="allCount">)[^<]*(</span>)', rf"\g<1>{total}\2", txt, count=1)
            txt = re.sub(
                r'(<span id="resultCount"[^>]*>)[^<]*(</span>)',
                rf"\g<1>共 {total} 条影像 · 点击查看出处\2",
                txt,
                count=1,
            )
            txt = re.sub(
                r'<div class="cards" id="cards">.*?</div>(?=<div class="empty" id="empty")',
                lambda _: f'<div class="cards" id="cards">{cards_html}</div>',
                txt,
                count=1,
                flags=re.S,
            )
            txt = re.sub(
                r'<button id="loadMore" class="load-more">.*?</button>',
                f'<button id="loadMore" class="load-more">继续浏览 <span>↓</span> <small>（还有 {rem} 条）</small></button>',
                txt,
                count=1,
                flags=re.S,
            )

        # 3. Convert trailing synchronous <script src="..."> tags before </body> into #jt-zh-async-loader
        is_shang_all = hp == site_dir / "shang-all.html"
        m_existing = None if is_shang_all else re.search(r'<script id="jt-zh-async-loader"[^>]*\bdata-all="([^"]+)"[^>]*>.*?</script>(?=\s*</body>)', txt, flags=re.S)
        m_raw = None if is_shang_all or m_existing else re.search(r'((?:<script\s+src="[^"]+"\s*></script>\s*)+)(?=</body>)', txt, flags=re.I)
        if m_existing or m_raw:
            if m_existing:
                raw_srcs = json.loads(_html.unescape(m_existing.group(1)))
                span_start, span_end = m_existing.span()
            else:
                raw_srcs = re.findall(r'<script\s+src="([^"]+)"\s*></script>', m_raw.group(1), flags=re.I)
                span_start, span_end = m_raw.span(1)
            updated_srcs = []
            for s_url in raw_srcs:
                base_u = s_url.split("?", 1)[0]
                clean_fn = base_u.lstrip("./")
                if "/" not in clean_fn and clean_fn in js_hashes and hp.parent == site_dir:
                    updated_srcs.append(f"{base_u}?v={js_hashes[clean_fn]}")
                else:
                    updated_srcs.append(s_url)
            is_index = (hp == site_dir / "index.html")
            p1, p2 = [], []
            for u in updated_srcs:
                fn = os.path.basename(u.split("?", 1)[0])
                if is_index and fn in ZH_DEFERRED_P2:
                    p2.append(u)
                else:
                    p1.append(u)
            loader_tag = _build_zh_async_loader_tag(updated_srcs, p1, p2)
            txt = txt[:span_start] + loader_tag + txt[span_end:]

        if txt != orig:
            hp.write_bytes(txt.encode("utf-8"))
            check_html_js_syntax(hp)
            html_modified += 1

    return {"js_modified": js_modified, "html_modified": html_modified, "ssg_records": ssg.get("total") if ssg else 0, "pruned_chunks": pruned_chunks, "fast_catalog_bytes": fast_cat["fast_bytes"] if fast_cat else 0}


def sync_zhonghua(site_dir: Path, auto_push: bool = True) -> dict:
    host = "zhonghua-civilization-atlas.fondcream1.chatgpt.site"
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://{host}/", headers={"User-Agent": UA}), timeout=15) as r_eff:
            eff_netloc = urllib.parse.urlparse(r_eff.geturl()).netloc
            if eff_netloc:
                host = eff_netloc
    except Exception:
        pass
    base = f"https://{host}/"

    # The catalog health probe below checks the new versioned gzip and scripts.
    probe_files = ["index.html", "site-version.json", "data.js", "daily-batch.js", "app.js", "song-data.js", "liao-data.js"]
    probe_parts = []
    index_bytes = b""
    for pf in probe_files:
        st_p, b_p = fetch_bytes(base + ("" if pf == "index.html" else pf))
        if pf == "index.html" and (st_p != 200 or not b_p):
            return {"site": "zhonghua", "status": "upstream_skipped", "http": st_p}
        if st_p == 200:
            if pf.endswith(".html"):
                b_p = strip_cf_challenge(b_p.decode("utf-8", "ignore")).encode("utf-8")
                index_bytes = b_p
            probe_parts.append(sha256_bytes(b_p))
    catalog_refs, verified_loader, catalog_fp = probe_zhonghua_catalog_upstream(base, index_bytes)
    new_catalog_declared = bool(verified_loader)
    catalog_base_rel = zh_catalog_loader_dependencies(verified_loader["catalog-loader.js"].decode("utf-8"))[0] if new_catalog_declared else None
    # Keep the local mirror current with cloud commits even when this upstream
    # snapshot is unchanged; a broken origin never reaches this Git operation.
    git_prepare_repo(site_dir, auto_push)
    quick_fp = "|".join(probe_parts + [catalog_fp, ZH_SHIM_REV, shang_all_input_fingerprint(site_dir) if new_catalog_declared else "legacy"])

    state_p = site_dir / ".sync_state.json"
    required_aux = (
        (site_dir / "site-version.json").is_file()
        and (site_dir / "publication-proofs" / "build-report.json").is_file()
    )
    if state_p.is_file() and required_aux:
        try:
            if json.loads(state_p.read_text(encoding="utf-8")).get("quick_fp") == quick_fp:
                if not new_catalog_declared:
                    return {"site": "zhonghua", "status": "up-to-date"}
                loader_bytes = verified_loader.get("catalog-loader.js")
                if loader_bytes:
                    base_rel, scripts = zh_catalog_loader_dependencies(loader_bytes.decode("utf-8"))
                    if (all((site_dir / rel).is_file() and (site_dir / rel).stat().st_size for rel in ["catalog-loader.js", base_rel, *scripts])
                            and shang_all_snapshot_ready(site_dir) and shang_all_index_ready(site_dir)):
                        return {"site": "zhonghua", "status": "up-to-date"}
        except Exception:
            pass

    # The quick pass reads only the small loader and response headers. Download
    # and hash large catalog chunks only when a new snapshot is actually needed.
    verified_catalog = verify_zhonghua_catalog_upstream(base, catalog_refs, verified_loader)

    text_exts = {".html", ".css", ".js", ".json", ".md", ".svg", ".txt"}
    asset_exts = {".webp", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".woff", ".woff2"}
    to_visit = {"index.html", "site-version.json", "publication-proofs/build-report.json", *verified_catalog}
    visited = set()
    fetched = set()
    catalog_loader_source = None
    discovered_media = set()
    gate_tag = make_gate_script("金泰 AI · 中华文明影像库")

    while to_visit:
        batch = sorted(to_visit - visited)
        if not batch:
            break
        def dl_doc(rel):
            if rel == "index.html":
                return rel, 200, index_bytes
            if rel in verified_catalog:
                return rel, 200, verified_catalog[rel]
            u = base + ("" if rel == "index.html" else urllib.parse.quote(rel, safe="/"))
            s, b = fetch_bytes(u, retries=3, timeout=30)
            return rel, s, b
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
            res = list(ex.map(dl_doc, batch))
        for rel, s, b in res:
            visited.add(rel)
            if s != 200 or not b:
                continue
            fetched.add(rel)
            ext = os.path.splitext(rel)[1].lower()
            txt = "" if ext == ".gz" else b.decode("utf-8", errors="ignore")
            if ext == ".html":
                clean_h = strip_cf_challenge(txt)
                clean_h = re.sub(r'<style>a\[href\*="signin-with-chatgpt"\][^<]*</style>', '', clean_h, flags=re.S)
                clean_h = re.sub(r'<script id="jt-unified-gate">.*?</script>', '', clean_h, flags=re.S)
                clean_h = re.sub(r'<script id="jintai-zhonghua-cdn-shim">.*?</script>', '', clean_h, flags=re.S)
                for ref in re.findall(r'(?:src|href)=["\']([^"\']+)["\']', clean_h, flags=re.I):
                    nr = norm_zh_rel(rel, ref)
                    if nr and not nr.startswith("signin-with-chatgpt"):
                        rext = os.path.splitext(nr)[1].lower()
                        if rext in text_exts:
                            to_visit.add(nr)
                        elif rext in asset_exts:
                            discovered_media.add(nr)
                # Rewrite root-relative src="/..." and href="/..." (including bare href="/") to "./..." for GitHub Pages subpath hosting
                rel_prefix = "./" if "/" not in rel else ("../" * rel.count("/"))
                clean_h = re.sub(
                    r'\bhref=(["\'])/\1',
                    lambda m_: f'href={m_.group(1)}{rel_prefix}{m_.group(1)}',
                    clean_h,
                    flags=re.I,
                )
                clean_h = re.sub(
                    r'\b(src|href)=(["\'])/(?!/|signin-with-chatgpt)([^"\']+)\2',
                    lambda m_: f'{m_.group(1)}={m_.group(2)}{rel_prefix}{m_.group(3)}{m_.group(2)}',
                    clean_h,
                    flags=re.I,
                )
                patched_h, n = re.subn(r"(<head\b[^>]*>)", r"\1" + gate_tag + ZH_SHIM, clean_h, count=1, flags=re.I)
                if n == 1:
                    lp = site_dir / rel
                    lp.parent.mkdir(parents=True, exist_ok=True)
                    lp.write_bytes(patched_h.encode("utf-8"))
                    check_html_js_syntax(lp)
            else:
                # Never overwrite gigantic >90MB files (GitHub limit)
                if len(b) < 90 * 1024 * 1024:
                    b_opt = optimize_zhonghua_js_bytes(rel, b) if ext == ".js" else b
                    lp = site_dir / rel
                    lp.parent.mkdir(parents=True, exist_ok=True)
                    if not lp.is_file() or lp.read_bytes() != b_opt:
                        lp.write_bytes(b_opt)
                if rel == catalog_base_rel:
                    discovered_media.update(discover_zh_catalog_media(b))
                if ext == ".css":
                    for ref in re.findall(r'url\(["\']?([^"\')]+)["\']?\)', txt, flags=re.I):
                        nr = norm_zh_rel(rel, ref)
                        if nr:
                            discovered_media.add(nr)
                elif ext in (".js", ".json"):
                    if rel == "catalog-loader.js":
                        catalog_loader_source = txt
                        catalog_base, catalog_scripts = zh_catalog_loader_dependencies(txt)
                        to_visit.add(catalog_base)
                        to_visit.update(catalog_scripts)
                    for m in re.finditer(r'["\'`]((?:\./)?(?:assets|(?:[A-Za-z0-9_-]+-)?images|research-[A-Za-z0-9_-]+)/[^"\'`\s?#]+|(?:[A-Za-z0-9_-]+\.html))(?:\?[^"\'`\s#]*)?["\'`]', txt):
                        nr = norm_zh_rel(rel, m.group(1))
                        if nr:
                            rext = os.path.splitext(nr)[1].lower()
                            if rext == ".html":
                                to_visit.add(nr)
                            elif rext in asset_exts:
                                discovered_media.add(nr)

    if new_catalog_declared:
        if catalog_loader_source is None:
            raise RuntimeError("upstream declares catalog-loader.js, but it was not fetched")
        validate_zh_catalog_downloads(site_dir, catalog_loader_source, fetched)

    prev_unhosted = set()
    if state_p.is_file():
        try:
            prev_unhosted = set(json.loads(state_p.read_text(encoding="utf-8")).get("unhosted_media") or [])
        except Exception:
            pass
    missing_media = sorted(m for m in discovered_media if not (site_dir / m).is_file() and m not in prev_unhosted)
    newly_unhosted = set()
    if missing_media:
        tls_local = threading.local()
        ctx = ssl.create_default_context()
        unhosted_lock = threading.Lock()
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
                    if resp.status in (301, 302, 307, 308):
                        loc = resp.getheader("Location") or ""
                        if loc.startswith("http"):
                            st_r, data_r = fetch_bytes(loc, retries=2, timeout=15)
                            if st_r == 200 and data_r and len(data_r) < 25 * 1024 * 1024:
                                lp = site_dir / rel
                                lp.parent.mkdir(parents=True, exist_ok=True)
                                lp.write_bytes(data_r)
                            elif st_r in (404, 410):
                                with unhosted_lock:
                                    newly_unhosted.add(rel)
                        return
                    if resp.status == 200 and data and len(data) < 25 * 1024 * 1024:
                        lp = site_dir / rel
                        lp.parent.mkdir(parents=True, exist_ok=True)
                        lp.write_bytes(data)
                    elif resp.status in (404, 410):
                        with unhosted_lock:
                            newly_unhosted.add(rel)
                    return
                except Exception:
                    tls_local.conn = None
                    conn = None

        with concurrent.futures.ThreadPoolExecutor(max_workers=24) as ex:
            list(ex.map(dl_media, missing_media))

    if new_catalog_declared:
        build_shang_all_snapshot(site_dir, site_dir / catalog_base_rel)

    # Align <meta name="atlas-snapshot-revision"> in all synced HTML pages with site-version.json so freshly opened tabs never enter a false update-banner loop
    sv_path = site_dir / "site-version.json"
    if sv_path.is_file():
        try:
            sv_rev = json.loads(sv_path.read_text(encoding="utf-8")).get("revision", "")
            if re.fullmatch(r"[0-9a-f]{64}", sv_rev):
                for hp in site_dir.rglob("*.html"):
                    if ".git" in hp.parts or hp == site_dir / "scripts" / "shang_all.template.html":
                        continue
                    htxt = hp.read_text(encoding="utf-8", errors="ignore")
                    hnew = re.sub(
                        r'(<meta\b[^>]*\bname=["\']atlas-snapshot-revision["\'][^>]*\bcontent=["\'])[0-9a-f]{64}(["\'])',
                        rf"\g<1>{sv_rev}\2",
                        htxt,
                    )
                    if hnew != htxt:
                        hp.write_bytes(hnew.encode("utf-8"))
        except Exception:
            pass

    optimized = optimize_zhonghua_site(site_dir)
    if new_catalog_declared and not optimized["ssg_records"]:
        raise RuntimeError("new zhonghua catalog could not be parsed for first-screen rendering")
    all_unhosted = sorted((prev_unhosted | newly_unhosted) - {m for m in discovered_media if (site_dir / m).is_file()})
    state_p.write_text(json.dumps({"quick_fp": quick_fp, "docs": len(visited), "new_media": len(missing_media) - len(newly_unhosted), "unhosted_media": all_unhosted}, indent=2), encoding="utf-8")
    changed = git_push_if_changed(site_dir, "zhonghua-civilization-atlas", f"sync(auto): upstream zhonghua atlas ({len(visited)} docs)", auto_push)
    return {"site": "zhonghua", "status": "updated" if changed else "up-to-date", "changed_files": len(changed), "new_media": len(missing_media)}


def sync_history_site1(auto_push: bool = True) -> dict:
    hist_mgr = Path(r"C:\Users\KingT\jintai-internal\中国历史文化图库\每日更新\管理\ensure_domestic_compact_index.py")
    cat_sync = Path(r"C:\Users\KingT\jintai-internal\中国历史文化图库\每日更新\管理\sync_all_category_pages.py")
    pub = Path(r"C:\Users\KingT\jintai-internal\中国历史文化图库\每日更新\publish_checkout_20261012")
    if not hist_mgr.is_file() or not pub.is_dir():
        return {"site": "history", "status": "skipped_not_local"}

    # The remote branch can advance while this partial clone's local HEAD stays
    # behind. Check before generating pages or staging objects; the publisher
    # cannot safely push across that divergence. Keep the other sites running.
    probe_env = os.environ.copy()
    probe_env["GIT_NO_LAZY_FETCH"] = "1"

    def probe_git(*args: str) -> str:
        command = ["git", "--no-lazy-fetch", "-C", str(pub), *args]
        proc = subprocess.Popen(
            command, env=probe_env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        try:
            stdout, stderr = proc.communicate(timeout=25)
        except subprocess.TimeoutExpired:
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    capture_output=True, timeout=10, check=False,
                )
            except subprocess.TimeoutExpired:
                pass
            if proc.poll() is None:
                proc.kill()
            proc.communicate()
            raise RuntimeError("history remote-head probe timed out")
        if proc.returncode:
            raise subprocess.CalledProcessError(
                proc.returncode, command, output=stdout, stderr=stderr,
            )
        return stdout.decode("utf-8", errors="replace").strip()

    try:
        local_head = probe_git("rev-parse", "HEAD")
        remote_line = probe_git("ls-remote", "--heads", "origin", "main")
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        return {"site": "history", "status": "blocked_remote_check", "reason": type(exc).__name__}
    remote_head = remote_line.split("\t", 1)[0] if remote_line else ""
    if remote_head != local_head:
        return {"site": "history", "status": "blocked_remote_diverged", "local_head": local_head, "remote_head": remote_head}

    sync_ext = hist_mgr.parent / "sync_external_and_verify.py"
    subprocess.run([sys.executable, str(sync_ext)], check=True)
    tracked_targets = [
        "index.html", "browser.html", "d1_idx", "d2_idx",
        "portal.html", "图库总入口.html", "arch5680.html", "arch_data", "myth5000.html", "myth_data",
        "epics.html", "epics_data", "zhiguai31.html", "zhiguai_data", "zhiguai57.html", "hongloumeng.html", "hongloumeng_data",
        "liaozhai.html", "聊斋志异角色与全场景专集.html", "聊斋志异角色场景法器全谱专集.html", "liaozhai_data",
        "dynasty2000.html", "dynasty_data", "websearch5000.html", "websearch_data",
        "figures.html", "figures_data", "sources.html", "影视来源目录.html",
        "更新记录.html", "changelog.html", "00_每日更新总目录.html", "每日更新/00_每日更新总目录.html",
    ]
    existing_targets = [t for t in tracked_targets if (pub / t).exists()]
    result = _history_publish_selected(pub, existing_targets, auto_push=auto_push)
    return {"site": "history", **result}


def collect_live_4sites_metrics(root: Path) -> dict:
    pub = Path(r"C:\Users\KingT\jintai-internal\中国历史文化图库\每日更新\publish_checkout_20261012")
    m: dict = {
        "d1_shards": 736, "d1_entries": 77379, "d1_prompts": 370412,
        "d2_shards": 793, "d2_entries": 76386, "d2_prompts": 364996,
        "film_works": 53000, "film_shots": 2779879, "film_styles": 250,
        "ws_groups": 13500, "ws_prompts": 135000,
        "dyn_groups": 7800, "dyn_prompts": 78000, "dyn_wtag": "W6200",
        "arch_sites": 9507, "arch_prompts": 45582,
        "myth_groups": 7884, "myth_prompts": 45666,
        "epics_groups": 2600, "epics_prompts": 25760, "full_lit_groups": 3000,
        "hlm_groups": 268, "hlm_prompts": 2423,
        "lz_groups": 376, "lz_prompts": 3094,
        "zg_rel": 3072, "figures_total": 26000,
        "zh_records": 26847, "zh_hosted_imgs": 18427,
        "doc_published": 4229, "doc_total": 30469, "doc_regions": 137, "doc_topics": 1176,
        "sc_total": 72298, "sc_cats": 12,
    }
    if pub.is_dir():
        for html_fn, pfx, idx_sub in (("index.html", "d1", "d1_idx"), ("browser.html", "d2", "d2_idx")):
            hp = pub / html_fn
            if hp.is_file():
                ht = hp.read_text(encoding="utf-8", errors="ignore")
                ms = re.search(r"const SHARDS=(\[[^\n;]+\]);", ht)
                if ms:
                    m[f"{pfx}_shards"] = len(json.loads(ms.group(1)))
                mc = re.search(r"const IDX_CHUNKS=(\[[^\n;]+\]);", ht)
                if mc and (pub / idx_sub).is_dir():
                    ec, pc = 0, 0
                    for cfn in json.loads(mc.group(1)):
                        cp = pub / idx_sub / cfn
                        if cp.is_file():
                            ct = cp.read_text(encoding="utf-8")
                            ib, ie = ct.find("["), ct.rfind("]")
                            if ib >= 0 and ie > ib:
                                for grp in json.loads(ct[ib:ie + 1]):
                                    ec += len(grp[2])
                                    pc += sum(int(r[-1]) for r in grp[2])
                    if ec > 0:
                        m[f"{pfx}_entries"], m[f"{pfx}_prompts"] = ec, pc
        if (pub / "sources.html").is_file():
            stxt = (pub / "sources.html").read_text(encoding="utf-8", errors="ignore")
            mk = re.search(r'id="topKpi"[^>]*><b>([\d,]+)</b>\s*部\s*·\s*<b>([\d,]+)</b>\s*镜', stxt)
            if mk:
                m["film_works"] = int(mk.group(1).replace(",", ""))
                m["film_shots"] = int(mk.group(2).replace(",", ""))
            msl = re.search(r"(\d+)大风格派", stxt)
            if msl:
                m["film_styles"] = int(msl.group(1))
        if (pub / "websearch5000.html").is_file():
            wtxt = (pub / "websearch5000.html").read_text(encoding="utf-8", errors="ignore")
            mw = re.search(r"全网考证总馆藏\s*·\s*([\d,]+)\s*条", wtxt)
            if mw:
                m["ws_prompts"] = int(mw.group(1).replace(",", ""))
                m["ws_groups"] = m["ws_prompts"] // 10
        if (pub / "dynasty2000.html").is_file():
            dtxt = (pub / "dynasty2000.html").read_text(encoding="utf-8", errors="ignore")
            md = re.search(r"专集\s*·\s*([\d,]+)\s*条", dtxt)
            if md:
                m["dyn_prompts"] = int(md.group(1).replace(",", ""))
                m["dyn_groups"] = m["dyn_prompts"] // 10
            mwtag = re.search(r"\b(W\d{4,5})\b", dtxt)
            if mwtag:
                m["dyn_wtag"] = mwtag.group(1)
        if (pub / "arch5680.html").is_file():
            atxt = (pub / "arch5680.html").read_text(encoding="utf-8", errors="ignore")
            ma = re.search(r"全库\s*([\d,]+)\s*座\s*·\s*([\d,]+)\s*条", atxt)
            if ma:
                m["arch_sites"] = int(ma.group(1).replace(",", ""))
                m["arch_prompts"] = int(ma.group(2).replace(",", ""))
        if (pub / "myth5000.html").is_file():
            mtxt = (pub / "myth5000.html").read_text(encoding="utf-8", errors="ignore")
            mm = re.search(r"([\d,]+)\s*组\s*·\s*([\d,]+)\s*条", mtxt)
            if mm:
                m["myth_groups"] = int(mm.group(1).replace(",", ""))
                m["myth_prompts"] = int(mm.group(2).replace(",", ""))
        if (pub / "epics.html").is_file():
            etxt = (pub / "epics.html").read_text(encoding="utf-8", errors="ignore")
            me = re.search(r"本集\s*([\d,]+)\s*组\s*/\s*([\d,]+)\s*条[^）]*满\s*([\d,]+)\s*组", etxt)
            if me:
                m["epics_groups"] = int(me.group(1).replace(",", ""))
                m["epics_prompts"] = int(me.group(2).replace(",", ""))
                m["full_lit_groups"] = int(me.group(3).replace(",", ""))
        if (pub / "hongloumeng.html").is_file():
            htxt = (pub / "hongloumeng.html").read_text(encoding="utf-8", errors="ignore")
            mh = re.search(r"(\d+)\s*组\s*[·（(]\s*([\d,]+)\s*条", htxt)
            if mh:
                m["hlm_groups"], m["hlm_prompts"] = int(mh.group(1)), int(mh.group(2).replace(",", ""))
        if (pub / "liaozhai.html").is_file():
            ltxt = (pub / "liaozhai.html").read_text(encoding="utf-8", errors="ignore")
            ml = re.search(r"(\d+)\s*组\s*[·（(]\s*([\d,]+)\s*条", ltxt)
            if ml:
                m["lz_groups"], m["lz_prompts"] = int(ml.group(1)), int(ml.group(2).replace(",", ""))
        if (pub / "zhiguai31.html").is_file():
            ztxt = (pub / "zhiguai31.html").read_text(encoding="utf-8", errors="ignore")
            mz = re.search(r"关联\s*([\d,]+)\s*组", ztxt)
            if mz:
                m["zg_rel"] = int(mz.group(1).replace(",", ""))
        fmf = pub / "figures_data" / "manifest.js"
        if fmf.is_file():
            mfm = re.search(r'"total_figures"\s*:\s*(\d+)', fmf.read_text(encoding="utf-8", errors="ignore"))
            if mfm:
                m["figures_total"] = int(mfm.group(1))

    zh_dir = root / "03_zhonghua-civilization-atlas"
    if (zh_dir / "index.html").is_file():
        zht = (zh_dir / "index.html").read_text(encoding="utf-8", errors="ignore")
        mzt = re.search(r'id="totalCount">(\d+)<', zht)
        if mzt:
            m["zh_records"] = int(mzt.group(1))
        m["zh_hosted_imgs"] = sum(
            1 for p in zh_dir.rglob("*")
            if p.suffix.lower() in {".webp", ".jpg", ".jpeg", ".png"} and ".git" not in p.parts
        )

    doc_lib = root / "02_documentary-classroom-library" / "data" / "library_full.json"
    if doc_lib.is_file():
        dobj = json.loads(doc_lib.read_text(encoding="utf-8"))
        st = dobj.get("stats") or {}
        fc = dobj.get("facets") or {}
        if st.get("published"):
            m["doc_published"] = int(st["published"])
        if st.get("total"):
            m["doc_total"] = int(st["total"])
        if fc.get("region"):
            m["doc_regions"] = len(fc["region"])
        if fc.get("topic"):
            m["doc_topics"] = len(fc["topic"])

    sc_dir = root / "01_shengcang-sound-library"
    if sc_dir.is_dir():
        cats = set()
        sc_rows = 0
        sc_mf_total = 0
        for cp in sorted(sc_dir.glob("catalogue-*.json")):
            cobj = json.loads(cp.read_text(encoding="utf-8"))
            if isinstance(cobj, dict):
                if "total" in cobj and "parts" in cobj:
                    sc_mf_total = int(cobj["total"])
                elif "rows" in cobj and "columns" in cobj:
                    sc_rows += len(cobj["rows"])
                    cols = cobj["columns"]
                    dct = cobj.get("dictionary") or []
                    if "category" in cols:
                        ci = cols.index("category")
                        for r in cobj["rows"]:
                            v = r[ci]
                            cats.add(dct[v] if isinstance(v, int) and 0 <= v < len(dct) else str(v))
        if sc_mf_total or sc_rows:
            m["sc_total"] = sc_mf_total or sc_rows
        if cats:
            m["sc_cats"] = len(cats)
    return m


def _patch_hbcm_html_metrics(txt: str, m: dict) -> str:
    combined_wan = f"{(m['d1_prompts'] + m['film_shots']) / 10000:.1f}"
    d1_wan = f"{m['d1_prompts'] / 10000:.1f}"
    film_wan = f"{m['film_shots'] / 10000:.1f}"
    works_wan = f"{m['film_works'] / 10000:g}"
    out = txt
    out = re.sub(r"\d+(?:\.\d+)?\s*万\+(?=\s*(?:考证与镜头|历史考证词|双图库|</div>))", f"{combined_wan} 万+", out)
    out = re.sub(r"总提示词与镜头描述资源已突破\s*[\d.]+\s*万条", f"总提示词与镜头描述资源已突破 {combined_wan} 万条", out)
    out = re.sub(r"超越 ShotDeck 的\s*[\d.]+\s*万镜引擎", f"超越 ShotDeck 的 {film_wan} 万镜引擎", out)
    out = re.sub(r'count:\s*"[\d,]+\s*条镜头词"', f'count: "{m["film_shots"]:,} 条镜头词"', out)
    out = re.sub(
        r'subCount:\s*"[\d,]+\s*部世界影史名作\s*·\s*全球百四十大摄影体系\s*\+\s*\d+大视觉流派"',
        f'subCount: "{m["film_works"]:,} 部世界影史名作 · 全球百四十大摄影体系 + {m["film_styles"]}大视觉流派"',
        out,
    )
    out = re.sub(
        r"直达《影视参考图集》\([^)]*镜\)",
        f"直达《影视参考图集》({works_wan}万部·{film_wan}万镜)",
        out,
    )
    out = re.sub(
        r"《影视参考图集》\s*\([\d.]+万镜\)",
        f"《影视参考图集》({film_wan}万镜)",
        out,
    )
    out = re.sub(
        r"影视参考图集\s*\([\d.]+万镜\)",
        f"影视参考图集 ({film_wan}万镜)",
        out,
    )
    out = re.sub(
        r"《影视参考图集》[\d.]+\s*万镜大师电影分镜检索引擎",
        f"《影视参考图集》{film_wan} 万镜大师电影分镜检索引擎",
        out,
    )
    out = re.sub(r'count:\s*"[\d,]+\s*条考证词"', f'count: "{m["d1_prompts"]:,} 条考证词"', out)
    out = re.sub(
        r'subCount:\s*"[\d,]+\s*个历史条目\s*·\s*[\d,]+\s*位历史名人\s*·\s*全网考证\s*[\d,]+\s*条"',
        f'subCount: "{m["d1_entries"]:,} 个历史条目 · {m["figures_total"]:,} 位历史名人 · 全网考证 {m["ws_prompts"]:,} 条"',
        out,
    )
    out = re.sub(
        r"《中国历史文化图库》[\d,]+\s*条中文十二段",
        f"《中国历史文化图库》{m['d1_prompts']:,} 条中文十二段",
        out,
    )
    out = re.sub(
        r"联通《中国历史文化图库》[\d.]+\s*万条考证词",
        f"联通《中国历史文化图库》{d1_wan} 万条考证词",
        out,
    )
    out = re.sub(
        r"(《中国历史文化图库》|历史文化图库)\s*\([\d.]+万[词条]?\)",
        rf"\1({d1_wan}万词)",
        out,
    )
    out = re.sub(
        r"《声仓(?:\s*Shengcang)?》\s*[\d,]+\s*条",
        f"《声仓》{m['sc_total']:,} 条",
        out,
    )
    out = re.sub(r"\((?:200|203|[\d,]+)条真品\)", f"({m['sc_total']:,}条真品)", out)
    out = re.sub(r"直跳《声仓》(?:200|203|[\d,]+)条真品", f"直跳《声仓》{m['sc_total']:,}条真品", out)
    out = re.sub(
        r'count:\s*"[\d,]+\s*部纪录片\s*\+\s*[\d,]+\s*(?:图|条考证)"',
        f'count: "{m["doc_published"]:,} 部纪录片 + {m["zh_records"]:,} 条考证"',
        out,
    )
    out = re.sub(
        r"《纪录片教学资源库》（[\d,]+\s*部课程档案）",
        f"《纪录片教学资源库》（{m['doc_published']:,} 部已发布课程档案 / {m['doc_total']:,} 总目）",
        out,
    )
    out = re.sub(
        r"《纪录片教学资源库》[\d,]+\s*部(?:已发布)?课程档案",
        f"《纪录片教学资源库》{m['doc_published']:,} 部课程档案",
        out,
    )
    out = re.sub(
        r"《纪录片教学资源库》\([\d,]+部\)",
        f"《纪录片教学资源库》({m['doc_published']:,}部)",
        out,
    )
    out = re.sub(
        r"([\d,]+)\s*部经典纪录片教学切入点",
        f"{m['doc_published']:,} 部经典纪录片教学切入点",
        out,
    )
    out = re.sub(
        r"([\d,]+)\s*部纪录片教学库",
        f"{m['doc_published']:,} 部纪录片教学库",
        out,
    )
    out = re.sub(r'metric:\s*"[\d,]+纪录片\s*\+\s*真人1:1"', f'metric: "{m["doc_published"]:,}纪录片 + 真人1:1"', out)
    out = re.sub(r'"[\d,]+部纪录片教学库"', f'"{m["doc_published"]:,}部纪录片教学库"', out)
    out = re.sub(
        r"《中华文明影像库》（[\d,]+\s*(?:张高清馆藏图|条文物考证[^）]*)）",
        f"《中华文明影像库》（{m['zh_records']:,} 条文物考证 · {m['zh_hosted_imgs']:,} 张自托管高清馆藏图）",
        out,
    )
    out = re.sub(
        r"《中华文明影像库》[\d,]+\s*(?:张|件)(?:博物馆)?(?:高清)?文物真迹",
        f"《中华文明影像库》{m['zh_records']:,} 件博物馆高清文物真迹",
        out,
    )
    out = re.sub(
        r"《中华文明影像库》[\d,]+\s*张文物真迹",
        f"《中华文明影像库》{m['zh_records']:,} 条文物真迹",
        out,
    )
    out = re.sub(
        r"《中华文明影像库》\([\d,]+件真迹\)",
        f"《中华文明影像库》({m['zh_records']:,}件真迹)",
        out,
    )
    return out


def sync_portal_and_hbcm_metrics(root: Path, auto_push: bool = True) -> dict:
    portal_dir = root / "00_portal"
    if not (portal_dir / "index.html").is_file():
        return {"site": "portal", "status": "skipped_not_local"}

    git_prepare_repo(portal_dir, auto_push)
    m = collect_live_4sites_metrics(root)
    d1_wan2 = f"{m['d1_prompts'] / 10000:.2f}"
    d1_wan1 = f"{m['d1_prompts'] / 10000:.1f}"
    d2_wan1 = f"{m['d2_prompts'] / 10000:.1f}"
    film_wan1 = f"{m['film_shots'] / 10000:.1f}"

    sites_data = [
        {
            "key": "history",
            "fullWidth": True,
            "title": "1. 中国历史文化图库与影视参考库（14 大分类专集全量同步）",
            "tags": [
                [f"{m['d1_entries']:,} 条目 / {m['d1_prompts']:,} 提示词（{d1_wan2}万词）· 全网考证 {m['ws_prompts']:,} 条", ""],
                [f"建筑 {m['arch_sites']:,} 座（{m['arch_prompts']:,} 条）· 名人 {m['figures_total']:,} 人 · 文学传奇满 {m['epics_groups']:,}/{m['full_lit_groups']:,} 组", ""],
                [f"影视参考 {m['film_works']:,} 部 · {m['film_shots']:,} 镜 · {m['film_styles']} 大流派", "red"],
            ],
            "desc": (
                f"覆盖中国全历史纪年 66 格矩阵（全库达 {m['d1_prompts']:,} 条提示词 / {m['d1_entries']:,} 条目 · {m['d1_shards']} 分片）："
                f"历代历史名人 {m['figures_total']:,} 人、全网考证 {m['ws_prompts']:,} 条、薄弱专集 {m['dyn_prompts']:,} 条（{m['dyn_wtag']}）、"
                f"历代建筑考证 {m['arch_sites']:,} 座（{m['arch_prompts']:,} 条）、神话与传说 {m['myth_groups']:,} 组（{m['myth_prompts']:,} 条）、"
                f"文学名著·民国小说与民间传奇（{m['epics_groups']:,} 组 / {m['epics_prompts']:,} 条，合璧红楼聊斋全库满 {m['full_lit_groups']:,} 组）。"
            ),
            "cloudUrl": "https://aikingtai-ctrl.github.io/jintai-history-image-library/portal.html",
            "localPath": "/jintai-history-image-library/portal.html",
            "catTitle": f"直达分类专集网页（14 个专集已与 {m['d1_shards']} 分片全量对齐）：",
            "categories": [
                {"name": "📋 全站更新记录中心", "meta": "每日批次台账", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/更新记录.html", "local": "/jintai-history-image-library/更新记录.html"},
                {"name": "🔍 全库总检索", "meta": f"{m['d1_entries']:,} 条目 / {d1_wan1}万词", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/index.html", "local": "/jintai-history-image-library/index.html"},
                {"name": "📚 18 分卷提示词浏览", "meta": f"{m['d2_entries']:,} 组 / {d2_wan1}万词", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/browser.html", "local": "/jintai-history-image-library/browser.html"},
                {"name": "🎬 影视参考图集", "meta": f"{m['film_works']:,} 部 / {film_wan1}万镜", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/film.html", "local": "/jintai-history-image-library/film.html"},
                {"name": "🏆 全球获奖影片目录", "meta": f"140 大奖项 · {m['film_styles']} 流派", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/sources.html", "local": "/jintai-history-image-library/sources.html"},
                {"name": "🌐 全网考证总馆藏", "meta": f"{m['ws_groups']:,} 组 / {m['ws_prompts']:,} 条", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/websearch5000.html", "local": "/jintai-history-image-library/websearch5000.html"},
                {"name": "🛠️ 薄弱与工程配套专集", "meta": f"{m['dyn_groups']:,} 组 / {m['dyn_prompts']:,} 条", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/dynasty2000.html", "local": "/jintai-history-image-library/dynasty2000.html"},
                {"name": "🏯 历代建筑考证总集", "meta": f"{m['arch_sites']:,} 座 / {m['arch_prompts']:,} 条", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/arch5680.html", "local": "/jintai-history-image-library/arch5680.html"},
                {"name": "🐉 神话与传说总专集", "meta": f"{m['myth_groups']:,} 组 / {m['myth_prompts']:,} 条", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/myth5000.html", "local": "/jintai-history-image-library/myth5000.html"},
                {"name": "📜 文学·民国小说·民间传奇", "meta": f"{m['epics_groups']:,} 组 / {m['epics_prompts']:,} 条（全库满{m['full_lit_groups']:,}组）", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/epics.html", "local": "/jintai-history-image-library/epics.html"},
                {"name": "🏮 《红楼梦》角色与大观园", "meta": f"{m['hlm_groups']} 组 / {m['hlm_prompts']:,} 条", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/hongloumeng.html", "local": "/jintai-history-image-library/hongloumeng.html"},
                {"name": "🦊 《聊斋志异》全谱专集", "meta": f"{m['lz_groups']} 组 / {m['lz_prompts']:,} 条", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/liaozhai.html", "local": "/jintai-history-image-library/liaozhai.html"},
                {"name": "📖 57 部志怪佛道传奇", "meta": f"800 组 + {m['zg_rel']:,} 关联", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/zhiguai31.html", "local": "/jintai-history-image-library/zhiguai31.html"},
                {"name": "👤 历代历史名人专集", "meta": f"{m['figures_total']:,} 人", "cloud": "https://aikingtai-ctrl.github.io/jintai-history-image-library/figures.html", "local": "/jintai-history-image-library/figures.html"},
            ],
        },
        {
            "key": "zhonghua",
            "fullWidth": True,
            "title": "2. 中华文明影像库 · 视觉美术参考（全朝代总览 + 12 断代考证专卷）",
            "tags": [
                [f"12 断代考证专卷 · {m['zh_records']:,} 条馆藏文物考证（{m['zh_hosted_imgs']:,} 张高清图）", ""],
                ["统一密码保护 · 微信一次通用", "red"],
            ],
            "desc": (
                f"汇集海内外博物馆开放馆藏与考古出土图像实证（全库已达 {m['zh_records']:,} 条文物考证记录 · {m['zh_hosted_imgs']:,} 张自托管高清馆藏图），"
                "覆盖史前至明清全朝代器物、服饰、甲胄、车马与建筑考证，内置商、西周、春秋、战国、秦、西汉、东汉、魏晋南北朝、隋、宋、辽、金 12 部独立断代分类专卷。"
            ),
            "cloudUrl": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/",
            "localPath": "/zhonghua-civilization-atlas/",
            "catTitle": "直达断代分类网页（全朝代总览 + 12 断代专卷）：",
            "categories": [
                {"name": "🏛️ 全朝代影像总览首页", "meta": f"{m['zh_records']:,} 条馆藏实证", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/", "local": "/zhonghua-civilization-atlas/"},
                {"name": "🏺 商代专卷", "meta": "青铜礼器·殷墟甲骨", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/shang.html", "local": "/zhonghua-civilization-atlas/shang.html"},
                {"name": "🔔 西周专卷", "meta": "礼乐彝器·车马铭文", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/western-zhou.html", "local": "/zhonghua-civilization-atlas/western-zhou.html"},
                {"name": "⚔️ 春秋专卷", "meta": "列国青铜·礼崩乐坏", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/spring-autumn.html", "local": "/zhonghua-civilization-atlas/spring-autumn.html"},
                {"name": "🐉 战国专卷", "meta": "楚漆错金·七雄衣冠", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/warring-states.html", "local": "/zhonghua-civilization-atlas/warring-states.html"},
                {"name": "🛡️ 秦代专卷", "meta": "兵马俑阵·秦诏度量", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/qin.html", "local": "/zhonghua-civilization-atlas/qin.html"},
                {"name": "🐎 西汉专卷", "meta": "马王堆·汉阙丝路", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/western-han.html", "local": "/zhonghua-civilization-atlas/western-han.html"},
                {"name": "🧱 东汉专卷", "meta": "画像石砖·绿釉陶楼", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/eastern-han.html", "local": "/zhonghua-civilization-atlas/eastern-han.html"},
                {"name": "🪷 魏晋南北朝专卷", "meta": "石窟壁画·褒衣博带", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/weijin.html", "local": "/zhonghua-civilization-atlas/weijin.html"},
                {"name": "🌉 隋代专卷", "meta": "白瓷金银·大运河", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/sui.html", "local": "/zhonghua-civilization-atlas/sui.html"},
                {"name": "🎋 宋代专卷", "meta": "汝官哥钧·风俗书画", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/song.html", "local": "/zhonghua-civilization-atlas/song.html"},
                {"name": "🦅 辽代专卷", "meta": "契丹金面·辽塔壁画", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/liao.html", "local": "/zhonghua-civilization-atlas/liao.html"},
                {"name": "🦌 金代专卷", "meta": "女真春水秋山·磁州窑", "cloud": "https://aikingtai-ctrl.github.io/zhonghua-civilization-atlas/jin.html", "local": "/zhonghua-civilization-atlas/jin.html"},
            ],
        },
        {
            "key": "documentary",
            "title": "3. 纪录片教学资源库 · 以真实，启发课堂",
            "tags": [
                [f"{m['doc_published']:,} 部已发布课程档案 / {m['doc_total']:,} 总目", ""],
                [f"{m['doc_regions']} 国家地区 · {m['doc_topics']:,} 主题分类", "red"],
            ],
            "desc": (
                f"覆盖 1910–2020 年代全球与中国经典纪录片，已扩容同步至 {m['doc_published']:,} 部已发布课程档案"
                f"（登记总目 {m['doc_total']:,} 部 · {m['doc_regions']} 个国家地区 · {m['doc_topics']:,} 个主题分类），"
                "支持按学科、年代、国家与主题多维课堂检索。"
            ),
            "cloudUrl": "https://aikingtai-ctrl.github.io/documentary-classroom-library/",
            "localPath": "/documentary-classroom-library/",
            "catTitle": "功能与分类入口：",
            "categories": [
                {"name": f"🎞️ {m['doc_published']:,} 部课程档案检索", "meta": "按学科 / 年代 / 国家", "cloud": "https://aikingtai-ctrl.github.io/documentary-classroom-library/#library", "local": "/documentary-classroom-library/#library"},
                {"name": f"🗂️ {m['doc_total']:,} 部全球纪录片总目", "meta": f"{m['doc_topics']:,} 个主题分类", "cloud": "https://aikingtai-ctrl.github.io/documentary-classroom-library/", "local": "/documentary-classroom-library/"},
            ],
        },
        {
            "key": "shengcang",
            "title": "4. 声仓 · 找到画面之外的声音",
            "tags": [
                [f"{m['sc_total']:,} 条影视声音素材 · {m['sc_cats']} 大声效分类", ""],
                ["统一密码保护 · 微信一次通用", "red"],
            ],
            "desc": (
                f"全量归档 {m['sc_total']:,} 条影视级声音素材，涵盖环境氛围、物件拟音、人物拟音、交通机械、战斗破坏、科幻魔法、"
                f"动物生物、冲击强调、转场运动、情绪张力、界面提示、音乐 {m['sc_cats']} 大声效分类，支持国内直连试听、波形预览与原文件下载。"
            ),
            "cloudUrl": "https://aikingtai-ctrl.github.io/shengcang-sound-library/#sound-library",
            "localPath": "/shengcang-sound-library/#sound-library",
            "catTitle": "功能与分类入口：",
            "categories": [
                {"name": "🔊 在线声效分类检索与试听", "meta": f"{m['sc_cats']} 大类 · {m['sc_total']:,} 条", "cloud": "https://aikingtai-ctrl.github.io/shengcang-sound-library/#sound-library", "local": "/shengcang-sound-library/#sound-library"},
                {"name": "🎚️ 声仓首页与使用指南", "meta": "波形预览与下载", "cloud": "https://aikingtai-ctrl.github.io/shengcang-sound-library/", "local": "/shengcang-sound-library/"},
            ],
        },
        {
            "key": "story2board",
            "fullWidth": True,
            "title": "5. 金泰 Story2Board · AI 分镜副导演与影史分镜工作台（公开免密直达）",
            "tags": [
                [f"250 部影史名片蒸馏 · 58,610 精标母镜 · 关联 {m['film_works']:,} 部 / {m['film_shots']:,} 镜", ""],
                ["AI 副导演拆镜配镜 · 锁脸提示词包 · 20pt 大字场记单", ""],
                ["公开免密直达 · 离线+隧道实时双模", "red"],
            ],
            "desc": (
                f"内置双预设 8×H100 实渲电影分镜示例（《雨夜霓虹》《长安暮雪》），支持 250 部影史名片离线秒搜与隧道直连 58,610 条精标母镜"
                f"（关联《影视参考图集》{m['film_works']:,} 部 / {m['film_shots']:,} 镜）、输入故事自动拆镜提供 3 套影史大师机位方案与运镜动机、"
                "一键复制锁脸提示词包及 20pt 大字场记单打印直出。"
            ),
            "cloudUrl": "https://aikingtai-ctrl.github.io/jintai-story2board/",
            "localPath": "/jintai-story2board/",
            "catTitle": "工作台核心模式与直达入口：",
            "categories": [
                {"name": "🎥 AI 副导演工作台", "meta": "剧本拆镜 · 3 套大师机位", "cloud": "https://aikingtai-ctrl.github.io/jintai-story2board/", "local": "/jintai-story2board/"},
                {"name": "📚 影史分镜索引库", "meta": f"250 名片 · {film_wan1}万全库", "cloud": "https://aikingtai-ctrl.github.io/jintai-story2board/#index", "local": "/jintai-story2board/#index"},
            ],
        },
    ]

    p_idx = portal_dir / "index.html"
    orig_pt = p_idx.read_text(encoding="utf-8")
    new_lead = (
        f'<p class="lead">已全量同步四大资源库与全部分类专集网页：历史文化图库（{m["d1_entries"]:,} 条目 / {m["d1_prompts"]:,} 提示词 / 14 大分类专集）'
        f'· 影视参考库（{m["film_works"]:,} 部 / {m["film_shots"]:,} 镜 / {m["film_styles"]} 大流派）'
        f'· 声仓（{m["sc_total"]:,} 条声效 / {m["sc_cats"]} 大类）'
        f'· 纪录片教学库（{m["doc_published"]:,} 部已发布 / {m["doc_total"]:,} 总目）'
        f'· 中华文明影像库（12 断代专卷 / {m["zh_records"]:,} 条馆藏考证）'
        f'· Story2Board AI 分镜工作台（250 名片 / 58,610 精标母镜）。</p>'
    )
    sites_js = "  var SITES = " + json.dumps(sites_data, ensure_ascii=False, indent=4) + ";"
    pt = re.sub(r'<p class="lead">.*?</p>', new_lead, orig_pt, count=1, flags=re.S)
    pt = re.sub(r"  var SITES = \[.*?\n\s*\];", lambda _: sites_js, pt, count=1, flags=re.S)
    if pt != orig_pt:
        today_s = time.strftime("%Y-%m-%d")
        pt = re.sub(r"四站全分类网页实时同步（\d{4}-\d{2}-\d{2}）", f"四站全分类网页实时同步（{today_s}）", pt, count=1)
        p_idx.write_bytes(pt.encode("utf-8"))
        check_html_js_syntax(p_idx)

    # Also update hbcm*.html inside 00_portal and sync to standalone jintai-hbcm-ai-platform repo
    for hfn in ("hbcm.html", "hbcm-m.html", "hbcm-mobile.html", "hbcm-platform.html"):
        hp = portal_dir / hfn
        if hp.is_file():
            ho = hp.read_text(encoding="utf-8")
            hn = _patch_hbcm_html_metrics(ho, m)
            if hn != ho:
                hp.write_bytes(hn.encode("utf-8"))
                check_html_js_syntax(hp)

    portal_changed = git_push_if_changed(
        portal_dir,
        "jintai-domestic-portal",
        f"chore(portal): auto-reconcile 4-site live metrics ({m['d1_entries']:,} entries, {m['film_works']:,} films, {m['sc_total']:,} sounds, {m['zh_records']:,} relics)",
        auto_push,
    )

    hbcm_gh = Path(r"C:\Users\KingT\Documents\Claude产出\2026-11-03_金泰AI影视全栈平台能力方案与动态美学网页\gh_pages_site")
    hbcm_changed = []
    if (hbcm_gh / ".git").is_dir() and (portal_dir / "hbcm.html").is_file() and (portal_dir / "hbcm-m.html").is_file():
        git_prepare_repo(hbcm_gh, auto_push)
        desk_bytes = (portal_dir / "hbcm.html").read_bytes()
        mob_bytes = (portal_dir / "hbcm-m.html").read_bytes()
        for dfn in ("index.html", "01_金泰AI影视艺术全栈智算平台_面向河传师生能力全景动态展映台.html"):
            dp = hbcm_gh / dfn
            if not dp.is_file() or dp.read_bytes() != desk_bytes:
                dp.write_bytes(desk_bytes)
        for mfn in ("m.html", "mobile.html", "05_金泰AI影视艺术全栈智算平台_面向河传师生手机版.html"):
            mp = hbcm_gh / mfn
            if not mp.is_file() or mp.read_bytes() != mob_bytes:
                mp.write_bytes(mob_bytes)
        for mirror_dir in (
            hbcm_gh.parent,
            Path(r"C:\Users\KingT\jintai-internal\2026-11-03_金泰AI平台面向河传能力全景方案"),
        ):
            if mirror_dir.is_dir():
                for src_b, tname in (
                    (desk_bytes, "01_金泰AI影视艺术全栈智算平台_面向河传师生能力全景动态展映台.html"),
                    (mob_bytes, "05_金泰AI影视艺术全栈智算平台_面向河传师生手机版.html"),
                ):
                    tp = mirror_dir / tname
                    if tp.is_file() and tp.read_bytes() != src_b:
                        tp.write_bytes(src_b)
        hbcm_changed = git_push_if_changed(
            hbcm_gh,
            "jintai-hbcm-ai-platform",
            f"chore(hbcm): auto-reconcile 4-library live metrics ({m['film_works']:,} films / {m['sc_total']:,} sounds / {m['zh_records']:,} relics)",
            auto_push,
        )

    return {
        "site": "portal_and_hbcm",
        "status": "updated" if (portal_changed or hbcm_changed) else "up-to-date",
        "portal_changed": len(portal_changed),
        "hbcm_changed": len(hbcm_changed),
        "metrics": m,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["all", "history", "shengcang", "documentary", "zhonghua", "portal"], default="all")
    ap.add_argument("--repo-dir", type=str, default="")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--optimize-zhonghua-local", action="store_true")
    args = ap.parse_args()

    auto_push = not args.no_push
    root = Path(r"C:\Users\KingT\Documents\Claude产出\2026-10-30_四大网站国内直连部署")

    if args.optimize_zhonghua_local:
        d = Path(args.repo_dir) if args.repo_dir else (root / "03_zhonghua-civilization-atlas")
        print(json.dumps(optimize_zhonghua_site(d), ensure_ascii=False, indent=2))
        return

    results = []
    if args.only in ("all", "history") and not args.repo_dir:
        # A partial-clone diff can lazily download multi-GB Git packs. Keep the
        # other site mirrors live while disk-space recovery is in progress.
        if (root / ".pause_history_sync").is_file():
            results.append({"site": "history", "status": "paused_low_disk"})
        else:
            results.append(sync_history_site1(auto_push=auto_push))
    if args.only in ("all", "shengcang"):
        d = Path(args.repo_dir) if args.repo_dir else (root / "01_shengcang-sound-library")
        results.append(sync_shengcang(d, auto_push=auto_push))
    if args.only in ("all", "documentary"):
        d = Path(args.repo_dir) if args.repo_dir else (root / "02_documentary-classroom-library")
        results.append(sync_documentary(d, auto_push=auto_push))
    if args.only in ("all", "zhonghua"):
        d = Path(args.repo_dir) if args.repo_dir else (root / "03_zhonghua-civilization-atlas")
        results.append(sync_zhonghua(d, auto_push=auto_push))
    if args.only in ("all", "portal") and not args.repo_dir:
        results.append(sync_portal_and_hbcm_metrics(root, auto_push=auto_push))

    print(json.dumps({"synced_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
