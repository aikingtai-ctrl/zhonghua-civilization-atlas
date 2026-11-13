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
ZH_SHIM_REV = "20261113f2"
SC_SHIM = """<style>a[href*="signin-with-chatgpt"]{display:none!important}</style><script id="jintai-shengcang-shim">(function(){
var BASE=new URL('.',location.href).pathname;if(BASE.slice(-1)!=='/')BASE+='/';window.__JT_BASE__=BASE;
var IS_GH=/github\\.io$/i.test(location.hostname||'');
var RAW='https://raw.githubusercontent.com/aikingtai-ctrl/shengcang-sound-library/main/';
var CDNS=['https://testingcf.jsdelivr.net/gh/aikingtai-ctrl/shengcang-sound-library@main/','https://gcore.jsdelivr.net/gh/aikingtai-ctrl/shengcang-sound-library@main/'];
function resolveMedia(rel){if(!rel||typeof rel!=='string')return rel;var clean=rel.replace(/^\\.\\//,'').replace(/^\\//,'');if(!/^(audio|images)\\//.test(clean))return rel;return BASE+clean;}
window.addEventListener('error',function(ev){var el=ev.target;if(!el||!el.tagName)return;var tag=el.tagName.toUpperCase();if(tag!=='AUDIO'&&tag!=='SOURCE'&&tag!=='IMG')return;var cur=el.getAttribute('src')||el.src||'';var m=cur.match(/(?:shengcang-sound-library(?:@main|\\/main)\\/|\\/)((?:audio|images)\\/[^?#]+)/);if(!m)return;var clean=m[1];var step=parseInt(el.getAttribute('data-jt-fb')||'0',10);var cands=IS_GH?[RAW+clean,CDNS[0]+clean,CDNS[1]+clean]:[CDNS[0]+clean,RAW+clean];if(step<cands.length){el.setAttribute('data-jt-fb',String(step+1));el.src=cands[step];if(tag==='AUDIO'&&typeof el.load==='function')el.load();}},true);
document.addEventListener('click',function(ev){var a=ev.target&&ev.target.closest?ev.target.closest('a'):null;if(!a)return;var hr=a.getAttribute('href')||'';if(hr.indexOf('signin-with-chatgpt')!==-1){ev.preventDefault();return;}if(/^\\/(audio|images)\\//.test(hr)){a.setAttribute('href',resolveMedia(hr));}},true);
var _dbPromise=null;var origFetch=window.fetch.bind(window);window.__jtOrigFetch=origFetch;
function getSoundsDB(){if(_dbPromise)return _dbPromise;var cb='?t='+Math.floor(Date.now()/300000);var urls=IS_GH?[BASE+'data/sounds.json'+cb,RAW+'data/sounds.json'+cb,CDNS[0]+'data/sounds.json'+cb]:[BASE+'data/sounds.json'+cb,CDNS[0]+'data/sounds.json'+cb];_dbPromise=(async function(){for(var i=0;i<urls.length;i++){try{var r=await origFetch(urls[i]);if(r.ok){var d=await r.json();var arr=Array.isArray(d)?d:(d.sounds||[]);arr.forEach(function(it){if(it.src)it.src=resolveMedia(it.src);if(Array.isArray(it.variants))it.variants.forEach(function(v){if(v&&v.src)v.src=resolveMedia(v.src);});});return Array.isArray(d)?{sounds:arr,raw:arr}:{sounds:arr,raw:d};}}catch(e){}}return {sounds:[],raw:{sounds:[]}};})();return _dbPromise;}
window.fetch=async function(input,init){var urlStr=typeof input==='string'?input:(input&&input.url?input.url:String(input));var u;try{u=new URL(urlStr,location.origin);}catch(e){return origFetch(input,init);}var p=u.pathname;var idxApi=p.indexOf('/api/sounds');if(idxApi!==-1){var method=((init&&init.method)||(input&&input.method)||'GET').toUpperCase();if(method!=='GET')return new Response(JSON.stringify({error:'国内直连只读镜像节点'}),{status:400,headers:{'Content-Type':'application/json;charset=utf-8'}});if(u.searchParams.get('community')==='1')return new Response(JSON.stringify({sounds:[]}),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});var db=await getSoundsDB();var after=p.slice(idxApi+'/api/sounds'.length);if(after&&after!=='/'){var sid=decodeURIComponent(after.replace(/^\\//,''));var found=db.sounds.find(function(x){return String(x.id)===sid;});if(found)return new Response(JSON.stringify(found),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});return new Response(JSON.stringify({error:'Not found'}),{status:404,headers:{'Content-Type':'application/json;charset=utf-8'}});}return new Response(JSON.stringify(db.raw),{status:200,headers:{'Content-Type':'application/json;charset=utf-8'}});}if(u.origin===location.origin&&p.indexOf(BASE)!==0&&(/^\\/(audio|images)\\//.test(p)||/^\\/catalogue-[A-Za-z0-9_.-]+\\.json$/.test(p)))return origFetch(BASE+p.slice(1)+u.search,init);return origFetch(input,init);};
})();</script>"""


def sync_shengcang(site_dir: Path, auto_push: bool = True) -> dict:
    git_prepare_repo(site_dir, auto_push)
    base = "https://shengcang-sound-library.fondcream1.chatgpt.site"
    st_h, b_h = fetch_bytes(base + "/")
    st_a, b_a = fetch_bytes(base + "/api/sounds")
    if st_h != 200 or st_a != 200:
        return {"site": "shengcang", "status": "upstream_skipped", "http": [st_h, st_a]}

    clean_html = strip_cf_challenge(b_h.decode("utf-8"))
    cat_refs = sorted(set(re.findall(r"/catalogue-[A-Za-z0-9_.-]+\.json", clean_html)))
    api_data = json.loads(b_a.decode("utf-8"))
    norm_sounds = json.dumps(api_data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    fp = sha256_bytes(clean_html.encode("utf-8") + b"|" + norm_sounds + b"|" + SHIM_REV.encode("ascii"))

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


def optimize_zhonghua_js_bytes(rel: str, data: bytes) -> bytes:
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
        "var pendingDetail=null;"
        "document.addEventListener('click',function(e){if(window.__JT_HYDRATED__)return;var b=e.target&&e.target.closest?e.target.closest('[data-detail]'):null;if(b){e.preventDefault();pendingDetail=b.getAttribute('data-detail');}},true);"
        "function loadTag(u){return new Promise(function(res){var s=document.createElement('script');s.src=u;s.onload=function(){res(true);};s.onerror=function(){res(false);};document.head.appendChild(s);});}"
        "async function runList(list){if(!list.length)return;if(location.protocol==='file:'){for(var i=0;i<list.length;i++)await loadTag(list[i]);return;}"
        "var tasks=list.map(function(u){return fetch(u).then(function(r){if(!r.ok)throw new Error(r.status);return r.text();});});"
        "for(var j=0;j<list.length;j++){try{var c=await tasks[j];var s=document.createElement('script');s.textContent=c+'\\n//# sourceURL='+list[j];document.head.appendChild(s);s.remove();if(c.length>2000000)await new Promise(function(r){setTimeout(r,0);});}catch(err){await loadTag(list[j]);}}}"
        "async function boot(){await runList(p1);if(window.__jtSanitizeAll)window.__jtSanitizeAll();window.__JT_HYDRATED__=true;"
        "if(['#tangReignDossier','#xixiaReignDossier'].indexOf(location.hash)!==-1)window.dispatchEvent(new Event('load'));"
        "if(pendingDetail&&typeof window.detail==='function'){try{window.detail(pendingDetail);}catch(e){}}"
        "if(p2.length){var rp=function(){runList(p2);};if(typeof requestIdleCallback==='function')requestIdleCallback(rp,{timeout:600});else setTimeout(rp,350);}}"
        "if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){setTimeout(boot,0);},{once:true});else setTimeout(boot,0);"
        "})();"
    )
    return f'<script id="jt-zh-async-loader" data-all="{a_attr}" data-p1="{p1_attr}" data-p2="{p2_attr}">{code}</script>'


def _compute_zhonghua_ssg_payload(site_dir: Path) -> dict | None:
    if not (site_dir / "data.js").is_file():
        return None
    node_js = r"""
const fs = require('fs'), path = require('path'), vm = require('vm');
const dir = process.argv[1];
const ctx = { window: {} };
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(dir, 'data.js'), 'utf8'), ctx);
for (let i = 1; i <= 20; i++) {
  const p = path.join(dir, `catalog-records-${i}.js`);
  if (fs.existsSync(p)) vm.runInContext(fs.readFileSync(p, 'utf8'), ctx);
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
    r = subprocess.run(["node", "-e", node_js, str(site_dir)], capture_output=True, text=True, encoding="utf-8", timeout=45)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return json.loads(r.stdout)


def optimize_zhonghua_site(site_dir: Path) -> dict:
    import html as _html
    js_hashes: dict[str, str] = {}
    js_modified = 0
    for jp in sorted(site_dir.glob("*.js")):
        raw = jp.read_bytes()
        opt = optimize_zhonghua_js_bytes(jp.name, raw)
        if opt != raw:
            jp.write_bytes(opt)
            js_modified += 1
        js_hashes[jp.name] = sha256_bytes(opt)[:12]

    ssg = _compute_zhonghua_ssg_payload(site_dir)
    gate_tag = make_gate_script("金泰 AI · 中华文明影像库")
    html_modified = 0

    for hp in sorted(site_dir.rglob("*.html")):
        if ".git" in hp.parts:
            continue
        orig = hp.read_text(encoding="utf-8", errors="ignore")
        txt = orig

        # 1. Refresh unified gate & ZH_SHIM
        txt = re.sub(r'<style>a\[href\*="signin-with-chatgpt"\][^<]*</style><script id="jintai-zhonghua-cdn-shim">.*?</script>', ZH_SHIM, txt, count=1, flags=re.S)
        txt = re.sub(r'<script id="jt-unified-gate">.*?</script>', gate_tag, txt, count=1, flags=re.S)

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
        m_existing = re.search(r'<script id="jt-zh-async-loader"[^>]*\bdata-all="([^"]+)"[^>]*>.*?</script>(?=\s*</body>)', txt, flags=re.S)
        m_raw = None if m_existing else re.search(r'((?:<script\s+src="[^"]+"\s*></script>\s*)+)(?=</body>)', txt, flags=re.I)
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

    return {"js_modified": js_modified, "html_modified": html_modified, "ssg_records": ssg.get("total") if ssg else 0}


def sync_zhonghua(site_dir: Path, auto_push: bool = True) -> dict:
    git_prepare_repo(site_dir, auto_push)
    host = "zhonghua-civilization-atlas.fondcream1.chatgpt.site"
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://{host}/", headers={"User-Agent": UA}), timeout=15) as r_eff:
            eff_netloc = urllib.parse.urlparse(r_eff.geturl()).netloc
            if eff_netloc:
                host = eff_netloc
    except Exception:
        pass
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
    quick_fp = "|".join(probe_parts + [ZH_SHIM_REV])

    state_p = site_dir / ".sync_state.json"
    required_aux = (
        (site_dir / "site-version.json").is_file()
        and (site_dir / "publication-proofs" / "build-report.json").is_file()
    )
    if state_p.is_file() and required_aux:
        try:
            if json.loads(state_p.read_text(encoding="utf-8")).get("quick_fp") == quick_fp:
                return {"site": "zhonghua", "status": "up-to-date"}
        except Exception:
            pass

    text_exts = {".html", ".css", ".js", ".json", ".md", ".svg", ".txt"}
    asset_exts = {".webp", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".woff", ".woff2"}
    to_visit = {"index.html", "site-version.json", "publication-proofs/build-report.json"}
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
                if ext == ".css":
                    for ref in re.findall(r'url\(["\']?([^"\')]+)["\']?\)', txt, flags=re.I):
                        nr = norm_zh_rel(rel, ref)
                        if nr:
                            discovered_media.add(nr)
                elif ext in (".js", ".json"):
                    for m in re.finditer(r'["\'`]((?:\./)?(?:assets|(?:[A-Za-z0-9_-]+-)?images|research-[A-Za-z0-9_-]+)/[^"\'`\s?#]+|(?:[A-Za-z0-9_-]+\.html))(?:\?[^"\'`\s#]*)?["\'`]', txt):
                        nr = norm_zh_rel(rel, m.group(1))
                        if nr:
                            rext = os.path.splitext(nr)[1].lower()
                            if rext == ".html":
                                to_visit.add(nr)
                            elif rext in asset_exts:
                                discovered_media.add(nr)

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

    # Align <meta name="atlas-snapshot-revision"> in all synced HTML pages with site-version.json so freshly opened tabs never enter a false update-banner loop
    sv_path = site_dir / "site-version.json"
    if sv_path.is_file():
        try:
            sv_rev = json.loads(sv_path.read_text(encoding="utf-8")).get("revision", "")
            if re.fullmatch(r"[0-9a-f]{64}", sv_rev):
                for hp in site_dir.rglob("*.html"):
                    if ".git" in hp.parts:
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

    optimize_zhonghua_site(site_dir)
    all_unhosted = sorted((prev_unhosted | newly_unhosted) - {m for m in discovered_media if (site_dir / m).is_file()})
    state_p.write_text(json.dumps({"quick_fp": quick_fp, "docs": len(visited), "new_media": len(missing_media) - len(newly_unhosted), "unhosted_media": all_unhosted}, indent=2), encoding="utf-8")
    changed = git_push_if_changed(site_dir, "zhonghua-civilization-atlas", f"sync(auto): upstream zhonghua atlas ({len(visited)} docs)", auto_push)
    return {"site": "zhonghua", "status": "updated" if changed else "up-to-date", "changed_files": len(changed), "new_media": len(missing_media)}


def sync_history_site1() -> dict:
    hist_mgr = Path(r"C:\Users\KingT\jintai-internal\中国历史文化图库\每日更新\管理\ensure_domestic_compact_index.py")
    cat_sync = Path(r"C:\Users\KingT\jintai-internal\中国历史文化图库\每日更新\管理\sync_all_category_pages.py")
    pub = Path(r"C:\Users\KingT\jintai-internal\中国历史文化图库\每日更新\publish_checkout_20261012")
    if not hist_mgr.is_file() or not pub.is_dir():
        return {"site": "history", "status": "skipped_not_local"}
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
    st = subprocess.run(["git", "-C", str(pub), "status", "--porcelain", "--"] + existing_targets, capture_output=True, text=True)
    if st.stdout.strip():
        subprocess.run(["git", "-C", str(pub), "add", "--"] + existing_targets, check=True)
        subprocess.run(["git", "-C", str(pub), "commit", "-m", "sync(auto): refresh domestic compact index, specialist category pages & WeChat gate"], check=True)
        subprocess.run(["git", "-C", str(pub), "push", "origin", "HEAD:main"], check=True, timeout=240)
        return {"site": "history", "status": "updated"}
    return {"site": "history", "status": "up-to-date"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["all", "history", "shengcang", "documentary", "zhonghua"], default="all")
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
