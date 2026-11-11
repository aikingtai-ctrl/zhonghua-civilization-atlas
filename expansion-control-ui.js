/* Read-only operational view. All state comes from the generated audit snapshot. */
(function () {
  'use strict';
  var conditionLabels = { explicitChina: '馆方未明确标注中国归属', publicDomain: '馆方未明确标注公共领域', officialOriginalImage: '官方原图链接条件未满足' };
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
  function collectionProgress(value) {
    var id = function (v) { return typeof v === 'string' && /^met-\d{4}-\d{2}-\d{2}-\d{3}$/.test(v); };
    var sha = function (v) { return typeof v === 'string' && /^[a-f0-9]{64}$/.test(v); };
    var count = function (v) { return Number.isSafeInteger(v) && v >= 0 && v <= 100; };
    var reasons = ['complete', 'bounded-run', 'attempt-limit', 'provider-hold', 'shared-provider-hold', 'shared-guard', 'consecutive-network-failures', 'STOP'];
    if (!value || value.schemaVersion !== 1 || !count(value.requested) || !value.requested || !count(value.attempted) || !count(value.unattempted) || value.attempted + value.unattempted !== value.requested || !reasons.includes(value.stopReason) || !sha(value.manifestSha256) || !sha(value.outcomesSha256)) return null;
    if (value.resumedFrom && (!id(value.resumedFrom.batchId) || !sha(value.resumedFrom.manifestSha256) || !sha(value.resumedFrom.outcomesSha256))) return null;
    if (value.continuedBy !== undefined) {
      if (!Array.isArray(value.continuedBy) || value.continuedBy.length > 100 || new Set(value.continuedBy.map(function (c) { return c && c.batchId; })).size !== value.continuedBy.length || !count(value.resumed) || !count(value.remainingUnstarted) || value.resumed + value.remainingUnstarted !== value.unattempted) return null;
      if (!value.continuedBy.every(function (c) { return c && id(c.batchId) && count(c.requested) && c.requested > 0 && count(c.attempted) && count(c.unattempted) && c.attempted + c.unattempted === c.requested && sha(c.manifestSha256) && sha(c.outcomesSha256); }) || value.continuedBy.reduce(function (n, c) { return n + c.attempted; }, 0) !== value.resumed) return null;
    }
    return value;
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
    var trace = data.releaseTraceability;
    if (trace && trace.latest && trace.dailyPackage) {
      var traceBox = el('section', 'ac-release-trace');
      traceBox.setAttribute('aria-label', '发布版本与每日包追溯');
      traceBox.appendChild(el('h3', '', '本次发布追溯'));
      var release = trace.latest;
      var pkg = trace.dailyPackage;
      var releaseLine = el('p', 'ac-release-line');
      releaseLine.appendChild(el('strong', '', '线上 v' + release.deploymentVersion + ' · ' + (release.status === 'succeeded' ? '部署成功' : release.status)));
      releaseLine.appendChild(el('span', '', '源提交 ' + String(release.sourceCommit || '').slice(0, 12) + '…'));
      releaseLine.appendChild(el('span', '', '更新时间 ' + date(release.updatedAt)));
      traceBox.appendChild(releaseLine);
      var packageLine = el('p', 'ac-release-line');
      packageLine.appendChild(el('strong', '', '对应每日包 ' + pkg.date + ' · ' + n(pkg.records) + ' 条'));
      packageLine.appendChild(el('span', '', '已核验 ' + n(pkg.verifiedRecords) + ' 条 · ' + n(pkg.batchCount) + ' 个批次'));
      if (typeof pkg.packageHref === 'string' && /^[a-z0-9][a-z0-9._/-]{2,160}$/.test(pkg.packageHref)) {
        var packageLink = el('a', '', '下载每日包 ↗'); packageLink.href = pkg.packageHref; packageLink.target = '_blank'; packageLink.rel = 'noopener noreferrer'; packageLine.appendChild(packageLink);
      }
      traceBox.appendChild(packageLine);
      section.appendChild(traceBox);
    }
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
    var csv = data.metCsvInventory;
    if (csv && csv.schemaVersion === 1 && csv.metadataOnly === true && csv.status === 'completed' && csv.actualImageAttempts === 0 && csv.candidates === 0 && csv.imported === 0 && csv.counts && Array.isArray(csv.coverage) && csv.coverage.length === 9 && Number.isFinite(Date.parse(csv.finishedAt || '')) && /^[a-f0-9]{64}$/.test(csv.reportSha256 || '')) {
      var csvBox = el('details', 'ac-csv-inventory');
      csvBox.appendChild(el('summary', '', 'CSV元数据预筛，不是图像入库'));
      csvBox.appendChild(el('p', 'ac-note', '已完成 · 预筛完成时间（北京时间） ' + date(csv.finishedAt) + '；以下数字均为该次预筛快照，不代表当前未尝试数量。'));
      var csvMetrics = el('div', 'ac-metrics');
      [
        ['解析元数据行', csv.counts.parsedRows, '完整固定快照解析完成'],
        ['快照公共领域 China 元数据', csv.counts.publicDomainChinaRows, 'CSV 标记 Is Public Domain=True、Culture=China'],
        ['预筛时未尝试', csv.counts.unattemptedAtDiscovery, '已排除预筛时三工作区的历史来源身份'],
        ['本次选中线索', csv.counts.selectedAtDiscovery, '仅供另行请求对象 API，不计入候选或入库']
      ].forEach(function (metric) {
        var box = el('div', 'ac-metric');
        box.appendChild(el('span', 'ac-metric-label', metric[0]));
        box.appendChild(el('strong', '', n(metric[1])));
        box.appendChild(el('small', '', metric[2])); csvMetrics.appendChild(box);
      });
      csvBox.appendChild(csvMetrics);
      csvBox.appendChild(el('p', 'ac-note', '全时期规划桶（含跨期／待细分），按快照规则预分组；不作为正式断代或覆盖统计。预筛时历史已知 ' + n(csv.counts.historyKnownAtDiscovery) + ' 条。'));
      csv.coverage.forEach(function (group) {
        csvBox.appendChild(el('p', 'ac-note', group.planningGroup + ' · 快照公共领域 China 元数据 ' + n(group.publicDomainChinaRows) + ' · 预筛时历史已知 ' + n(group.historyKnownAtDiscovery) + ' · 预筛时未尝试 ' + n(group.unattemptedAtDiscovery) + ' · 本次选中 ' + n(group.selectedAtDiscovery)));
      });
      csvBox.appendChild(el('p', 'ac-note', 'CSV 快照里的公共领域标记不证明当前图像许可、可访问性或入库资格；每张图像仍须另行核对最新官方对象 API、原图、版权和审核。'));
      csvBox.appendChild(el('small', 'ac-note', '预筛报告 SHA-256 ' + csv.reportSha256));
      queueBox.appendChild(csvBox);
    }
    var discovery = data.discoveryLeads || {};
    if (Number(discovery.count)) {
      var leadBox = el('details', 'ac-discovery-leads');
      leadBox.appendChild(el('summary', '', '官方来源线索核对 ' + n(discovery.count) + ' 条（不计入候选／正式入库）'));
      leadBox.appendChild(el('p', 'ac-note', discovery.note || '官方来源发现线索仅供后续采集复核，不计入候选或正式入库。'));
      leadBox.appendChild(el('p', 'ac-note', '已有目录 ' + n(discovery.alreadyCataloged) + ' · 已在待审队列 ' + n(discovery.pending) + ' · 已尝试未形成候选 ' + n(discovery.attemptedNoCandidate) + ' · 尚未采集 ' + n(discovery.uncollected) + ' · 来源待核 ' + n(discovery.invalid)));
      (discovery.entries || []).forEach(function (lead) {
        var row = el('p', 'ac-note');
        var leadLabels = { 'already-cataloged': '已有目录／需按需补充复核', 'pending-candidate': '已有待审候选', 'attempted-no-candidate': '已尝试未形成候选', 'uncollected': '尚未采集', 'invalid-source': '来源待核' };
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
        (lead.actualAttempts || []).forEach(function (attempt) {
          var labels = { 'eligibility-exclusion': '资格排除', 'network-failure': '网络／HTTP 失败', 'duplicate-exclusion': '重复排除', 'interrupted': '采集中断', 'source-or-local-failure': '来源／本地问题' };
          row.appendChild(el('small', 'ac-note', ' · 实际报告：' + attempt.reportFile + '；批次 ' + attempt.batchId + '；' + (labels[attempt.classification] || '原因待核') + ' · ' + attempt.code + (attempt.httpStatus ? ' · HTTP ' + attempt.httpStatus : '') + (attempt.metadataHttpStatus === 200 ? '；采集回执记录元数据 HTTP 200' : '') + '；结束时间 ' + date(attempt.finishedAt)));
        });
        leadBox.appendChild(row);
      });
      queueBox.appendChild(leadBox);
    }
    queueBox.appendChild(el('small', 'ac-note', '本页为只读快照；重试、限流和断点续采须在采集脚本执行后重新生成快照。'));
    state.appendChild(queueBox);
    var holdBox = el('div', 'ac-holds'); holdBox.appendChild(el('h3', '', '来源暂停与待复查'));
    holdBox.appendChild(el('p', 'ac-note', '以下为本构建快照记录；采集前仍须检查各工作区的当前来源限制，未记录暂停不等于来源全部可用。'));
    var holds = data.holds || [];
    if (!holds.length) holdBox.appendChild(el('p', 'ac-note', '当前快照未记录来源暂停；这不等同于各来源可用性检测通过。'));
    holds.forEach(function (hold) {
      var row = el('details', 'ac-hold');
      row.appendChild(el('summary', '', hold.provider + ' · 暂停／待复查'));
      row.appendChild(el('p', '', hold.reason));
      row.appendChild(el('small', '', '记录时间：' + date(hold.at)));
      if (hold.retryAfter) row.appendChild(el('small', '', '下次复查：' + date(hold.retryAfter)));
      holdBox.appendChild(row);
    });
    var history = data.holdHistory || [];
    if (history.length) {
      var historyBox = el('details', 'ac-hold-history');
      historyBox.appendChild(el('summary', '', '历史来源限制（' + n(history.length) + ' 条，已由后续状态取代）'));
      history.forEach(function (hold) {
        var row = el('div', 'ac-note');
        row.appendChild(el('strong', '', hold.provider + ' · 历史记录'));
        row.appendChild(el('p', '', hold.reason));
        row.appendChild(el('small', '', '原记录时间：' + date(hold.at) + '；后续状态时间：' + date(hold.currentAt)));
        historyBox.appendChild(row);
      });
      holdBox.appendChild(historyBox);
    }
    state.appendChild(holdBox); section.appendChild(state);
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
        var progress = collectionProgress(b.collectionProgress), linked = progress ? [progress.manifestSha256, progress.outcomesSha256, progress.resumedFrom && progress.resumedFrom.batchId].concat((progress.continuedBy || []).map(function (c) { return c.batchId; })) : [];
        return (!provider.value || b.provider === provider.value) && (!status.value || b.status === status.value) && (!term || [b.batchId, b.provider, b.status, lineage.originalBatchId, lineage.sourceManifestSha256, lineage.originalAcceptedSha256, lineage.run].concat(linked, b.failureReasons || [], (b.collectionExclusionReasons || []).map(function (reason) { return reason.code; }), (b.collectionEligibilityConditions || []).map(function (finding) { return Object.hasOwn(conditionLabels, finding.condition) ? finding.condition + ' ' + conditionLabels[finding.condition] : ''; })).join(' ').toLocaleLowerCase().includes(term));
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
        var progress = collectionProgress(b.collectionProgress);
        if (progress) {
          var stopLabels = { complete: '完成', 'bounded-run': '达到本轮运行时限', 'attempt-limit': '达到本轮尝试上限', 'provider-hold': '来源暂停', 'shared-provider-hold': '工作区来源限制', 'shared-guard': '工作区采集门禁停止', 'consecutive-network-failures': '连续网络失败后停止', STOP: '收到停止指令' };
          name.appendChild(el('small', 'ac-batch-source ac-collection-progress', '实际启动 ' + n(progress.attempted) + '/' + n(progress.requested) + ' 项 · 未启动 ' + n(progress.unattempted) + ' 项（不计失败） · 停止原因：' + stopLabels[progress.stopReason]));
          if (progress.resumedFrom) name.appendChild(el('small', 'ac-batch-source', '断点续采自 ' + progress.resumedFrom.batchId + '；仅承接父批未启动项'));
          (progress.continuedBy || []).forEach(function (child) { name.appendChild(el('small', 'ac-batch-source', '续批 ' + child.batchId + ' · 实际启动 ' + n(child.attempted) + '/' + n(child.requested) + ' 项')); });
          if (progress.continuedBy && progress.continuedBy.length) name.appendChild(el('small', 'ac-batch-source', '直接续批实际启动 ' + n(progress.resumed) + ' 项；父批原未启动数保留，未由这些续批启动 ' + n(progress.remainingUnstarted) + ' 项'));
        }
        if (Number(b.collectionExcluded)) {
          name.appendChild(el('small', 'ac-batch-source', '采集未形成候选 ' + n(b.collectionExcluded) + ' 次（含排重／范围／本地问题），其中重复 ' + n(b.collectionDuplicateCount) + ' 次；按采集事件计数'));
          var exclusions = el('details', 'ac-failure');
          exclusions.appendChild(el('summary', '', '展开采集排除与本地问题'));
          var exclusionList = el('ul');
          (b.collectionExclusionReasons || []).forEach(function (reason) { exclusionList.appendChild(el('li', '', reason.code + ' · ' + n(reason.count) + ' 次')); });
          if (Number(b.eligibilityEvidenceEvents)) {
            exclusionList.appendChild(el('li', '', '已取得成功的元数据响应并核对资格 ' + n(b.eligibilityEvidenceEvents) + ' 次；同次检查可能有多项条件未满足：'));
            (b.collectionEligibilityConditions || []).forEach(function (finding) {
              if (Object.hasOwn(conditionLabels, finding.condition)) exclusionList.appendChild(el('li', '', conditionLabels[finding.condition] + ' · ' + n(finding.count) + ' 次'));
            });
          }
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
