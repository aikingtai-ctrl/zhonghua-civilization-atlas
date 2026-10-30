(() => {
  const pack=window.ARCHIVE_DATA.prehistory;
  if(!pack)return;
  let culture='all', region='all';
  const items=records.filter(r=>r.era==='史前');
  const oldFiltered=filtered, oldRender=renderCards, oldReset=reset, oldView=setView, oldClose=closeDialog;
  const q=s=>document.querySelector(s), e=esc;
  const cultures=[...new Set(items.map(r=>r.cultureGroup||r.culture).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'zh-CN'));
  const regions=[...new Set(items.map(r=>r.regionGroup||r.coverageRegion).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'zh-CN'));
  const section=document.createElement('section');section.id='prehistoryPanel';section.className='preh-hub';section.hidden=true;
  section.innerHTML=`<div class="eyebrow">PREHISTORY · ARCHAEOLOGICAL EVIDENCE</div><div class="preh-heading"><div><h1>史前 · 视觉美术参考</h1><p>从石器、彩陶和玉器，到聚落、生产与生活。</p></div><a class="secondary" href="prehistory-reference-pack.json" download="史前影像与出处目录.json">↓ 下载史前资料包</a></div><p class="preh-intro">按考古文化与遗址寻找依据。原件、复制品、遗址现状和考古图分别标识，逐图保留来源与使用边界。</p><div class="preh-stats"><span><b>${items.length}</b>条有源影像</span><span><b>${cultures.length}</b>组文化／遗址标签</span><span><b>${new Set(items.map(r=>new URL(r.sourceUrl).hostname)).size}</b>个来源网站</span><span><b>${items.filter(r=>r.polity==='旧石器时代').length}</b>条旧石器资料</span></div><div class="preh-index"><button data-preh-stage="all">全部史前</button><button data-preh-stage="旧石器时代">旧石器时代</button><button data-preh-stage="新石器时代">新石器时代</button><button data-preh-stage="transition">跨期／过渡材料</button><a href="#prehistoryReading">研究文献与参考范围 ↓</a></div>`;
  q('#explore').before(section);
  const nav=document.createElement('button');nav.className='nav';nav.dataset.prehOpen='true';nav.textContent='史前专题';/* The historical entry belongs to the chronology directory. */
  const filters=document.createElement('div');filters.className='preh-filters';filters.hidden=true;filters.id='prehistoryFilters';
  filters.innerHTML=`<label>文化／遗址<select id="prehistoryCulture"><option value="all">全部文化与遗址</option>${cultures.map(c=>`<option>${e(c)}</option>`).join('')}</select></label><label>地域<select id="prehistoryRegion"><option value="all">全部地域</option>${regions.map(c=>`<option>${e(c)}</option>`).join('')}</select></label><p>史前资料不分帝王年号。文化名称、年代和出土地以各条原始著录为准。</p>`;
  q('.results-meta').before(filters);
  const reading=document.createElement('section');reading.id='prehistoryReading';reading.className='preh-reading';reading.hidden=true;
  reading.innerHTML=`<div class="eyebrow">SOURCES · LIMITS · COVERAGE</div><h2>研究文献与原始来源</h2><p>下面分别注明核读程度；只查到书目或摘要的资料，不计作已经读过原始报告全书。</p><div class="preh-reading-grid">${pack.reading.map(r=>`<article><span>${e(r.institution)}</span><h3>${e(r.title)}</h3><p>${e(r.notes)}</p><small>${e(r.status)}</small><a href="${e(r.url)}" target="_blank" rel="noopener noreferrer">查看原始来源 ↗</a></article>`).join('')}</div><details open><summary>6项必须保留的参考边界</summary><ol>${pack.boundaries.map(b=>`<li>${e(b)}</li>`).join('')}</ol></details><details open><summary>地域覆盖与资料范围</summary><p>${e(pack.scope)}</p><div class="preh-coverage">${pack.coveragePlan.map(c=>`<article><h3>${e(c.area)}</h3><p>${e(c.targets)}</p><small>${e(c.gap)}</small></article>`).join('')}</div></details><p class="preh-verification">来源记录日期：${e(pack.verifiedAt)}。原始网页可能更新，来源日期与访问日期分别保留。不以“全面收齐”代替实际覆盖清单。</p>`;
  q('#timelinePanel').before(reading);
  let transition=false;
  const active=()=>state.view==='library'&&state.era==='史前'&&!state.saved;
  function sync(){
    const on=active();section.hidden=!on;filters.hidden=!on;reading.hidden=!on;nav.classList.toggle('active',on);document.body.classList.toggle('preh-active',on);
    if(on){q('#hero').hidden=true;q('.evidence-strip').hidden=true;q('.header [data-view="library"]').classList.remove('active');q('#search').placeholder='搜索文化、遗址、器物、工艺或出土地…';}else q('#search').placeholder='搜索朝代、服饰、器物、建筑或馆藏机构…';
    for(const b of section.querySelectorAll('[data-preh-stage]')){const selected=transition?b.dataset.prehStage==='transition':b.dataset.prehStage===(state.polity||'all');b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',String(selected));}
  }
  filtered=function(options){let list=oldFiltered(options);if(active())list=list.filter(r=>(culture==='all'||(r.cultureGroup||r.culture)===culture)&&(region==='all'||(r.regionGroup||r.coverageRegion)===region)&&(!transition||r.transition));return list;};
  renderCards=function(){oldRender();sync();if(active()){for(const card of q('#cards').querySelectorAll('.card')){const r=records.find(x=>x.id===card.querySelector('[data-detail]')?.dataset.detail);if(r){card.classList.add('preh-card');const label=document.createElement('p');label.className='preh-card-context';label.textContent=[r.culture,r.coverageRegion].filter(Boolean).join(' · ');card.querySelector('.card-date').after(label);}}}};
  reset=function(){culture='all';region='all';transition=false;q('#prehistoryCulture').value='all';q('#prehistoryRegion').value='all';oldReset();};
  setView=function(view,scroll=true){oldView(view,scroll);sync();};
  closeDialog=function(){oldClose();if(active())history.replaceState(null,'','#prehistory');};
  q('#closeDialog').onclick=closeDialog;
  function openPrehistory(stage='all',scroll=true){selectEra('史前',stage==='all'||stage==='transition'?null:stage,false);transition=stage==='transition';renderCards();history.replaceState(null,'','#prehistory');if(scroll)window.scrollTo({top:0,behavior:'smooth'});}
  nav.addEventListener('click',()=>openPrehistory());
  q('#clearFilters').onclick=()=>{if(active())openPrehistory('all',false);else reset();};
  q('#emptyReset').onclick=()=>{if(active())openPrehistory('all',false);else reset();};
  section.addEventListener('click',ev=>{const b=ev.target.closest('[data-preh-stage]');if(b)openPrehistory(b.dataset.prehStage,false);});
  for(const [id,type] of [['prehistoryCulture','culture'],['prehistoryRegion','region']])q('#'+id).addEventListener('change',ev=>{if(type==='culture')culture=ev.target.value;else region=ev.target.value;state.limit=12;renderCards();});
  const oldDetail=detail;
  detail=function(id){oldDetail(id);const r=records.find(x=>x.id===id);if(r?.era==='史前'){const meta=q('#detailContent .meta-grid');if(meta){meta.insertAdjacentHTML('beforeend',`<dt>文化／遗址</dt><dd>${e(r.culture||'未细分')}</dd><dt>地域标签</dt><dd>${e(r.coverageRegion||'见出土地')}</dd>`);}if(r.transition)q('#detailContent .description').insertAdjacentHTML('afterend','<p class="preh-transition">跨期／过渡材料：请保留原始断代，不将整条范围视为新石器时代。</p>');}};
  q('#detailDialog').addEventListener('cancel',()=>{if(active())history.replaceState(null,'','#prehistory');});
  const hash=location.hash;
  if(hash==='#prehistory'||hash==='#prehistoryReading'){openPrehistory('all',false);if(hash==='#prehistoryReading'){history.replaceState(null,'',hash);requestAnimationFrame(()=>reading.scrollIntoView());}}
  else if(hash.startsWith('#item=')){const id=decodeURIComponent(hash.slice(6));if(items.some(r=>r.id===id)){openPrehistory('all',false);detail(id);}}
  else sync();
})();


