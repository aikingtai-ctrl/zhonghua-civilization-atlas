(function (root) {
  'use strict';
  const API = '/api/atlas-control';
  const LABELS = {queued:'等待执行',pending:'待处理',pending_review:'待审核',running:'执行中',leased:'执行中',paused:'已暂停',completed:'已完成',complete:'已完成',failed:'失败',retry_wait:'等待重试',retrying:'等待重试',provider_hold:'来源暂停',source_hold:'来源暂停',candidate:'待审核候选',approved:'审核通过',rejected:'审核退回',reviewed:'已审核'};
  const IMPORT_LABELS = {queued:'等待入库执行器',running:'入库执行中',accepted:'严格接收完成 · 继续入库',imported:'本地正式入库 · 待发布',failed:'入库失败'};
  const PUBLICATION_PROVIDERS = ['met','cma','aic','mia','si','wellcome'];
  const PROVIDER_LABELS = {met:'Met · 大都会',cma:'CMA · 克利夫兰',aic:'AIC · 芝加哥艺术博物馆',mia:'Mia · 明尼阿波利斯艺术博物馆',si:'Smithsonian · 史密森尼',wellcome:'Wellcome Collection'};
  const REVIEW_LABELS = {human:'人工复核',ai:'AI视觉复核',automatic:'自动检查（未逐图视觉复核）'};
  function text(value, fallback = '未注明') { return value === null || value === undefined || value === '' ? fallback : String(value); }
  function count(value) { return Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }
  function timestamp(value) { if (!value) return '—'; const date = new Date(value); return Number.isFinite(date.getTime()) ? date.toISOString().replace('T', ' ').replace(/\.000Z$/, 'Z').replace(/Z$/, ' UTC') : '时间未注明'; }
  function modePayload(mode = 'regular') {
    if (mode === 'regular') return {};
    if (mode === 'bulk') return {mode:'bulk'};
    throw new Error('请选择常规模式或批量模式。');
  }
  function parseObjectIds(value, mode = 'regular') {
    const limit = modePayload(mode).mode === 'bulk' ? 100 : 50;
    const parts = String(value).trim().split(/[\s,，、;；]+/).filter(Boolean);
    if (!parts.length || parts.length > limit) throw new Error('请输入 1–' + limit + ' 个正整数对象编号。');
    if (parts.some(part => !/^[1-9]\d*$/.test(part) || !Number.isSafeInteger(Number(part)))) throw new Error('仅接受当前来源的正整数对象 ID，不接受 URL、馆藏登记号、小数或其他文字。');
    return [...new Set(parts.map(Number))];
  }
  function creationViewId(mode, value) {
    if (mode === 'primary') return 'primary';
    const ordinal = String(value).trim();
    if (mode !== 'alternate' || !/^[1-9]\d{0,3}$/.test(ordinal) || Number(ordinal) > 1000) throw new Error('备用视图序号须为 1–1000 的整数。');
    return 'alt' + (Number(ordinal) - 1);
  }
  function viewLabel(viewId = 'primary') {
    return viewId === 'primary' ? '主图' : /^alt(?:0|[1-9]\d{0,2})$/.test(viewId) ? '备用视图 ' + (Number(viewId.slice(3)) + 1) : '视图未注明';
  }
  function publicationDate(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new Error('请选择明确的发布日期（YYYY-MM-DD）。');
    const [year,month,day] = value.split('-').map(Number);
    const days = [31,year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0) ? 29 : 28,31,30,31,30,31,31,30,31,30,31];
    if (year < 1 || month < 1 || month > 12 || day < 1 || day > days[month - 1]) throw new Error('发布日期必须是有效的日历日期。');
    return value;
  }
  function officialUrl(value, kind, provider = 'met') {
    if (typeof value !== 'string') return null;
    try {
      const url = new URL(value);
      if (url.protocol !== 'https:' || url.username || url.password || url.port || url.search || url.hash || url.href !== value) return null;
      const source = url.hostname === 'www.metmuseum.org' && /^\/art\/collection\/search\/[1-9]\d*$/.test(url.pathname);
      const image = url.hostname === 'images.metmuseum.org' && /^\/CRDImages\/[a-z0-9-]+\/original\/[^/]+$/i.test(url.pathname);
      const rights = url.hostname === 'www.metmuseum.org' && url.pathname === '/about-the-met/policies-and-documents/open-access';
      if (provider === 'cma') {
        const museum = ['clevelandart.org','www.clevelandart.org'].includes(url.hostname);
        const source = museum && /^\/art\/[a-z0-9][a-z0-9._-]*$/i.test(url.pathname);
        const image = url.hostname === 'openaccess-cdn.clevelandart.org' && /^\/[a-z0-9][a-z0-9._-]*\/[a-z0-9][a-z0-9._-]*_(?:web|print)\.(?:jpg|jpeg|png|tiff?|webp)$/i.test(url.pathname);
        const rights = museum && url.pathname === '/open-access';
        return (kind === 'image' ? image : kind === 'rights' ? rights : source) ? url.href : null;
      }
      return (kind === 'image' ? image : kind === 'rights' ? rights : source) ? url.href : null;
    } catch (_) { return null; }
  }
  function errorMessage(status, code) {
    if (status === 401) return '会话已失效，请重新登录。';
    if (status === 403) return '当前账号没有管理权限。';
    if (status === 409) return '记录状态已改变、审核版本已更新、已有入库任务，或来源暂停尚未解除。请刷新后核对。';
    if (status === 429) return '请求过于频繁，请稍后重试。';
    if (status === 503) return '管理服务暂不可用，请稍后刷新。';
    if (status === 400 || status === 422) return '提交内容未通过校验，请检查编号、审核项、备注与发布日期。';
    return code === 'NETWORK' ? '网络请求未完成，请检查连接后重试。' : '操作未完成（HTTP ' + status + '），请稍后重试。';
  }
  function isHeld(record) { return !!(record && (record.providerHold || record.sourceHold || Array.isArray(record.providerHolds) && record.providerHolds.some(hold => hold.active === true) || record.status === 'provider_hold' || record.status === 'source_hold')); }
  function holdText(hold) { return text(hold && (hold.reason || hold.message || [hold.code,hold.httpStatus && 'HTTP ' + hold.httpStatus,hold.holdUntil && '保留至 ' + timestamp(hold.holdUntil)].filter(Boolean).join(' · ')),'来源限制尚未解除；相关批次不可重试。'); }
  function createController(document, fetchFn) {
    const byId = id => document.getElementById(id);
    const state = {authorized:false,provider:'met',publicationProvider:'met',summary:null,publicationSummary:null,publicationBuildReport:null,publicationBuildReportError:'',batches:[],items:[],imports:[],publications:[],publicationDetails:new Map(),publicationEpoch:0,publicationLoading:false,busy:false,loading:false,epoch:0,batchesOffset:0,itemsOffset:0,importsOffset:0,publicationsOffset:0,importsBatchId:'',batchStatusFilter:'',itemFilters:{q:'',era:'',category:'',institution:''},importDates:new Map(),importModes:new Map(),limit:20,batchesTotal:0,itemsTotal:0,importsTotal:0,publicationsTotal:0};
    function node(tag, className, value) { const el = document.createElement(tag); if (className) el.className = className; if (value !== undefined) el.textContent = String(value); return el; }
    function showNotice(message, error) { const box = byId('notice'); box.textContent = message; box.className = 'notice' + (error ? ' error' : ''); box.hidden = !message; }
    function renderCreationView() {
      const cma = state.provider === 'cma', alternate = byId('cma-view-mode').value === 'alternate';
      byId('cma-view-fields').hidden = !cma; byId('cma-view-mode').disabled = !cma;
      byId('cma-alt-field').hidden = !alternate; byId('cma-alt-number').disabled = !cma || !alternate;
    }
    function renderCreationMode() {
      const limit = byId('batch-mode').value === 'bulk' ? 100 : 50;
      byId('create-description').textContent = state.provider === 'cma' ? '输入 1–' + limit + ' 个 CMA API 数字对象 ID（例如 98298）；馆藏登记号如 1917.974 不能用于创建任务。' : '输入 1–' + limit + ' 个大都会艺术博物馆对象编号，使用空格、逗号或换行分隔。';
    }
    function setAccess(authenticated, reason) {
      state.authorized = false; state.epoch++; state.publicationEpoch++; state.publicationLoading = false; state.summary = null; state.publicationSummary = null; state.batches = []; state.items = []; state.imports = []; state.publications = []; state.publicationDetails.clear(); state.importDates.clear(); state.importModes.clear(); state.importsBatchId = ''; state.batchesTotal = state.itemsTotal = state.importsTotal = state.publicationsTotal = 0;
      byId('workspace').hidden = true; byId('refresh').hidden = true; byId('access').hidden = false;
      byId('access-title').textContent = authenticated ? '此账号没有管理权限' : '登录后继续';
      byId('access-message').textContent = reason || (authenticated ? '仅获授权的管理员可访问采集队列与审核记录。' : '使用本站 ChatGPT 登录验证身份。登录成功后将返回此工作台。');
      byId('signin').hidden = authenticated;
      byId('batches').replaceChildren(); byId('items').replaceChildren(); byId('imports').replaceChildren(); byId('publications').replaceChildren(); byId('publications-summary').textContent = ''; byId('counts').replaceChildren(); byId('imports-batch-id').value = ''; byId('imports-filter-status').textContent = '';
      byId('publications-notice').textContent = ''; byId('publications-notice').hidden = true;
      state.publicationBuildReport = null; state.publicationBuildReportError = ''; byId('publications-held').replaceChildren();
    }
    async function api(route, options, provider = state.provider, isCurrent) {
      const epoch = state.epoch, current = isCurrent || (() => epoch === state.epoch && provider === state.provider);
      const scopedRoute = route === '/session' || provider === 'met' && !route.startsWith('/publications') ? route : route + (route.includes('?') ? '&' : '?') + 'provider=' + provider;
      let response;
      try { response = await fetchFn(API + scopedRoute, {credentials:'same-origin',redirect:'error',cache:'no-store',headers:{'Accept':'application/json',...(options ? {'Content-Type':'application/json'} : {})},...options}); }
      catch (_) { const error = new Error(errorMessage(0, 'NETWORK')); error.status = 0; throw error; }
      let data; try { data = await response.json(); } catch (_) { data = {}; }
      if (!response.ok) {
        if ((response.status === 401 || response.status === 403) && current()) setAccess(response.status === 403);
        const error = new Error(errorMessage(response.status, data.error && data.error.code)); error.status = response.status; throw error;
      }
      if (route !== '/session' && data.provider && data.provider !== provider) throw new Error('来源响应不匹配，请刷新重试。');
      return data;
    }
    function field(list, label, value) { list.append(node('dt', '', label), node('dd', '', text(value))); }
    function badge(status) { return node('span', 'badge' + (['failed','rejected'].includes(status) ? ' danger' : ['provider_hold','source_hold','paused','retry_wait'].includes(status) ? ' warning' : ''), LABELS[status] || text(status, '状态未注明')); }
    function link(container, label, value, kind) { const href = officialUrl(value, kind, state.provider); if (!href) return; const anchor = node('a', '', label + ' ↗'); anchor.href = href; anchor.target = '_blank'; anchor.rel = 'noopener noreferrer'; container.append(anchor); }
    function renderSummary(summary) {
      state.summary = summary;
      const counts = summary.counts || {};
      const specs = [['successCandidates','成功候选','采集已产生记录'],['failedRequests','失败请求','累计采集失败次数'],['pendingObjects','待采集对象','尚未完成采集'],['pending','待审核候选','等待独立审核'],['accepted','严格接收','已有接收回执'],['imported','本地正式入库','已有本地入库回执'],['pendingPublish','待发布','本地入库尚待发布核验'],['published','已核验发布','发布后核验才计数'],['batches','批次数','控制队列']];
      const aliases = {successCandidates:counts.successCandidates ?? counts.collected ?? summary.items?.total,failedRequests:counts.failedRequests,pendingObjects:counts.pendingObjects,pending:counts.pending ?? summary.items?.pending_review,accepted:counts.accepted,imported:counts.imported ?? summary.imported,pendingPublish:counts.pendingPublish,published:counts.published,batches:typeof counts.batches === 'number' ? counts.batches : summary.batches?.total};
      byId('counts').replaceChildren(...specs.map(([key,label,note]) => { const box = node('div','count'); box.append(node('strong','',count(aliases[key])),node('span','',label),node('small','',note)); return box; }));
      const runner = summary.runner || {};
      const active = runner.online === true || runner.status === 'online' || runner.status === 'running';
      const offline = runner.online === false || runner.status === 'offline';
      byId('execution-title').textContent = active ? '执行器近期有活动' : offline ? '本机执行器离线' : '执行器状态未确认';
      byId('execution-badge').textContent = active ? '有活动记录' : offline ? '离线' : '未确认';
      byId('execution-message').textContent = active ? '已收到执行器活动记录。批次的租约与进度以服务端状态为准。' : '服务端尚未确认本机执行器在线；等待操作员运行后才会开始采集。';
      if (runner.lastSeenAt) byId('execution-message').textContent += ' 最近活动：' + timestamp(runner.lastSeenAt) + '。';
      const hold = summary.providerHolds?.find(hold => hold.active === true) || summary.providerHold || summary.sourceHold;
      byId('hold-message').hidden = !hold;
      byId('hold-message').textContent = hold ? '来源暂停：' + holdText(hold) : '';
      byId('updated-at').textContent = '最近刷新 ' + timestamp(new Date().toISOString());
    }
    function action(label, handler, disabled) { const button = node('button','secondary',label); button.type = 'button'; button.disabled = !!disabled || state.busy; button.addEventListener('click',handler); return button; }
    async function filterImports(batchId) {
      if (state.busy || state.loading || !state.authorized) return;
      state.importsBatchId = batchId; state.importsOffset = 0; byId('imports-batch-id').value = batchId; await refresh();
    }
    async function applyBatchFilter(status) { if (state.busy || state.loading || !state.authorized) return; state.batchStatusFilter = status; state.batchesOffset = 0; await refresh(); }
    async function applyItemFilter(filters) { if (state.busy || state.loading || !state.authorized) return; state.itemFilters = {...filters}; state.itemsOffset = 0; await refresh(); }
    function importForm(batch) {
      const form = node('form','import-form'), label = node('label','','发布日期'), input = node('input');
      input.type = 'date'; input.name = 'publicationDate'; input.required = true; input.min = '0001-01-01'; input.max = '9999-12-31'; input.value = state.importDates.get(batch.id) || ''; label.append(input); form.append(label);
      input.addEventListener('input',() => state.importDates.set(batch.id,input.value));
      const modeLabel = node('label','','入库模式'), mode = node('select'); mode.name = 'mode'; mode.disabled = state.busy;
      for (const [value,title] of [['regular','常规 · 最多 50 条'],['bulk','批量 · 最多 100 条']]) { const option = node('option','',title); option.value = value; mode.append(option); }
      mode.value = state.importModes.get(batch.id) || 'regular'; modeLabel.append(mode); form.append(modeLabel);
      mode.addEventListener('change',() => state.importModes.set(batch.id,mode.value));
      const revisionValid = Number.isSafeInteger(batch.revision) && batch.revision >= 0;
      const pendingReview = (batch.counts || batch).pending;
      const awaitingReview = Number.isSafeInteger(pendingReview) && pendingReview > 0;
      const explanation = node('p','help','申请将冻结当前已通过候选与审核版本 ' + text(batch.revision,'未提供') + '。发布日期用于本地入库材料；申请不会自动发布。');
      const error = node('p','field-error'); error.hidden = true; error.setAttribute('role','alert');
      const submit = node('button','primary','申请正式入库'); submit.type = 'submit'; submit.disabled = state.busy || !revisionValid || awaitingReview;
      if (awaitingReview) { error.textContent = '尚有 ' + pendingReview + ' 条候选待审核；完成全部候选的通过或退回后，才能申请正式入库。'; error.hidden = false; }
      else if (!revisionValid) { error.textContent = '缺少有效审核版本，请刷新后再申请。'; error.hidden = false; }
      form.append(explanation,error,submit);
      form.addEventListener('submit',async event => {
        event.preventDefault(); if (state.busy || state.loading || !revisionValid || awaitingReview) return;
        state.importDates.set(batch.id,input.value);
        let date, selectedMode; try { date = publicationDate(input.value); selectedMode = modePayload(mode.value); const limit = selectedMode.mode === 'bulk' ? 100 : 50; if ((batch.counts || batch).approved > limit) throw new Error('当前审核通过数量超过 ' + limit + ' 条；请明确选择批量模式，单次仍最多 100 条。'); error.hidden = true; } catch (failure) { error.textContent = failure.message; error.hidden = false; input.focus(); return; }
        state.importModes.set(batch.id,mode.value);
        await mutate('/batches/' + encodeURIComponent(batch.id) + '/import',{expectedRevision:batch.revision,publicationDate:date,...selectedMode},'正式入库申请已加入队列，等待本机入库执行器。审核清单已冻结；本地入库与发布仍以各阶段回执和核验为准。');
      });
      return form;
    }
    function renderBatches(result) {
      state.batches = Array.isArray(result.items) ? result.items : []; state.batchesTotal = Number.isSafeInteger(result.total) ? result.total : state.batches.length;
      byId('batches-total').textContent = count(state.batchesTotal) + ' 个批次';
      const cards = state.batches.map(batch => {
        const card = node('article','batch-card'), head = node('div','batch-head'); head.append(node('span','batch-id',text(batch.id)),badge(batch.status)); card.append(head);
        const meta = node('dl','batch-meta');
        const details = [['游标',count(batch.cursor) + ' / ' + count(batch.objectIds && batch.objectIds.length)],['租约截止',timestamp(batch.leaseUntil || batch.leaseExpiresAt)],['下次重试',timestamp(batch.nextAttemptAt || batch.nextRetryAt)],['创建时间',timestamp(batch.createdAt)]];
        details.unshift(['采集模式',batch.mode === 'bulk' ? '批量 · 最多 100 个对象' : '常规 · 最多 50 个对象']);
        if (state.provider === 'cma') details.unshift(['所选视图',viewLabel(batch.viewId)]);
        const c = batch.counts || batch; details.push(['成功候选',count(c.collected ?? c.successCandidates)],['失败请求',count(c.failedRequests)],['待审核',count(c.pending)],['审核通过',count(c.approved)],['本地正式入库',count(c.imported)]);
        for (const [label,value] of details) { const group = node('div'); field(group,label,value); meta.append(group); } card.append(meta);
        const held = isHeld(batch) || isHeld(state.summary);
        const error = batch.error || batch.lastError;
        if (held) card.append(node('p','batch-hold','来源暂停：' + holdText(error || state.summary?.providerHolds?.find(hold => hold.active === true) || batch.providerHold || batch.sourceHold)));
        else if (error) card.append(node('p','batch-hold','最近错误：' + text(error.message || error.code)));
        const actions = node('div','actions');
        actions.append(action('暂停批次',() => mutate('/batches/' + encodeURIComponent(batch.id) + '/pause',{}),!['queued','pending','running','leased','retry_wait','retrying'].includes(batch.status)),action('重试批次',() => mutate('/batches/' + encodeURIComponent(batch.id) + '/retry',{}),held || !['failed','paused','retry_wait','retrying'].includes(batch.status)));
        const existingImport = batch.importJobId || batch.importId || state.imports.find(job => job.batchId === batch.id)?.id;
        if (existingImport) {
          actions.append(action('查看入库任务',() => filterImports(batch.id)));
          card.append(node('p','help','已有正式入库任务：' + text(existingImport) + '。请在任务中查看回执或重试失败任务。'));
        }
        card.append(actions);
        if (batch.status === 'completed' && Number.isSafeInteger(c.approved) && c.approved > 0 && !existingImport) card.append(importForm(batch));
        return card;
      });
      byId('batches').replaceChildren(...(cards.length ? cards : [node('p','empty','尚无采集批次。创建批次后，队列会显示在这里。')])); pagination('batches');
    }
    function renderImports(result) {
      state.imports = Array.isArray(result.items) ? result.items : []; state.importsTotal = Number.isSafeInteger(result.total) ? result.total : state.imports.length;
      byId('imports-total').textContent = count(state.importsTotal) + ' 个入库任务';
      byId('imports-filter-status').textContent = state.importsBatchId ? '当前采集批次：' + state.importsBatchId : '当前显示全部入库任务。';
      byId('imports-clear-filter').disabled = state.busy || !state.importsBatchId;
      const cards = state.imports.map(job => {
        const card = node('article','import-card'), head = node('div','batch-head'), status = badge(job.status);
        const meta = node('dl','batch-meta'), c = job.counts || {};
        const publication = job.publicationReceipt, verifiedAt = job.latestVerifiedAt || job.lastVerifiedAt || publication?.verifiedAt;
        const verified = !!publication && Number.isSafeInteger(c.published) && c.published > 0 && !!verifiedAt;
        status.textContent = verified ? '发布已核验 · 见版本与时间' : IMPORT_LABELS[job.status] || text(job.status,'状态未注明'); head.append(node('span','batch-id',text(job.id)),status); card.append(head);
        const pendingPublish = Number.isSafeInteger(c.imported) && c.imported >= 0 && Number.isSafeInteger(c.published) && c.published >= 0 && c.published <= c.imported ? c.imported - c.published : undefined;
        for (const [label,value] of [['入库模式',job.mode === 'bulk' ? '批量 · 最多 100 条' : '常规 · 最多 50 条'],['采集批次',job.batchId],['本地批次',job.localBatchId],['发布日期',job.publicationDate],['审核通过（冻结）',count(c.approved)],['严格接收',count(c.accepted)],['本地正式入库',count(c.imported)],['待发布',count(pendingPublish)],['已核验发布',count(c.published)],['租约截止',timestamp(job.leaseUntil)],['创建时间',timestamp(job.createdAt)]]) { const group = node('div'); field(group,label,value); meta.append(group); }
        card.append(meta);
        const manifest = node('div','hash'); manifest.append(node('b','','FROZEN MANIFEST SHA-256'),node('span','',text(job.manifestSha256,'尚未提供清单指纹'))); card.append(manifest);
        const received = verified ? '已保存发布核验回执；截至 ' + timestamp(verifiedAt) + '，对应部署版本 ' + text(publication.nativeReceipt?.versionNumber) + '。后续版本须重新核验。' : job.importedReceipt ? '已保存本地入库回执；仍待构建和发布核验。' : job.stage === 'imported' ? '本地入库阶段已完成；仍待构建和发布核验。' : job.acceptedReceipt || job.stage === 'accepted' ? '已保存严格接收回执；等待本地正式入库。' : '尚未确认严格接收或本地入库回执；等待本机入库执行器。';
        card.append(node('p','receipt-note',received));
        if (job.error) card.append(node('p','batch-hold','最近错误：' + text(typeof job.error === 'string' ? job.error : job.error.message || job.error.code)));
        if (job.status === 'failed') { const actions = node('div','actions'); actions.append(action('重试入库任务',() => mutate('/imports/' + encodeURIComponent(job.id) + '/retry',{},'入库任务已重新排队。执行器将核对已保存回执后继续；尚未发布。'))); card.append(actions); }
        return card;
      });
      byId('imports').replaceChildren(...(cards.length ? cards : [node('p','empty',state.importsBatchId ? '此批次暂无正式入库任务。' : '暂无正式入库任务。审核通过后，在已完成的采集批次中申请。')])); pagination('imports');
    }
    function renderPublications(result) {
      state.publications = Array.isArray(result.items) ? result.items : []; state.publicationsTotal = Number.isSafeInteger(result.total) ? result.total : state.publications.length;
      byId('publications-total').textContent = count(state.publicationsTotal) + ' 份核验回执';
      const cards = state.publications.map(publication => {
        const card = node('article','import-card'), head = node('div','batch-head');
        head.append(node('span','batch-id',text(publication.localBatchId)),node('span','badge',publication.importId ? '控制任务入库' : '原有扩库流程')); card.append(head);
        const meta = node('dl','batch-meta'), native = publication.nativeReceipt || {};
        for (const [label,value] of [['来源',PROVIDER_LABELS[publication.provider] || '未注明'],['发布日期',publication.publicationDate],['该批次核验记录',count(publication.recordsCount)],['控制入库任务',publication.importId || '无；原有扩库独立登记'],['核验时间',timestamp(publication.verifiedAt)],['原生部署版本',native.versionNumber],['版本 ID',native.versionId],['部署 ID',native.deploymentId],['来源提交',native.sourceCommit],['线上来源',publication.liveOrigin],['发布证明 SHA-256',publication.proofSha256],['索引 SHA-256',publication.indexSha256],['接收批次 SHA-256',publication.acceptedBatchSha256]]) { const group = node('div'); field(group,label,value); meta.append(group); }
        card.append(meta,node('p','receipt-note','本回执仅证明上述版本在该核验时间的目录、日包元数据及图像指纹与当次部署一致；不等于本轮逐一重新检测全部远程原图链接或重新进行逐图视觉复核。'));
        const reviews = publication.reviewCounts;
        card.append(node('p','help',reviews ? '发布时记录的审核类型：人工 ' + count(reviews.human) + ' · AI视觉 ' + count(reviews.ai) + ' · 自动检查 ' + count(reviews.automatic) + '。自动检查不代表逐图视觉复核。' : '此回执尚未提供审核类型分布。'));
        const key = state.publicationProvider + ':' + publication.id, detail = state.publicationDetails.get(key);
        const button = node('button','secondary',detail?.loading ? '正在读取历史凭据…' : detail?.error ? '重试历史凭据' : detail?.expanded ? '收起历史凭据' : '查看历史核验凭据'); button.type = 'button'; button.disabled = state.publicationLoading || detail?.loading === true; button.setAttribute('aria-expanded',detail?.expanded ? 'true' : 'false');
        button.addEventListener('click',() => publicationDetail(publication)); card.append(button);
        if (detail?.expanded) {
          const box = node('section','publication-evidence');
          if (detail.error) box.append(node('p','notice error',detail.error));
          else if (detail.result) {
            const proof = detail.result.proof, hashes = node('dl','batch-meta'); box.append(node('h3','','该回执保存的历史证明'));
            for (const [label,value] of [['证明生成时间',timestamp(proof.builtAt)],['接收批次 SHA-256',proof.acceptedBatchSha256],['来源日包 SHA-256',proof.sourceDayPackageSha256],['交付日包 SHA-256',proof.servedDayPackageSha256],['目录 SHA-256',proof.catalogSha256]]) { const group = node('div'); field(group,label,value); hashes.append(group); } box.append(hashes);
            const records = Array.isArray(proof.records) ? proof.records : [], list = node('div','publication-proof-records'); list.tabIndex = 0; list.setAttribute('aria-label','历史证明逐项审核类型与证据哈希');
            for (const record of records.slice(0,20)) { const row = node('dl','proof-record'); for (const [label,value] of [['记录',record.id],['审核类型',REVIEW_LABELS[record.reviewerType] || '未注明'],['图像 SHA-256',record.imageSha256],['来源记录 SHA-256',record.sourceRecordSha256],['正式记录 SHA-256',record.recordSha256]]) field(row,label,value); list.append(row); }
            box.append(node('p','help','显示历史证明前 ' + Math.min(records.length,20) + ' 条，共 ' + records.length + ' 条。审核类型沿用发布时已记录的类型，此处未重新进行逐图视觉复核。'),list);
          } else box.append(node('p','help','正在读取该部署版本保存的核验凭据。'));
          card.append(box);
        }
        return card;
      });
      byId('publications').replaceChildren(...(cards.length ? cards : [node('p','empty','当前来源暂无已核验发布回执；本地入库不等于发布核验。')])); pagination('publications');
    }
    async function publicationDetail(publication) {
      if (!state.authorized || state.publicationLoading) return;
      const provider = state.publicationProvider, epoch = state.publicationEpoch, key = provider + ':' + publication.id, prior = state.publicationDetails.get(key);
      if (prior?.loading) return;
      if (prior?.expanded && !prior.error) { state.publicationDetails.set(key,{...prior,expanded:false}); renderPublications({items:state.publications,total:state.publicationsTotal}); return; }
      if (prior?.result) { state.publicationDetails.set(key,{...prior,expanded:true}); renderPublications({items:state.publications,total:state.publicationsTotal}); return; }
      state.publicationDetails.set(key,{expanded:true,loading:true}); renderPublications({items:state.publications,total:state.publicationsTotal});
      try {
        const result = await api('/publications/' + encodeURIComponent(publication.id),undefined,provider,() => state.authorized && epoch === state.publicationEpoch && provider === state.publicationProvider);
        if (!state.authorized || epoch !== state.publicationEpoch || provider !== state.publicationProvider) return;
        if (result.publication?.id !== publication.id || result.publication.provider !== provider || result.proof?.provider !== provider || result.proof.localBatchId !== publication.localBatchId) throw new Error('历史核验凭据与当前回执不匹配。');
        state.publicationDetails.set(key,{expanded:true,loading:false,result});
      } catch (error) { if (state.authorized && epoch === state.publicationEpoch && provider === state.publicationProvider) state.publicationDetails.set(key,{expanded:true,loading:false,error:error.message}); }
      if (state.authorized && epoch === state.publicationEpoch && provider === state.publicationProvider) renderPublications({items:state.publications,total:state.publicationsTotal});
    }
    async function publicationBuildReport() {
      let response; try { response = await fetchFn('/publication-proofs/build-report.json',{method:'GET',credentials:'same-origin',redirect:'error',cache:'no-store',headers:{Accept:'application/json'}}); } catch (_) { throw new Error('当前构建来源待考报告暂未读取，待考数未确认。'); }
      if (!response.ok) throw new Error('当前构建来源待考报告暂未读取，待考数未确认。');
      let report; try { report = await response.json(); } catch (_) { throw new Error('当前构建来源待考报告无法解析，待考数未确认。'); }
      if (!Array.isArray(report.unverifiedRecords) || report.unverifiedRecords.some(row => !row || typeof row.id !== 'string' || !PUBLICATION_PROVIDERS.includes(row.provider) || !Array.isArray(row.issues)) || !Number.isSafeInteger(report.proofs) || report.proofs < 0 || !Number.isSafeInteger(report.records) || report.records < 0 || !Array.isArray(report.entries) || report.entries.some(entry => !entry || !PUBLICATION_PROVIDERS.includes(entry.provider) || !Number.isSafeInteger(entry.recordCount) || entry.recordCount < 0) || report.entries.length !== report.proofs || report.entries.reduce((sum,entry) => sum + entry.recordCount,0) !== report.records) throw new Error('当前构建未提供有效的覆盖与逐项来源待考报告，覆盖数和待考数未确认。');
      return report;
    }
    function renderPublicationHeld() {
      const box = byId('publications-held'), report = state.publicationBuildReport;
      if (!report) { box.replaceChildren(node('p','help',state.publicationBuildReportError || '尚未读取当前构建的来源待考报告。')); return; }
      const held = report.unverifiedRecords, selected = held.filter(row => row.provider === state.publicationProvider), selectedProofs = report.entries.filter(entry => entry.provider === state.publicationProvider);
      box.replaceChildren(node('h3','','当前构建的证明覆盖与来源待考'),node('p','help','当前构建：' + count(report.proofs) + ' 份证明 · 覆盖 ' + count(report.records) + ' 条 · 来源待考 ' + held.length + ' 条。当前筛选：' + selectedProofs.length + ' 份证明 · 覆盖 ' + count(selectedProofs.reduce((sum,entry) => sum + entry.recordCount,0)) + ' 条 · 来源待考 ' + selected.length + ' 条。报告时间 ' + timestamp(report.builtAt || report.generatedAt) + '。构建证明尚须与原生部署及线上资产核验后登记回执；已入库、当前构建覆盖和历史核验分别统计。当前构建未为下列待考项出具发布证明；历史已核验记录仍保留原版本回执，不据此自动减数。'));
      for (const row of held.slice(0,20)) { const reasons = Array.isArray(row.issues) ? row.issues.map(issue => typeof issue === 'string' ? issue : text(issue?.message || issue?.code,'原因待核')).join('；') : '待考原因未注明'; box.append(node('p','source-held-record',(PROVIDER_LABELS[row.provider] || '来源未注明') + ' · ' + text(row.id) + ' · ' + reasons)); }
      if (held.length > 20) box.append(node('p','help','此处显示前20条来源待考记录。'));
    }
    async function refreshPublications() {
      if (!state.authorized || state.publicationLoading) return;
      const epoch = state.publicationEpoch, provider = state.publicationProvider; state.publicationLoading = true; byId('publications-refresh').disabled = true; pagination('publications');
      try {
        const current = () => state.authorized && epoch === state.publicationEpoch && provider === state.publicationProvider;
        const [summaryRead,listRead,buildRead] = await Promise.allSettled([api('/publications/summary',undefined,provider,current),api('/publications?limit=' + state.limit + '&offset=' + state.publicationsOffset,undefined,provider,current),publicationBuildReport()]);
        if (!state.authorized || epoch !== state.publicationEpoch || provider !== state.publicationProvider) return;
        state.publicationBuildReport = buildRead.status === 'fulfilled' ? buildRead.value : null; state.publicationBuildReportError = buildRead.status === 'rejected' ? buildRead.reason.message : ''; renderPublicationHeld();
        if (summaryRead.status === 'rejected') throw summaryRead.reason; if (listRead.status === 'rejected') throw listRead.reason;
        const summary = summaryRead.value, result = listRead.value;
        if (!Array.isArray(summary.scope) || summary.scope.length !== 1 || summary.scope[0] !== provider) throw new Error('发布统计来源不匹配，请刷新重试。');
        state.publicationSummary = summary;
        byId('publications-summary').textContent = PROVIDER_LABELS[provider] + ' · 历史已核验唯一记录 ' + count(summary.verifiedRecords) + ' · 原有扩库 ' + count(summary.directVerifiedRecords) + ' · 控制任务 ' + count(summary.controlVerifiedRecords) + ' · 最近核验 ' + timestamp(summary.latestVerifiedAt) + '。按历史已保存回执及对应版本累计，不代表当前部署覆盖；同一记录跨版本只计一次。';
        byId('publications-notice').hidden = true; byId('publications-notice').textContent = ''; renderPublications(result);
      } catch (error) { if (state.authorized && epoch === state.publicationEpoch && provider === state.publicationProvider) { byId('publications-notice').textContent = error.message; byId('publications-notice').className = 'notice error'; byId('publications-notice').hidden = false; } }
      finally { if (epoch === state.publicationEpoch && provider === state.publicationProvider) { state.publicationLoading = false; byId('publications-refresh').disabled = false; if (state.authorized) renderPublications({items:state.publications,total:state.publicationsTotal}); } }
    }
    async function selectPublicationProvider(provider) {
      if (!PUBLICATION_PROVIDERS.includes(provider) || provider === state.publicationProvider) return;
      state.publicationProvider = provider; state.publicationEpoch++; state.publicationLoading = false; state.publicationSummary = null; state.publicationBuildReport = null; state.publicationBuildReportError = ''; state.publications = []; state.publicationsTotal = 0; state.publicationsOffset = 0; state.publicationDetails.clear(); renderPublicationHeld();
      byId('publication-provider-select').value = provider; byId('publications').replaceChildren(); byId('publications-total').textContent = ''; byId('publications-page').textContent = '0 / 0'; byId('publications-summary').textContent = '尚未读取当前来源的发布核验记录。'; byId('publications-notice').textContent = ''; byId('publications-notice').hidden = true;
      await refreshPublications();
    }
    function reviewForm(item) {
      const form = node('form','review-form'), fieldset = node('fieldset'); fieldset.append(node('legend','','独立审核 · 四项核对'));
      const checks = {};
      for (const [key,label] of [['source','官方对象与原图来源一致'],['rights','开放权利与使用条件已核实'],['metadata','题名、年代、时期与待考字段已核对'],['visual','图像内容与官方对象相符']]) { const row = node('label','check-label'), input = node('input'); input.type = 'checkbox'; input.name = key; checks[key] = input; row.append(input,node('span','',label)); fieldset.append(row); }
      form.append(fieldset); const fields = node('div','review-fields');
      const who = node('div'), whoLabel = node('label','','审核者类型'), whoSelect = node('select'); whoSelect.name = 'reviewerType'; whoLabel.append(whoSelect); for (const [value,label] of [['human','人工审核'],['ai','AI 审核']]) { const option = node('option','',label); option.value = value; whoSelect.append(option); } whoSelect.value = 'human'; who.append(whoLabel); fields.append(who); form.append(fields);
      const noteLabel = node('label','','审核依据与备注（必填）'), noteInput = node('textarea'); noteInput.name = 'note'; noteInput.rows = 3; noteInput.required = true; noteInput.maxLength = 2000; noteInput.placeholder = '说明核对依据、发现的问题及仍待考的信息；AI 审核请写明方法。'; noteLabel.append(noteInput); form.append(noteLabel,node('p','help','通过需确认全部四项。AI 审核须写明方法。此操作只保存审核决定，正式入库计数不会因此增加。'));
      const error = node('p','field-error'); error.hidden = true; error.setAttribute('role','alert'); form.append(error);
      const actions = node('div','actions'), approve = node('button','primary','保存通过意见'), reject = node('button','secondary','退回候选'); approve.type = reject.type = 'submit'; approve.name = reject.name = 'decision'; approve.value = 'approve'; reject.value = 'reject'; actions.append(approve,reject); form.append(actions);
      const validHash = /^[a-f0-9]{64}$/i.test(item.imageSha256 || '');
      approve.disabled = reject.disabled = state.busy || !validHash;
      if (!validHash) { error.textContent = '缺少有效的图像 SHA-256，无法绑定审核意见。'; error.hidden = false; }
      form.addEventListener('submit',async event => {
        event.preventDefault(); if (state.busy || state.loading) return;
        const decision = event.submitter && event.submitter.value;
        const values = Object.fromEntries(Object.entries(checks).map(([key,input]) => [key,input.checked]));
        if (!['approve','reject'].includes(decision)) { error.textContent = '请选择通过或退回。'; error.hidden = false; return; }
        if (!noteInput.value.trim() || (decision === 'approve' && Object.values(values).some(value => !value))) { error.textContent = !noteInput.value.trim() ? '请填写审核依据与备注。' : '通过前请完成全部四项核对。'; error.hidden = false; return; }
        error.hidden = true;
        await mutate('/items/' + encodeURIComponent(item.id) + '/review',{decision,reviewerType:whoSelect.value,imageSha256:item.imageSha256,checks:values,note:noteInput.value.trim()},'审核决定已保存；尚未执行严格接收、正式入库或发布。');
      }); return form;
    }
    function renderItems(result) {
      state.items = Array.isArray(result.items) ? result.items : []; state.itemsTotal = Number.isSafeInteger(result.total) ? result.total : state.items.length;
      byId('items-total').textContent = count(state.itemsTotal) + ' 条候选';
      const cards = state.items.map(item => {
        const card = node('article','candidate-card'), photo = node('div','candidate-photo'), imageUrl = officialUrl(item.originalImageUrl || item.imageUrl,'image',state.provider);
        if (imageUrl) { const image = node('img'); image.src = imageUrl; image.alt = text(item.title,'官方候选图像'); image.loading = 'lazy'; image.referrerPolicy = 'no-referrer'; image.addEventListener('error',() => photo.replaceChildren(node('span','muted','原图预览暂不可用，请通过官方原图链接核验。')),{once:true}); photo.append(image); } else photo.append(node('span','muted','缺少可验证的官方原图地址。'));
        const body = node('div','candidate-body'); body.append(badge(item.status),node('h3','',text(item.title,'题名待考'))); const meta = node('dl','candidate-meta');
        field(meta,'对象编号',item.objectId ?? item.sourceRecordId); field(meta,'原始年代',item.originalDateText || item.date); field(meta,'原始时期',item.originalPeriod); field(meta,'图谱时期',item.era); field(meta,'权利',item.rights); field(meta,'权利状态',item.rightsStatus); field(meta,'材质 / 尺寸',[item.material,item.dimensions].filter(Boolean).join(' / ')); field(meta,'待考字段',Array.isArray(item.unknownFields) && item.unknownFields.length ? item.unknownFields.join('、') : '未列明；不等于全部已核实'); body.append(meta);
        if (state.provider === 'cma') field(meta,'所选视图',viewLabel(item.viewId));
        const links = node('div','candidate-links'); link(links,'官方对象页',item.sourceUrl); link(links,'官方精确原图',item.originalImageUrl || item.imageUrl,'image'); link(links,'官方开放权利',item.rightsUrl,'rights'); body.append(links);
        if (state.provider === 'cma') body.append(node('p','help','CMA 官方图像版本：' + (item.acquisitionImageRendition === 'print' ? 'print' : 'web') + '。审核绑定实际下载文件的 SHA-256；CC0 使用条件以官方记录及开放访问条款为准。'));
        const hash = node('div','hash'); hash.append(node('b','','IMAGE SHA-256'),node('span','',text(item.imageSha256,'缺失，无法提交审核'))); body.append(hash);
        const review = item.review || item.latestReview;
        if (review) { const history = node('div','review-history'); history.append(node('p','','最近审核：' + text(review.decision) + ' · ' + text(review.reviewerType) + ' · ' + timestamp(review.createdAt || review.reviewedAt)),node('p','',text(review.note))); body.append(history); }
        body.append(reviewForm(item)); card.append(photo,body); return card;
      });
      byId('items').replaceChildren(...(cards.length ? cards : [node('p','empty','暂无候选。执行器成功采集后，记录会出现在这里。')])); pagination('items');
    }
    function pagination(kind) { const offset = state[kind + 'Offset'], total = state[kind + 'Total'], blocked = kind === 'publications' ? state.publicationLoading : state.busy; byId(kind + '-prev').disabled = blocked || offset === 0; byId(kind + '-next').disabled = blocked || offset + state.limit >= total; byId(kind + '-page').textContent = total ? (offset + 1) + '–' + Math.min(offset + state.limit,total) + ' / ' + total : '0 / 0'; }
    function busy(value) { state.busy = value; byId('refresh').disabled = value; byId('create-batch').disabled = value; for (const button of byId('workspace').querySelectorAll('button')) if (value) button.disabled = true; if (!value && state.authorized) { byId('publications-refresh').disabled = state.publicationLoading; renderPublications({items:state.publications,total:state.publicationsTotal}); renderImports({items:state.imports,total:state.importsTotal}); renderBatches({items:state.batches,total:state.batchesTotal}); renderItems({items:state.items,total:state.itemsTotal}); } }
    async function refresh() {
      const publicationRefresh = refreshPublications();
      if (!state.authorized || state.loading) { await publicationRefresh; return; } state.loading = true; const epoch = state.epoch;
      byId('refresh').disabled = true; byId('workspace').setAttribute('aria-busy','true'); for (const button of byId('workspace').querySelectorAll('button')) button.disabled = true;
      try {
        const batchFilters = state.batchStatusFilter ? '&status=' + encodeURIComponent(state.batchStatusFilter) : '';
        const itemFilters = Object.entries(state.itemFilters).filter(([,value]) => value).map(([key,value]) => '&' + key + '=' + encodeURIComponent(value)).join('');
        const results = await Promise.all([api('/summary'),api('/batches?limit=' + state.limit + '&offset=' + state.batchesOffset + batchFilters),api('/items?limit=' + state.limit + '&offset=' + state.itemsOffset + itemFilters),api('/imports?limit=' + state.limit + '&offset=' + state.importsOffset + (state.importsBatchId ? '&batchId=' + encodeURIComponent(state.importsBatchId) : ''))]);
        if (!state.authorized || epoch !== state.epoch) return; renderSummary(results[0]); renderImports(results[3]); renderBatches(results[1]); renderItems(results[2]);
      } catch (error) { if (epoch === state.epoch) { const prior = byId('notice').textContent; showNotice((prior ? prior + ' 状态刷新未完成：' : '') + error.message,true); } }
      finally { if (epoch === state.epoch) { state.loading = false; byId('workspace').setAttribute('aria-busy','false'); byId('refresh').disabled = state.busy; byId('create-batch').disabled = state.busy; if (state.authorized) { renderPublications({items:state.publications,total:state.publicationsTotal}); renderImports({items:state.imports,total:state.importsTotal}); renderBatches({items:state.batches,total:state.batchesTotal}); renderItems({items:state.items,total:state.itemsTotal}); } } }
      await publicationRefresh;
    }
    async function mutate(route, body, success) {
      if (state.busy || state.loading || !state.authorized) return; const epoch = state.epoch; busy(true); showNotice('',false);
      try { await api(route,{method:'POST',body:JSON.stringify(body)}); if (epoch !== state.epoch) return; showNotice(success || '操作已保存；队列状态以刷新结果为准。',false); await refresh(); }
      catch (error) { if (epoch === state.epoch) { showNotice(error.message,true); if (error.status === 409 && state.authorized) await refresh(); } }
      finally { if (epoch === state.epoch) busy(false); }
    }
    async function selectProvider(provider) {
      if (!['met','cma'].includes(provider) || provider === state.provider) return;
      state.provider = provider; state.epoch++; state.loading = false; state.busy = false; state.summary = null; state.batches = []; state.items = []; state.imports = []; state.importDates.clear(); state.importModes.clear(); state.importsBatchId = ''; state.batchStatusFilter = ''; state.itemFilters = {q:'',era:'',category:'',institution:''}; state.batchesOffset = state.itemsOffset = state.importsOffset = 0; state.batchesTotal = state.itemsTotal = state.importsTotal = 0;
      byId('provider-select').value = provider; byId('provider-title').textContent = '当前来源：' + (provider === 'cma' ? 'CMA 克利夫兰艺术博物馆' : 'Met 大都会艺术博物馆');
      byId('overview-title').textContent = (provider === 'cma' ? 'CMA' : 'Met') + ' 来源队列概览';
      byId('create-title').textContent = '从 ' + (provider === 'cma' ? 'CMA' : 'Met') + ' 官方对象开始';
      byId('batch-mode').value = 'regular'; renderCreationMode();
      byId('ids-help').textContent = provider === 'cma' ? '仅接受 CMA API 正整数 ID；重复编号会合并。需官方中国藏品与 CC0 图像；登记号和 URL 不可提交。' : '仅接受正整数编号；重复编号会合并。URL 不可提交。';
      byId('object-ids').value = ''; byId('object-ids').placeholder = provider === 'cma' ? '例如：98298' : '例如：39666, 39901'; byId('ids-error').hidden = true; byId('imports-batch-id').value = ''; byId('imports-filter-status').textContent = ''; byId('hold-message').hidden = true; byId('updated-at').textContent = '尚未刷新';
      byId('cma-view-mode').value = 'primary'; byId('cma-alt-number').value = '1'; renderCreationView();
      for (const kind of ['counts','batches','items','imports']) byId(kind).replaceChildren();
      for (const kind of ['batches','items','imports']) { byId(kind + '-total').textContent = ''; byId(kind + '-page').textContent = '0 / 0'; }
      byId('execution-title').textContent = '等待当前来源状态'; byId('execution-badge').textContent = '待核验'; byId('execution-message').textContent = '正在读取当前来源的执行记录。'; showNotice('',false);
      await refresh();
    }
    async function start() {
      byId('refresh').addEventListener('click',refresh);
      byId('provider-select').value = state.provider; byId('provider-select').addEventListener('change',() => selectProvider(byId('provider-select').value));
      byId('publication-provider-select').value = state.publicationProvider; byId('publication-provider-select').addEventListener('change',() => selectPublicationProvider(byId('publication-provider-select').value)); byId('publications-refresh').addEventListener('click',refreshPublications);
      byId('cma-view-mode').value = 'primary'; byId('cma-alt-number').value = '1'; byId('cma-view-mode').addEventListener('change',renderCreationView); renderCreationView();
      byId('batch-mode').value = 'regular'; byId('batch-mode').addEventListener('change',renderCreationMode); renderCreationMode();
      byId('batch-form').addEventListener('submit',async event => { event.preventDefault(); if (state.busy || state.loading) return; let value; try { const objectIds = parseObjectIds(byId('object-ids').value,byId('batch-mode').value); value = {objectIds,...modePayload(byId('batch-mode').value),...(state.provider === 'cma' ? {viewId:creationViewId(byId('cma-view-mode').value,byId('cma-alt-number').value)} : {})}; byId('ids-error').hidden = true; } catch (error) { byId('ids-error').textContent = error.message; byId('ids-error').hidden = false; byId('object-ids').focus(); return; } await mutate('/batches',value,'批次已加入队列，等待本机执行器采集。'); });
      for (const kind of ['batches','items','imports']) for (const direction of ['prev','next']) byId(kind + '-' + direction).addEventListener('click',async () => { if (state.busy || state.loading) return; state[kind + 'Offset'] = Math.max(0,state[kind + 'Offset'] + (direction === 'next' ? state.limit : -state.limit)); await refresh(); });
      for (const direction of ['prev','next']) byId('publications-' + direction).addEventListener('click',async () => { if (state.publicationLoading || !state.authorized) return; state.publicationsOffset = Math.max(0,state.publicationsOffset + (direction === 'next' ? state.limit : -state.limit)); await refreshPublications(); });
      byId('imports-filter-form').addEventListener('submit',async event => { event.preventDefault(); await filterImports(byId('imports-batch-id').value.trim()); });
      byId('imports-clear-filter').addEventListener('click',() => filterImports(''));
      byId('batch-filter-form').addEventListener('submit',async event => { event.preventDefault(); await applyBatchFilter(byId('batch-status-filter').value); });
      byId('batch-filter-clear').addEventListener('click',async () => { byId('batch-status-filter').value = ''; await applyBatchFilter(''); });
      byId('items-filter-form').addEventListener('submit',async event => { event.preventDefault(); await applyItemFilter(Object.fromEntries(['q','era','category','institution'].map(key => [key, byId('item-filter-' + key).value.trim()]))); });
      byId('items-filter-clear').addEventListener('click',async () => { for (const key of ['q','era','category','institution']) byId('item-filter-' + key).value = ''; await applyItemFilter({q:'',era:'',category:'',institution:''}); });
      try { const session = await api('/session'); if (session.authenticated !== true || session.authorized !== true) { setAccess(session.authenticated === true); return; } state.authorized = true; byId('access').hidden = true; byId('workspace').hidden = false; byId('refresh').hidden = false; await refresh(); }
      catch (error) { if (error.status !== 401 && error.status !== 403) { byId('access-title').textContent = '暂时无法核验身份'; byId('access-message').textContent = error.message; byId('refresh').hidden = false; byId('refresh').textContent = '重新核验'; byId('refresh').addEventListener('click',() => root.location.reload(),{once:true}); } }
    }
    return {start,state,refresh,refreshPublications,mutate,selectProvider,selectPublicationProvider};
  }
  const exported = {parseObjectIds,modePayload,creationViewId,viewLabel,publicationDate,officialUrl,text,count,timestamp,errorMessage,isHeld,holdText,createController,publicationProviders:PUBLICATION_PROVIDERS};
  if (typeof module === 'object' && module.exports) module.exports = exported;
  else { root.AtlasControlUI = Object.freeze(exported); if (root.document) createController(root.document,root.fetch.bind(root)).start(); }
})(typeof globalThis === 'object' ? globalThis : this);
