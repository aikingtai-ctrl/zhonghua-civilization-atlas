/* Read-only operational view. All state comes from the generated audit snapshot. */
(function () {
  'use strict';
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function n(value) { return Number(value || 0).toLocaleString('zh-CN'); }
  function date(value) {
    if (!value) return '未记录';
    var d = new Date(value);
    return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false });
  }
  function snapshotFreshness(value) {
    var time = Date.parse(value || '');
    if (!Number.isFinite(time)) return { text: '新鲜度未知', stale: true };
    var minutes = Math.max(0, Math.round((Date.now() - time) / 60000));
    return { text: minutes < 30 ? '数据新鲜（约 ' + minutes + ' 分钟前）' : '需刷新（约 ' + minutes + ' 分钟前）', stale: minutes >= 30 };
  }
  function mount() {
    var anchor = document.getElementById('expansionQueue');
    if (!anchor || document.getElementById('atlasControlConsole')) return;
    var data = window.ATLAS_CONTROL_CONSOLE;
    var section = el('section', 'atlas-control');
    section.id = 'atlasControlConsole';
    section.setAttribute('aria-labelledby', 'atlasControlTitle');
    anchor.parentNode.insertBefore(section, anchor);
    if (!data || !data.totals) {
      section.appendChild(el('p', 'ac-warning', '扩库控制台快照未加载，请刷新页面或下载审核数据核对。'));
      return;
    }
    var head = el('div', 'ac-heading');
    var titleBox = el('div');
    titleBox.appendChild(el('div', 'eyebrow', 'ACQUISITION CONTROL · AUDIT SNAPSHOT'));
    var title = el('h2', '', '扩库任务控制台'); title.id = 'atlasControlTitle';
    titleBox.appendChild(title);
    var stamp = el('p', 'ac-stamp');
    stamp.appendChild(el('span', '', '快照时间（北京时间） ' + date(data.measuredAt) + ' · '));
    var freshness = snapshotFreshness(data.measuredAt);
    stamp.appendChild(el('span', freshness.stale ? 'ac-stamp-stale' : 'ac-stamp-fresh', freshness.text));
    stamp.setAttribute('aria-label', '快照时间（北京时间） ' + date(data.measuredAt) + '，' + freshness.text);
    titleBox.appendChild(stamp);
    head.appendChild(titleBox);
    var download = el('button', 'secondary ac-download', '下载控制台 JSON ↓');
    download.type = 'button';
    download.addEventListener('click', function () {
      var url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8' }));
      var a = el('a'); a.href = url; a.download = 'atlas-control-console.json';
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    });
    head.appendChild(download); section.appendChild(head);
    var metrics = el('div', 'ac-metrics');
    [
      ['主目录唯一记录', data.totals.records, '含历史目录，数量不代表已全库复核'],
      ['新流程真实入库', data.totals.admitted, '合并目录中的核验记录，按唯一 ID 计数'],
      ['待审核候选', data.totals.pending, '未计入新流程入库'],
      ['审核淘汰', data.totals.rejected, '按最新审核决定去重'],
      ['历史失败请求', data.totals.failedRequests, '请求次数，非缺失图像数'],
      ['可追溯批次', data.totals.batches, '批次详情与来源状态见下方']
    ].forEach(function (metric) {
      var box = el('div', 'ac-metric');
      box.appendChild(el('span', 'ac-metric-label', metric[0]));
      box.appendChild(el('strong', '', n(metric[1])));
      box.appendChild(el('small', '', metric[2])); metrics.appendChild(box);
    }); section.appendChild(metrics);
    section.appendChild(el('p', 'ac-note', data.note || '本地核验入库与线上发布分别记录；候选不计为正式入库。'));
    var periods = el('div', 'ac-periods');
    var phead = el('div', 'ac-subheading');
    phead.appendChild(el('h3', '', '全时期覆盖与缺口'));
    phead.appendChild(el('span', '', '目录口径与新流程核验口径分别呈现'));
    section.appendChild(phead);
    (data.periods || []).forEach(function (period) {
      var card = el('article', 'ac-period');
      card.appendChild(el('h4', '', period.name));
      var count = el('p', 'ac-period-count'); count.appendChild(el('strong', '', n(period.records))); count.appendChild(el('span', '', '目录记录')); card.appendChild(count);
      var line = el('div', 'ac-period-meta');
      line.appendChild(el('span', '', '核验入库 ' + n(period.admitted)));
      line.appendChild(el('span', '', '待审 ' + n(period.pending))); card.appendChild(line);
      var target = period.target === null || period.target === undefined ? null : Number(period.target);
      card.appendChild(el('p', 'ac-progress-label', '目录规模进度'));
      var progress = el('div', 'ac-period-bar');
      if (target && target > 0) {
        var filled = el('span'); filled.style.width = Math.min(100, Math.max(0, Number(period.records || 0) / target * 100)) + '%'; progress.appendChild(filled);
        progress.setAttribute('role', 'progressbar'); progress.setAttribute('aria-label', period.name + '目录目标进度'); progress.setAttribute('aria-valuemin', '0'); progress.setAttribute('aria-valuemax', String(target)); progress.setAttribute('aria-valuenow', String(Math.min(target, Number(period.records || 0))));
      } else { progress.classList.add('ac-unallocated'); progress.setAttribute('aria-label', '未分配目标'); }
      card.appendChild(progress);
      card.appendChild(el('p', 'ac-progress-label ac-admitted-progress-label', '核验入库进度'));
      var admittedProgress = el('div', 'ac-period-bar ac-period-bar-admitted');
      if (target && target > 0) {
        var admittedFilled = el('span'); admittedFilled.style.width = Math.min(100, Math.max(0, Number(period.admitted || 0) / target * 100)) + '%'; admittedProgress.appendChild(admittedFilled);
        admittedProgress.setAttribute('role', 'progressbar'); admittedProgress.setAttribute('aria-label', period.name + '核验入库目标进度'); admittedProgress.setAttribute('aria-valuemin', '0'); admittedProgress.setAttribute('aria-valuemax', String(target)); admittedProgress.setAttribute('aria-valuenow', String(Math.min(target, Number(period.admitted || 0))));
      } else { admittedProgress.classList.add('ac-unallocated'); admittedProgress.setAttribute('aria-label', '未分配目标'); }
      card.appendChild(admittedProgress);
      card.appendChild(el('p', 'ac-period-gap', target === null ? '目标未分配 · 缺口待考' : '目标 ' + n(target) + ' · 缺口 ' + n(period.gap)));
      card.appendChild(el('p', 'ac-period-note', period.note || ''));
      periods.appendChild(card);
    }); section.appendChild(periods);
    var state = el('div', 'ac-source-state');
    var queue = data.queue || {};
    var queueBox = el('div', 'ac-queue-state');
    queueBox.appendChild(el('h3', '', '采集队列与执行边界'));
    queueBox.appendChild(el('p', '', '计划队列 ' + n(queue.planned) + ' · ' + (queue.status || '未提供')));
    if (queue.reason) queueBox.appendChild(el('p', 'ac-note', queue.reason));
    if (queue.nextAction) queueBox.appendChild(el('p', 'ac-next-action', '下一步：' + queue.nextAction));
    var discovery = data.discoveryLeads || {};
    if (Number(discovery.count)) {
      var leadBox = el('details', 'ac-discovery-leads');
      leadBox.appendChild(el('summary', '', '官方来源线索核对 ' + n(discovery.count) + ' 条（不计入候选／正式入库）'));
      leadBox.appendChild(el('p', 'ac-note', discovery.note || '官方来源发现线索仅供后续采集复核，不计入候选或正式入库。'));
      leadBox.appendChild(el('p', 'ac-note', '已有目录 ' + n(discovery.alreadyCataloged) + ' · 已在待审队列 ' + n(discovery.pending) + ' · 尚未采集 ' + n(discovery.uncollected) + ' · 来源待核 ' + n(discovery.invalid)));
      (discovery.entries || []).forEach(function (lead) {
        var row = el('p', 'ac-note');
        var leadLabels = { 'already-cataloged': '已有目录／需按需补充复核', 'pending-candidate': '已有待审候选', 'uncollected': '尚未采集', 'invalid-source': '来源待核' };
        row.appendChild(el('strong', '', (leadLabels[lead.resolvedStatus] || '状态待核') + ' · '));
        var url = String(lead.objectUrl || '');
        if (/^https:\/\/[^\s]+$/i.test(url)) {
          var link = el('a', '', (lead.objectId ? String(lead.objectId) + ' · ' : '') + (lead.title || '未命名线索'));
          link.href = url; link.target = '_blank'; link.rel = 'noopener'; row.appendChild(link);
        } else row.appendChild(el('span', '', (lead.objectId ? String(lead.objectId) + ' · ' : '') + (lead.title || '未命名线索')));
        if (lead.period || lead.date) row.appendChild(el('span', '', ' · ' + [lead.period, lead.date].filter(Boolean).join(' · ')));
        if (lead.reason) row.appendChild(el('small', 'ac-note', ' · ' + lead.reason));
        if (lead.catalogRecordIds && lead.catalogRecordIds.length) row.appendChild(el('small', 'ac-note', ' · 对应目录 ID：' + lead.catalogRecordIds.join('、')));
        if (lead.candidateIds && lead.candidateIds.length) row.appendChild(el('small', 'ac-note', ' · 对应候选 ID：' + lead.candidateIds.join('、')));
        leadBox.appendChild(row);
      });
      queueBox.appendChild(leadBox);
    }
    queueBox.appendChild(el('small', 'ac-note', '本页为只读快照；重试、限流和断点续采须在采集脚本执行后重新生成快照。'));
    state.appendChild(queueBox);
    var holdBox = el('div', 'ac-holds'); holdBox.appendChild(el('h3', '', '来源暂停与待复查'));
    var holds = data.holds || [];
    if (!holds.length) holdBox.appendChild(el('p', 'ac-note', '当前快照未记录来源暂停；这不等同于各来源可用性检测通过。'));
    holds.forEach(function (hold) {
      var row = el('details', 'ac-hold');
      row.appendChild(el('summary', '', hold.provider + ' · 暂停／待复查'));
      row.appendChild(el('p', '', hold.reason));
      row.appendChild(el('small', '', '记录时间：' + date(hold.at)));
      if (hold.retryAfter) row.appendChild(el('small', '', '下次复查：' + date(hold.retryAfter)));
      holdBox.appendChild(row);
    }); state.appendChild(holdBox); section.appendChild(state);
    var tableHead = el('div', 'ac-subheading'); tableHead.appendChild(el('h3', '', '批次运行记录')); section.appendChild(tableHead);
    var tools = el('div', 'ac-tools');
    function field(label, node) { var wrapper = el('label', 'ac-field'); wrapper.appendChild(el('span', '', label)); wrapper.appendChild(node); tools.appendChild(wrapper); return node; }
    var search = field('搜索批次或失败原因', el('input')); search.type = 'search'; search.placeholder = '输入批次 ID、来源、原因或来源 SHA';
    var provider = field('来源', el('select')); var status = field('批次状态', el('select'));
    function options(select, items, all) { var option = el('option', '', all); option.value = ''; select.appendChild(option); items.forEach(function (value) { var o = el('option', '', value); o.value = value; select.appendChild(o); }); }
    var batches = Array.isArray(data.batches) ? data.batches : [];
    options(provider, Array.from(new Set(batches.map(function (b) { return b.provider; }))).filter(Boolean).sort(), '全部来源');
    options(status, Array.from(new Set(batches.map(function (b) { return b.status; }))).filter(Boolean).sort(), '全部状态');
    var reset = el('button', 'secondary ac-reset', '清除筛选'); reset.type = 'button'; tools.appendChild(reset); section.appendChild(tools);
    var live = el('p', 'ac-result-count'); live.setAttribute('aria-live', 'polite'); section.appendChild(live);
    var tableWrap = el('div', 'ac-table-wrap'); tableWrap.tabIndex = 0; tableWrap.setAttribute('role', 'region'); tableWrap.setAttribute('aria-label', '扩库批次表，可横向滚动');
    var table = el('table', 'ac-table');
    var caption = el('caption', 'ac-sr-only', '批次候选、入库、待审核和历史请求失败数量'); table.appendChild(caption);
    var thead = el('thead'); var headerRow = el('tr');
    ['批次 / 来源', '状态', '采集候选', '已入库', '待审核', '淘汰', '失败请求'].forEach(function (text) { var th = el('th', '', text); th.scope = 'col'; headerRow.appendChild(th); }); thead.appendChild(headerRow); table.appendChild(thead);
    var tbody = el('tbody'); table.appendChild(tbody); tableWrap.appendChild(table); section.appendChild(tableWrap);
    var pager = el('div', 'ac-pagination');
    var prev = el('button', 'secondary', '← 上一页'); prev.type = 'button';
    var pageInfo = el('span'); var next = el('button', 'secondary', '下一页 →'); next.type = 'button';
    pager.appendChild(prev); pager.appendChild(pageInfo); pager.appendChild(next); section.appendChild(pager);
    var page = 1, perPage = 12;
    function render() {
      var term = search.value.trim().toLocaleLowerCase();
      var filtered = batches.filter(function (b) {
        var lineage = b.reconciliation || {};
        return (!provider.value || b.provider === provider.value) && (!status.value || b.status === status.value) && (!term || [b.batchId, b.provider, b.status, lineage.originalBatchId, lineage.sourceManifestSha256, lineage.originalAcceptedSha256, lineage.run].concat(b.failureReasons || [], (b.collectionExclusionReasons || []).map(function (reason) { return reason.code; })).join(' ').toLocaleLowerCase().includes(term));
      });
      var pages = Math.max(1, Math.ceil(filtered.length / perPage)); page = Math.min(page, pages);
      tbody.replaceChildren();
      filtered.slice((page - 1) * perPage, page * perPage).forEach(function (b) {
        var tr = el('tr'); var name = el('td'); name.appendChild(el('strong', 'ac-batch-id', b.batchId)); name.appendChild(el('small', 'ac-batch-source', b.provider + ' · ' + b.date));
        var lineage = b.reconciliation;
        if (lineage && lineage.newNetworkAcquisitions === 0) {
          name.appendChild(el('small', 'ac-batch-source', '历史迁入 ' + n(lineage.retainedRecords) + ' 条 · 新采 0；原批次 ' + lineage.originalBatchId + '；原日期 ' + lineage.originalPublicationDate));
          name.appendChild(el('small', 'ac-batch-source', '按原日期保留，未重复计为本日采集；来源清单 SHA ' + String(lineage.sourceManifestSha256 || '').slice(0, 12) + '… · 原接收 SHA ' + String(lineage.originalAcceptedSha256 || '').slice(0, 12) + '…'));
        }
        if (Number(b.transferredImports)) name.appendChild(el('small', 'ac-batch-source', n(b.transferredImports) + ' 条已转至其他批次入库；不重复计数'));
        if (Number(b.collectionExcluded)) {
          name.appendChild(el('small', 'ac-batch-source', '采集未形成候选 ' + n(b.collectionExcluded) + ' 次（含排重／范围／本地问题），其中重复 ' + n(b.collectionDuplicateCount) + ' 次；按采集事件计数'));
          var exclusions = el('details', 'ac-failure');
          exclusions.appendChild(el('summary', '', '展开采集排除与本地问题'));
          var exclusionList = el('ul');
          (b.collectionExclusionReasons || []).forEach(function (reason) { exclusionList.appendChild(el('li', '', reason.code + ' · ' + n(reason.count) + ' 次')); });
          exclusions.appendChild(exclusionList); name.appendChild(exclusions);
        }
        if (b.failureReasons && b.failureReasons.length) {
          var details = el('details', 'ac-failure'); details.appendChild(el('summary', '', '展开失败原因（' + b.failureReasons.length + ' 类）'));
          var reasons = el('ul'); b.failureReasons.forEach(function (r) { reasons.appendChild(el('li', '', r)); }); details.appendChild(reasons); name.appendChild(details);
        }
        tr.appendChild(name); var stateCell = el('td'); var badge = el('span', 'ac-status', b.status);
        if (Number(b.pending)) badge.classList.add('ac-status-pending'); else if (Number(b.failedRequests)) badge.classList.add('ac-status-failed'); stateCell.appendChild(badge); tr.appendChild(stateCell);
        ['collected', 'imported', 'pending', 'rejected', 'failedRequests'].forEach(function (key) { tr.appendChild(el('td', 'ac-number' + (key === 'imported' ? ' ac-admitted' : ''), n(b[key]))); }); tbody.appendChild(tr);
      });
      if (!filtered.length) { var empty = el('tr'); var td = el('td', 'ac-empty', '没有匹配的批次，请调整筛选条件。'); td.colSpan = 7; empty.appendChild(td); tbody.appendChild(empty); }
      live.textContent = '显示 ' + n(filtered.length) + ' 个批次，共 ' + n(batches.length) + ' 个 · 每页 ' + perPage + ' 个';
      pageInfo.textContent = page + ' / ' + pages + ' 页'; prev.disabled = page <= 1; next.disabled = page >= pages;
    }
    function changed() { page = 1; render(); }
    search.addEventListener('input', changed); provider.addEventListener('change', changed); status.addEventListener('change', changed);
    reset.addEventListener('click', function () { search.value = ''; provider.value = ''; status.value = ''; changed(); });
    prev.addEventListener('click', function () { page--; render(); }); next.addEventListener('click', function () { page++; render(); }); render();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
}());
