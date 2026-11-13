/* A long-lived tab keeps its original JS/data in memory. Announce a new static
   snapshot without replacing data under an active search or management action. */
(function () {
  'use strict';
  var meta = document.querySelector('meta[name="atlas-snapshot-revision"]');
  var current = meta && meta.getAttribute('content');
  if (!/^[a-f0-9]{64}$/.test(current || '') || typeof fetch !== 'function') return;
  var checking = false, attemptedAt = 0, nextRevision = null, notice = null, refreshTimer = null;
  function hasActiveState() {
    var path = (location.pathname || '').toLowerCase();
    if (/\/manage(?:\.html)?\/?$/.test(path)) return true;
    var params;
    try { params = new URLSearchParams(location.search || ''); } catch (_) { params = null; }
    if (params && ['q', 'era', 'category', 'period', 'batch', 'item'].some(function (key) { return params.has(key); })) return true;
    var active = document.activeElement;
    return !!(active && /^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName || ''));
  }
  function reloadLatest() {
    if (!nextRevision || hasActiveState() || document.visibilityState === 'hidden') return;
    var url = new URL(location.href);
    url.searchParams.set('atlas-update', nextRevision);
    location.replace(url.href);
  }
  function announce(revision) {
    nextRevision = revision;
    if (notice || !document.body) return;
    var style = document.createElement('style');
    style.textContent = '.atlas-version-notice{position:fixed;z-index:10000;bottom:16px;left:50%;transform:translateX(-50%);box-sizing:border-box;width:max-content;max-width:calc(100% - 24px);display:flex;gap:12px;align-items:center;padding:12px 16px;border:1px solid #bca581;border-radius:8px;background:#fffaf0;color:#302a23;box-shadow:0 3px 18px #0002;font:14px/1.5 sans-serif}.atlas-version-notice button{flex-shrink:0;border:1px solid #6c5638;border-radius:4px;padding:7px 10px;background:#6c5638;color:#fff;font:inherit;cursor:pointer}@media(max-width:560px){.atlas-version-notice{align-items:flex-start;flex-direction:column}}';
    document.head.appendChild(style);
    notice = document.createElement('aside');
    notice.id = 'atlasVersionUpdate'; notice.className = 'atlas-version-notice';
    notice.setAttribute('role', 'status'); notice.setAttribute('aria-live', 'polite');
    var text = document.createElement('span');
    text.textContent = '网站内容已更新。当前页面仍是较早的目录快照。';
    var button = document.createElement('button'); button.type = 'button'; button.textContent = '加载最新内容';
    button.addEventListener('click', function () {
      if (refreshTimer) clearTimeout(refreshTimer);
      reloadLatest();
    });
    notice.appendChild(text); notice.appendChild(button); document.body.appendChild(notice);
    // A public page with no active filters is safe to refresh automatically.
    // Keep management/search sessions manual so a release cannot discard work.
    if (!hasActiveState()) refreshTimer = setTimeout(reloadLatest, 4000);
  }
  async function check(force) {
    if (checking || document.visibilityState === 'hidden' || !force && attemptedAt && Date.now() - attemptedAt < 15000) return;
    checking = true; attemptedAt = Date.now();
    var controller = typeof AbortController === 'function' ? new AbortController() : null;
    var timeout = controller && setTimeout(function () { controller.abort(); }, 15000);
    try {
      var response = await fetch(new URL('/site-version.json', location.href).href, { cache: 'no-store', credentials: 'same-origin', redirect: 'error', signal: controller ? controller.signal : undefined });
      if (!response.ok) return;
      var data = await response.json();
      if (data && data.schemaVersion === 1 && /^[a-f0-9]{64}$/.test(data.revision || '') && data.revision !== current) announce(data.revision);
    } catch (_) { /* A failed check makes no freshness claim; retry on visibility/timer. */ }
    finally { if (timeout) clearTimeout(timeout); checking = false; }
  }
  setTimeout(function () { check(false); }, 1500);
  setInterval(function () { check(false); }, 60000);
  document.addEventListener('visibilitychange', function () { if (document.visibilityState !== 'hidden') check(true); });
  window.addEventListener('pageshow', function (event) { check(!!event.persisted); });
}());
