(function (root) {
  'use strict';
  const API = '/api/atlas-control';
  const LABELS = {queued:'等待执行',pending:'待处理',pending_review:'待审核',running:'执行中',leased:'执行中',paused:'已暂停',completed:'已完成',complete:'已完成',failed:'失败',retry_wait:'等待重试',retrying:'等待重试',provider_hold:'来源暂停',source_hold:'来源暂停',candidate:'待审核候选',approved:'审核通过',rejected:'审核退回',reviewed:'已审核'};
  function text(value, fallback = '未注明') { return value === null || value === undefined || value === '' ? fallback : String(value); }
  function count(value) { return Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }
  function timestamp(value) { if (!value) return '—'; const date = new Date(value); return Number.isFinite(date.getTime()) ? date.toISOString().replace('T', ' ').replace(/\.000Z$/, 'Z').replace(/Z$/, ' UTC') : '时间未注明'; }
  function parseObjectIds(value) {
    const parts = String(value).trim().split(/[\s,，、;；]+/).filter(Boolean);
    if (!parts.length || parts.length > 50) throw new Error('请输入 1–50 个正整数对象编号。');
    if (parts.some(part => !/^[1-9]\d*$/.test(part) || !Number.isSafeInteger(Number(part)))) throw new Error('仅接受正整数 Met 对象编号，不接受 URL、小数或其他文字。');
    return [...new Set(parts.map(Number))];
  }
  function officialUrl(value, kind) {
    if (typeof value !== 'string') return null;
    try {
      const url = new URL(value);
      if (url.protocol !== 'https:' || url.username || url.password || url.port || url.search || url.hash || url.href !== value) return null;
      const source = url.hostname === 'www.metmuseum.org' && /^\/art\/collection\/search\/[1-9]\d*$/.test(url.pathname);
      const image = url.hostname === 'images.metmuseum.org' && /^\/CRDImages\/[a-z0-9-]+\/original\/[^/]+$/i.test(url.pathname);
      const rights = url.hostname === 'www.metmuseum.org' && url.pathname === '/about-the-met/policies-and-documents/open-access';
      return (kind === 'image' ? image : kind === 'rights' ? rights : source) ? url.href : null;
    } catch (_) { return null; }
  }
  function errorMessage(status, code) {
    if (status === 401) return '会话已失效，请重新登录。';
    if (status === 403) return '当前账号没有管理权限。';
    if (status === 409) return '记录状态已改变，或来源暂停尚未解除。请刷新后核对。';
    if (status === 429) return '请求过于频繁，请稍后重试。';
    if (status === 503) return '管理服务暂不可用，请稍后刷新。';
    if (status === 400 || status === 422) return '提交内容未通过校验，请检查编号、审核项与备注。';
    return code === 'NETWORK' ? '网络请求未完成，请检查连接后重试。' : '操作未完成（HTTP ' + status + '），请稍后重试。';
  }
  function isHeld(record) { return !!(record && (record.providerHold || record.sourceHold || Array.isArray(record.providerHolds) && record.providerHolds.some(hold => hold.active === true) || record.status === 'provider_hold' || record.status === 'source_hold')); }
  function holdText(hold) { return text(hold && (hold.reason || hold.message || [hold.code,hold.httpStatus && 'HTTP ' + hold.httpStatus,hold.holdUntil && '保留至 ' + timestamp(hold.holdUntil)].filter(Boolean).join(' · ')),'来源限制尚未解除；相关批次不可重试。'); }
  function createController(document, fetchFn) {
    const byId = id => document.getElementById(id);
    const state = {authorized:false,summary:null,batches:[],items:[],busy:false,loading:false,epoch:0,batchesOffset:0,itemsOffset:0,limit:20,batchesTotal:0,itemsTotal:0};
    function node(tag, className, value) { const el = document.createElement(tag); if (className) el.className = className; if (value !== undefined) el.textContent = String(value); return el; }
    function showNotice(message, error) { const box = byId('notice'); box.textContent = message; box.className = 'notice' + (error ? ' error' : ''); box.hidden = !message; }
    function setAccess(authenticated, reason) {
      state.authorized = false; state.epoch++; state.summary = null; state.batches = []; state.items = []; state.batchesTotal = state.itemsTotal = 0;
      byId('workspace').hidden = true; byId('refresh').hidden = true; byId('access').hidden = false;
      byId('access-title').textContent = authenticated ? '此账号没有管理权限' : '登录后继续';
      byId('access-message').textContent = reason || (authenticated ? '仅获授权的管理员可访问采集队列与审核记录。' : '使用本站 ChatGPT 登录验证身份。登录成功后将返回此工作台。');
      byId('signin').hidden = authenticated;
      byId('batches').replaceChildren(); byId('items').replaceChildren(); byId('counts').replaceChildren();
    }
    async function api(route, options) {
      let response;
      try { response = await fetchFn(API + route, {credentials:'same-origin',redirect:'error',cache:'no-store',headers:{'Accept':'application/json',...(options ? {'Content-Type':'application/json'} : {})},...options}); }
      catch (_) { const error = new Error(errorMessage(0, 'NETWORK')); error.status = 0; throw error; }
      let data; try { data = await response.json(); } catch (_) { data = {}; }
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) setAccess(response.status === 403);
        const error = new Error(errorMessage(response.status, data.error && data.error.code)); error.status = response.status; throw error;
      }
      return data;
    }
    function field(list, label, value) { list.append(node('dt', '', label), node('dd', '', text(value))); }
    function badge(status) { return node('span', 'badge' + (['failed','rejected'].includes(status) ? ' danger' : ['provider_hold','source_hold','paused','retry_wait'].includes(status) ? ' warning' : ''), LABELS[status] || text(status, '状态未注明')); }
    function link(container, label, value, kind) { const href = officialUrl(value, kind); if (!href) return; const anchor = node('a', '', label + ' ↗'); anchor.href = href; anchor.target = '_blank'; anchor.rel = 'noopener noreferrer'; container.append(anchor); }
    function renderSummary(summary) {
      state.summary = summary;
      const counts = summary.counts || {};
      const specs = [['successCandidates','成功候选','采集已产生记录'],['failedRequests','失败请求','累计采集失败次数'],['pendingObjects','待采集对象','尚未完成采集'],['pending','待审核候选','等待独立审核'],['imported','正式入库','独立接收流程'],['batches','批次数','控制队列']];
      const aliases = {successCandidates:counts.successCandidates ?? counts.collected ?? summary.items?.total,failedRequests:counts.failedRequests,pendingObjects:counts.pendingObjects,pending:counts.pending ?? summary.items?.pending_review,imported:counts.imported ?? summary.imported,batches:typeof counts.batches === 'number' ? counts.batches : summary.batches?.total};
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
    function renderBatches(result) {
      state.batches = Array.isArray(result.items) ? result.items : []; state.batchesTotal = Number.isSafeInteger(result.total) ? result.total : state.batches.length;
      byId('batches-total').textContent = count(state.batchesTotal) + ' 个批次';
      const cards = state.batches.map(batch => {
        const card = node('article','batch-card'), head = node('div','batch-head'); head.append(node('span','batch-id',text(batch.id)),badge(batch.status)); card.append(head);
        const meta = node('dl','batch-meta');
        const details = [['游标',count(batch.cursor) + ' / ' + count(batch.objectIds && batch.objectIds.length)],['租约截止',timestamp(batch.leaseUntil || batch.leaseExpiresAt)],['下次重试',timestamp(batch.nextAttemptAt || batch.nextRetryAt)],['创建时间',timestamp(batch.createdAt)]];
        const c = batch.counts || batch; details.push(['成功候选',count(c.collected ?? c.successCandidates)],['失败请求',count(c.failedRequests)],['待审核',count(c.pending)],['正式入库',count(c.imported)]);
        for (const [label,value] of details) { const group = node('div'); field(group,label,value); meta.append(group); } card.append(meta);
        const held = isHeld(batch) || isHeld(state.summary);
        const error = batch.error || batch.lastError;
        if (held) card.append(node('p','batch-hold','来源暂停：' + holdText(error || state.summary?.providerHolds?.find(hold => hold.active === true) || batch.providerHold || batch.sourceHold)));
        else if (error) card.append(node('p','batch-hold','最近错误：' + text(error.message || error.code)));
        const actions = node('div','actions');
        actions.append(action('暂停批次',() => mutate('/batches/' + encodeURIComponent(batch.id) + '/pause',{}),!['queued','pending','running','leased','retry_wait','retrying'].includes(batch.status)),action('重试批次',() => mutate('/batches/' + encodeURIComponent(batch.id) + '/retry',{}),held || !['failed','paused','retry_wait','retrying'].includes(batch.status)));
        card.append(actions); return card;
      });
      byId('batches').replaceChildren(...(cards.length ? cards : [node('p','empty','尚无采集批次。创建批次后，队列会显示在这里。')])); pagination('batches');
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
        const card = node('article','candidate-card'), photo = node('div','candidate-photo'), imageUrl = officialUrl(item.originalImageUrl || item.imageUrl,'image');
        if (imageUrl) { const image = node('img'); image.src = imageUrl; image.alt = text(item.title,'官方候选图像'); image.loading = 'lazy'; image.referrerPolicy = 'no-referrer'; image.addEventListener('error',() => photo.replaceChildren(node('span','muted','原图预览暂不可用，请通过官方原图链接核验。')),{once:true}); photo.append(image); } else photo.append(node('span','muted','缺少可验证的官方原图地址。'));
        const body = node('div','candidate-body'); body.append(badge(item.status),node('h3','',text(item.title,'题名待考'))); const meta = node('dl','candidate-meta');
        field(meta,'对象编号',item.objectId ?? item.sourceRecordId); field(meta,'原始年代',item.originalDateText || item.date); field(meta,'原始时期',item.originalPeriod); field(meta,'图谱时期',item.era); field(meta,'权利',item.rights); field(meta,'权利状态',item.rightsStatus); field(meta,'材质 / 尺寸',[item.material,item.dimensions].filter(Boolean).join(' / ')); field(meta,'待考字段',Array.isArray(item.unknownFields) && item.unknownFields.length ? item.unknownFields.join('、') : '未列明；不等于全部已核实'); body.append(meta);
        const links = node('div','candidate-links'); link(links,'官方对象页',item.sourceUrl); link(links,'官方精确原图',item.originalImageUrl || item.imageUrl,'image'); link(links,'官方开放权利',item.rightsUrl,'rights'); body.append(links);
        const hash = node('div','hash'); hash.append(node('b','','IMAGE SHA-256'),node('span','',text(item.imageSha256,'缺失，无法提交审核'))); body.append(hash);
        const review = item.review || item.latestReview;
        if (review) { const history = node('div','review-history'); history.append(node('p','','最近审核：' + text(review.decision) + ' · ' + text(review.reviewerType) + ' · ' + timestamp(review.createdAt || review.reviewedAt)),node('p','',text(review.note))); body.append(history); }
        body.append(reviewForm(item)); card.append(photo,body); return card;
      });
      byId('items').replaceChildren(...(cards.length ? cards : [node('p','empty','暂无候选。执行器成功采集后，记录会出现在这里。')])); pagination('items');
    }
    function pagination(kind) { const offset = state[kind + 'Offset'], total = state[kind + 'Total']; byId(kind + '-prev').disabled = state.busy || offset === 0; byId(kind + '-next').disabled = state.busy || offset + state.limit >= total; byId(kind + '-page').textContent = total ? (offset + 1) + '–' + Math.min(offset + state.limit,total) + ' / ' + total : '0 / 0'; }
    function busy(value) { state.busy = value; byId('refresh').disabled = value; byId('create-batch').disabled = value; for (const button of byId('workspace').querySelectorAll('button')) if (value) button.disabled = true; if (!value && state.authorized) { renderBatches({items:state.batches,total:state.batchesTotal}); renderItems({items:state.items,total:state.itemsTotal}); } }
    async function refresh() {
      if (!state.authorized || state.loading) return; state.loading = true; const epoch = state.epoch;
      byId('refresh').disabled = true; byId('workspace').setAttribute('aria-busy','true'); for (const button of byId('workspace').querySelectorAll('button')) button.disabled = true;
      try {
        const results = await Promise.all([api('/summary'),api('/batches?limit=' + state.limit + '&offset=' + state.batchesOffset),api('/items?limit=' + state.limit + '&offset=' + state.itemsOffset)]);
        if (!state.authorized || epoch !== state.epoch) return; renderSummary(results[0]); renderBatches(results[1]); renderItems(results[2]);
      } catch (error) { showNotice(error.message,true); }
      finally { state.loading = false; byId('workspace').setAttribute('aria-busy','false'); byId('refresh').disabled = state.busy; byId('create-batch').disabled = state.busy; if (state.authorized) { renderBatches({items:state.batches,total:state.batchesTotal}); renderItems({items:state.items,total:state.itemsTotal}); } }
    }
    async function mutate(route, body, success) {
      if (state.busy || state.loading || !state.authorized) return; busy(true); showNotice('',false);
      try { await api(route,{method:'POST',body:JSON.stringify(body)}); showNotice(success || '操作已保存；队列状态以刷新结果为准。',false); await refresh(); }
      catch (error) { showNotice(error.message,true); if (error.status === 409 && state.authorized) await refresh(); }
      finally { busy(false); }
    }
    async function start() {
      byId('refresh').addEventListener('click',refresh);
      byId('batch-form').addEventListener('submit',async event => { event.preventDefault(); if (state.busy) return; let objectIds; try { objectIds = parseObjectIds(byId('object-ids').value); byId('ids-error').hidden = true; } catch (error) { byId('ids-error').textContent = error.message; byId('ids-error').hidden = false; byId('object-ids').focus(); return; } await mutate('/batches',{objectIds},'批次已加入队列，等待本机执行器采集。'); });
      for (const kind of ['batches','items']) for (const direction of ['prev','next']) byId(kind + '-' + direction).addEventListener('click',async () => { state[kind + 'Offset'] = Math.max(0,state[kind + 'Offset'] + (direction === 'next' ? state.limit : -state.limit)); await refresh(); });
      try { const session = await api('/session'); if (session.authenticated !== true || session.authorized !== true) { setAccess(session.authenticated === true); return; } state.authorized = true; byId('access').hidden = true; byId('workspace').hidden = false; byId('refresh').hidden = false; await refresh(); }
      catch (error) { if (error.status !== 401 && error.status !== 403) { byId('access-title').textContent = '暂时无法核验身份'; byId('access-message').textContent = error.message; byId('refresh').hidden = false; byId('refresh').textContent = '重新核验'; byId('refresh').addEventListener('click',() => root.location.reload(),{once:true}); } }
    }
    return {start,state,refresh,mutate};
  }
  const exported = {parseObjectIds,officialUrl,text,count,timestamp,errorMessage,isHeld,holdText,createController};
  if (typeof module === 'object' && module.exports) module.exports = exported;
  else { root.AtlasControlUI = Object.freeze(exported); if (root.document) createController(root.document,root.fetch.bind(root)).start(); }
})(typeof globalThis === 'object' ? globalThis : this);
