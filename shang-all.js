'use strict';
(function(){
  if(window.__JT_LOCKED__)return;
  const $=selector=>document.querySelector(selector);
  const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const plain=value=>String(value??'').replace(/<[^>]*>/g,'');
  const collator=new Intl.Collator('zh-CN');
  const state={query:'',category:'all',evidence:'all',license:'all',sort:'original',saved:false,limit:18};
  let pack=null,records=[],searchText=new Map(),saved=new Set();
  try{const value=JSON.parse(localStorage.getItem('civilization-references')||'[]');if(Array.isArray(value))saved=new Set(value.filter(x=>typeof x==='string'));}catch{}

  function safeUrl(value,allowRelative=false){
    if(typeof value!=='string'||!value.trim()||/[\u0000-\u001f]/.test(value))return '';
    try{
      const url=new URL(value,location.href);
      if(!['http:','https:'].includes(url.protocol))return '';
      if(!allowRelative&&!/^https?:\/\//i.test(value))return '';
      if(allowRelative&&/^\s*(?:javascript:|data:)/i.test(value))return '';
      return value;
    }catch{return ''}
  }
  function sourceUrl(record){return safeUrl(record.sourceUrl||record.apiUrl||'')}
  function originalImageUrl(record){return safeUrl(record.originalImageUrl||record.imageUrl||'')}
  function displayImageUrl(record){return safeUrl(record.localImage||record.previewUrl||record.imageUrl||'',true)}
  function imgFallback(record){return '<span class="source-placeholder">原图暂未载入<small>请打开原始出处核对，不以其他图片代替。</small></span>'}
  function imageMarkup(record){
    if(record.displayMode==='source-only')return '<span class="source-placeholder">原站查阅<small>该条仅在来源页面查看原图。</small></span>';
    const url=displayImageUrl(record);
    return url?'<img src="'+escapeHtml(url)+'" alt="'+escapeHtml(plain(record.title))+'" loading="lazy" referrerpolicy="no-referrer">':imgFallback(record);
  }
  function bindImageFallback(root){
    root.querySelectorAll('img').forEach(img=>img.addEventListener('error',()=>{
      const id=img.closest('[data-detail]')?.dataset.detail;
      const record=records.find(item=>item.id===id);
      const alternate=record&&originalImageUrl(record);
      if(alternate&&img.dataset.fallbackTried!=='1'&&img.getAttribute('src')!==alternate){
        img.dataset.fallbackTried='1';img.src=alternate;return;
      }
      img.replaceWith(document.createRange().createContextualFragment(imgFallback(record||{})));
    }));
  }
  function recordSearchText(record){
    const fields=['title','originalTitle','date','originalPeriod','material','institution','institutionShort','objectNumber','findspot','description','notes','sourceTitle','category','evidence','catalogNumber','citation','locator','polity'];
    return fields.map(key=>record[key]||'').concat(record.topics||[],record.subjects||[]).join(' ').toLocaleLowerCase();
  }
  function filtered(){
    let list=records.filter(record=>(state.category==='all'||record.category===state.category)&&
      (state.evidence==='all'||record.evidence===state.evidence)&&
      (state.license==='all'||Boolean(record.openLicense)===(state.license==='open'))&&
      (!state.saved||saved.has(record.id))&&
      (!state.query||searchText.get(record.id).includes(state.query)));
    if(state.sort==='title')list=list.sort((a,b)=>collator.compare(plain(a.title),plain(b.title)));
    if(state.sort==='institution')list=list.sort((a,b)=>collator.compare(a.institution||'',b.institution||''));
    return list;
  }
  function render(){
    const list=filtered();
    $('#count').textContent='当前 '+list.length+' 条 / 全库商代 '+records.length+' 条 · 点击图像查看出处与许可';
    $('#grid').innerHTML=list.slice(0,state.limit).map(record=>{
      const source=sourceUrl(record);
      return '<article class="card"><button class="image-button" type="button" data-detail="'+escapeHtml(record.id)+'" aria-label="查看'+escapeHtml(plain(record.title))+'的原始著录">'+imageMarkup(record)+'<span class="image-label">'+escapeHtml(record.evidence||'图像记录')+'</span></button><button class="save '+(saved.has(record.id)?'saved':'')+'" type="button" data-save="'+escapeHtml(record.id)+'" aria-label="'+(saved.has(record.id)?'移出':'加入')+'参考集：'+escapeHtml(plain(record.title))+'" aria-pressed="'+saved.has(record.id)+'">'+(saved.has(record.id)?'♥':'♡')+'</button><div class="card-copy"><div class="kicker">'+escapeHtml(record.category||'未分类')+' · '+escapeHtml(record.catalogNumber||record.id)+'</div><button class="title-button" type="button" data-detail="'+escapeHtml(record.id)+'">'+escapeHtml(plain(record.title))+'</button><p class="card-date">'+escapeHtml(record.date||record.originalPeriod||'原始断代待查')+'</p><div class="card-source"><span>'+escapeHtml(record.institutionShort||record.institution||'来源机构待查')+'<br>'+(record.openLicense?'◈ 原记录标注开放':'↗ 许可见原页')+'</span>'+(source?'<a href="'+escapeHtml(source)+'" target="_blank" rel="noopener noreferrer">原始出处 ↗</a>':'')+'</div></div></article>';
    }).join('');
    $('#empty').hidden=!!list.length;
    $('#loadMore').hidden=list.length<=state.limit;
    $('#loadMore').textContent='继续浏览 ↓（还有 '+Math.max(0,list.length-state.limit)+' 条）';
    $('#savedToggle').setAttribute('aria-pressed',String(state.saved));
    $('#savedToggle').textContent=(state.saved?'♥':'♡')+' 我的参考集（'+[...saved].filter(id=>records.some(r=>r.id===id)).length+'）';
    bindImageFallback($('#grid'));
  }
  function toast(message){const el=$('#toast');el.textContent=message;el.classList.add('show');clearTimeout(window.__shangToastTimer);window.__shangToastTimer=setTimeout(()=>el.classList.remove('show'),3000)}
  function save(id){
    saved.has(id)?saved.delete(id):saved.add(id);
    try{localStorage.setItem('civilization-references',JSON.stringify([...saved]));}catch{toast('浏览器保存不可用，请导出记录备份。')}
    render();
    const button=$('#detailContent [data-detail-save]');
    if(button&&button.dataset.detailSave===id)button.textContent=saved.has(id)?'♥ 已加入参考集':'♡ 加入参考集';
  }
  function link(url,label){const safe=safeUrl(url);return safe?'<a class="source-link" href="'+escapeHtml(safe)+'" target="_blank" rel="noopener noreferrer">'+escapeHtml(label)+' ↗</a>':''}
  function detail(id){
    const record=records.find(item=>item.id===id);if(!record)return;
    const image=displayImageUrl(record),original=originalImageUrl(record),source=sourceUrl(record);
    const review=({automatic:'自动检查通过 · 未逐图视觉复核',ai:'AI 逐图视觉复核',human:'人工复核'})[record.verification?.reviewerType]||'原记录未标注审核类型';
    $('#detailContent').innerHTML='<div class="detail-layout"><div class="detail-image" data-detail="'+escapeHtml(record.id)+'">'+(record.displayMode==='source-only'?imgFallback(record):image?'<img src="'+escapeHtml(image)+'" alt="'+escapeHtml(plain(record.title))+'来源图像" referrerpolicy="no-referrer">':imgFallback(record))+'<p>'+escapeHtml(record.evidence||'图像记录')+' · '+escapeHtml(record.imageCredit||record.institution||'来源详见著录')+'<br>'+(original?'<a href="'+escapeHtml(original)+'" target="_blank" rel="noopener noreferrer">查看来源原图 ↗</a>':'')+(source?' · <a href="'+escapeHtml(source)+'" target="_blank" rel="noopener noreferrer">原始著录 ↗</a>':'')+'</p></div><div class="detail-text"><p class="eyebrow">'+escapeHtml(record.catalogNumber||record.id)+' / 商 / '+escapeHtml(record.category||'未分类')+'</p><h2 id="detailTitle">'+escapeHtml(plain(record.title))+'</h2>'+(record.originalTitle?'<p class="original">来源原名：'+escapeHtml(plain(record.originalTitle))+'</p>':'')+'<p>'+escapeHtml(record.description||'原记录未提供说明')+'</p><dl><dt>原始断代</dt><dd>'+escapeHtml(record.date||record.originalPeriod||'待查')+'</dd><dt>审核类型</dt><dd class="review-status">'+escapeHtml(review)+'</dd><dt>材质／工艺</dt><dd>'+escapeHtml(record.material||'原记录未标注')+'</dd><dt>收藏／来源</dt><dd>'+escapeHtml(record.institution||'原记录未标注')+'</dd><dt>馆藏标识</dt><dd>'+escapeHtml(record.objectNumber||'原记录未标注')+'</dd><dt>出土／所在地</dt><dd>'+escapeHtml(record.findspot||'原记录未标注')+'</dd><dt>图像性质</dt><dd>'+escapeHtml(record.evidence||'原记录未标注')+'</dd><dt>来源定位</dt><dd>'+escapeHtml(record.locator||'请见原始来源')+'</dd></dl><h3>参考说明与边界</h3><p class="boundary">'+escapeHtml(record.notes||'原记录未标注')+'</p><h3>原始出处</h3>'+(source?link(source,plain(record.sourceTitle)||'查看原始著录'):'<p>原始出处链接未标注。</p>')+(record.additionalSources||[]).map(item=>link(item.url,'补充依据：'+plain(item.title||'来源'))).join('')+(record.apiUrl&&record.apiUrl!==source?link(record.apiUrl,'来源开放数据接口'):'')+'<p class="review-status">来源核验日期：'+escapeHtml(record.verifiedAt||'原记录未标注')+'。本页保留原记录中的审核状态，不代替独立鉴定。</p>'+(record.citation?'<p class="citation">'+escapeHtml(record.citation)+'</p>':'')+'<h3>图片使用许可</h3><p>'+escapeHtml(record.rights||'原记录未标注；请以来源机构最新条款为准')+'</p>'+(record.rightsUrl?link(record.rightsUrl,'来源许可条款'):'')+'<div class="detail-actions"><button class="primary" type="button" data-detail-save="'+escapeHtml(record.id)+'">'+(saved.has(record.id)?'♥ 已加入参考集':'♡ 加入参考集')+'</button><button class="outline" type="button" data-copy="'+escapeHtml(record.id)+'">复制引用</button><button class="outline" type="button" data-export="'+escapeHtml(record.id)+'">导出本条</button></div></div></div>';
    bindImageFallback($('#detailContent'));
    if(!$('#detail').open)$('#detail').showModal();
    $('#detail').scrollTop=0;
    history.replaceState(null,'','#item='+encodeURIComponent(id));
  }
  function closeDetail(){if($('#detail').open)$('#detail').close();if(location.hash.startsWith('#item='))history.replaceState(null,'','#collection')}
  function downloadJson(data,name){
    const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'});
    const url=URL.createObjectURL(blob),anchor=document.createElement('a');
    anchor.href=url;anchor.download=name;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),5000);
  }
  function reset(){
    Object.assign(state,{query:'',category:'all',evidence:'all',license:'all',sort:'original',saved:false,limit:18});
    $('#search').value='';for(const key of ['category','evidence','license','sort'])$('#'+key).value=state[key];render();
  }
  async function init(){
    try{
      const version=$('meta[name="shang-all-data-hash"]')?.content||'';
      const response=await fetch('shang-all-data.json.gz?v='+encodeURIComponent(version));
      if(!response.ok)throw new Error('目录 HTTP '+response.status);
      const bytes=new Uint8Array(await response.arrayBuffer());
      const stream=new Blob([bytes]).stream();
      const zipped=bytes[0]===31&&bytes[1]===139;
      if(zipped&&typeof DecompressionStream!=='function')throw new Error('此浏览器不支持压缩目录');
      pack=JSON.parse(await new Response(zipped?stream.pipeThrough(new DecompressionStream('gzip')):stream).text());
      if(!Array.isArray(pack.records)||!pack.records.length||pack.records.some(r=>r.era!=='商'||!r.id))throw new Error('商代目录数据无效');
      records=pack.records;
      searchText=new Map(records.map(record=>[record.id,recordSearchText(record)]));
      $('#stats').innerHTML=[[records.length,'全库商代记录'],[new Set(records.map(r=>r.institution).filter(Boolean)).size,'来源机构'],[records.filter(r=>r.openLicense).length,'原记录标注开放图像']].map(([number,label])=>'<span><strong>'+number+'</strong><small>'+label+'</small></span>').join('');
      for(const key of ['category','evidence']){
        const values=[...new Set(records.map(r=>r[key]).filter(Boolean))].sort(collator.compare);
        $('#'+key).innerHTML+=[...values].map(value=>'<option value="'+escapeHtml(value)+'">'+escapeHtml(value)+'</option>').join('');
      }
      const hero=records.find(r=>r.id==='npm-2831-CARD'&&displayImageUrl(r))||records.find(r=>r.localImage&&r.openLicense&&displayImageUrl(r))||records.find(r=>displayImageUrl(r));
      if(hero&&displayImageUrl(hero)){
        const heroObject=$('#heroObject');
        heroObject.insertAdjacentHTML('beforeend','<img src="'+escapeHtml(displayImageUrl(hero))+'" alt="'+escapeHtml(plain(hero.title))+'" referrerpolicy="no-referrer">');
        heroObject.querySelector('.hero-caption').innerHTML='<span>'+escapeHtml(plain(hero.title))+' · '+escapeHtml(hero.institutionShort||hero.institution||'来源见详情')+'</span><a href="#item='+encodeURIComponent(hero.id)+'" data-detail="'+escapeHtml(hero.id)+'">查看出处 ↗</a>';
        bindImageFallback(heroObject);
      }
      render();
      if(location.hash.startsWith('#item='))detail(decodeURIComponent(location.hash.slice(6)));
      window.__SHANG_ALL_READY__={count:records.length,revision:pack.revision||'',at:performance.now()};
    }catch(error){
      console.error(error);
      $('#count').textContent='目录暂时无法读取，请刷新重试，或使用上方的独立精选专页。';
      window.__SHANG_ALL_ERROR__=String(error);
    }
  }
  $('#search').addEventListener('input',event=>{state.query=event.target.value.trim().toLocaleLowerCase();state.limit=18;render()});
  for(const key of ['category','evidence','license','sort'])$('#'+key).addEventListener('change',event=>{state[key]=event.target.value;state.limit=18;render()});
  $('#reset').onclick=reset;
  $('#savedToggle').onclick=()=>{state.saved=!state.saved;state.limit=18;render()};
  $('#loadMore').onclick=()=>{state.limit+=18;render()};
  $('#exportSelection').onclick=()=>pack&&downloadJson({title:'中华文明影像库 · 全库商代筛选',revision:pack.revision,version:pack.version,count:filtered().length,records:filtered()},'中华文明影像库-商代全库-当前结果.json');
  $('#closeDetail').onclick=closeDetail;
  $('#detail').addEventListener('click',event=>{if(event.target===$('#detail'))closeDetail()});
  $('#detail').addEventListener('cancel',closeDetail);
  document.addEventListener('click',async event=>{
    const target=event.target.closest('button,a');if(!target)return;
    if(target.dataset.detail){event.preventDefault();detail(target.dataset.detail);return}
    if(target.dataset.save||target.dataset.detailSave){save(target.dataset.save||target.dataset.detailSave);return}
    if(target.dataset.export){const record=records.find(r=>r.id===target.dataset.export);if(record)downloadJson(record,'商代-'+record.id+'.json');return}
    if(target.dataset.copy){const record=records.find(r=>r.id===target.dataset.copy);if(!record)return;try{await navigator.clipboard.writeText(record.citation||record.sourceUrl||'');toast('已复制原记录引用')}catch{downloadJson({citation:record.citation,sourceUrl:record.sourceUrl},'商代-'+record.id+'-引用.json');toast('已导出引用')}}
  });
  init();
})();
