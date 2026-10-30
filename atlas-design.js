/* Functional navigation and contextual modules; collection data is unchanged. */
(() => {
 const initialHash=location.hash;
 let pane='images',lastEra=null,sourceMode='institutions',sourceLimit=18;
 const expansionPlan=window.ATLAS_EXPANSION_PLAN;
 const q=s=>document.querySelector(s),qa=s=>[...document.querySelectorAll(s)],e=esc;
 document.body.classList.add('atlas-shell');
 q('.header nav').innerHTML='<button class="nav" data-view="library">影像检索</button><button class="nav" data-view="timeline">历代索引</button><button class="nav" data-view="expansion">10万扩容</button><button class="nav" data-view="standards">收录来源</button>';
 q('.evidence-strip').hidden=true;
 const results=q('.results-panel');
 const toolbar=document.createElement('div');toolbar.id='atlasModuleNav';toolbar.className='atlas-module-nav';toolbar.setAttribute('aria-label','当前资料模块');
 q('#chronologySelection').after(toolbar);
 const imagePane=document.createElement('section');imagePane.id='atlasImages';imagePane.setAttribute('aria-label','影像检索结果');
 const reignPane=document.createElement('section');reignPane.id='atlasReigns';
 const topicPane=document.createElement('section');topicPane.id='atlasTopics';
 const readingPane=document.createElement('section');readingPane.id='atlasReading';
 const filterShelf=document.createElement('details');filterShelf.className='atlas-specific-filters';filterShelf.id='atlasSpecificFilters';filterShelf.innerHTML='<summary>本期专用筛选 <span>分期、文化与生活场景</span></summary><div id="atlasFilterBody"></div>';
 for(const sel of ['.search-row','.filter-line','#xixiaSubcategories','.advanced','#xixiaSceneDrawer','#prehistoryFilters','.results-meta','#cards','#empty','#loadMore','#xixiaRelatedVisuals','.collection-note']){const el=q(sel);if(el)imagePane.append(el)}
 results.append(imagePane,reignPane,topicPane,readingPane);
 q('#cards')?.before(filterShelf);
 for(const id of ['tangPanel','xixiaPanel','xiaPanel','prehistoryPanel']){const el=q('#'+id);if(el)topicPane.append(el)}
 for(const id of ['tangReading','xixiaReading','xiaReading','prehistoryReading']){const el=q('#'+id);if(el)readingPane.append(el)}
 const eraHelp=document.createElement('div');eraHelp.className='atlas-era-context';eraHelp.id='atlasEraContext';q('.section-heading').after(eraHelp);
 const eraLinks={西汉:{url:'western-han.html',label:'西汉六期场景与专属图库'},东汉:{url:'eastern-han.html',label:'东汉七期视觉档案与专属图库'},三国:{url:'weijin.html#period=three-kingdoms',label:'三国专属视觉参考'},西晋:{url:'weijin.html#period=western-jin',label:'西晋专属视觉参考'},东晋:{url:'weijin.html#period=eastern-jin',label:'东晋专属视觉参考'},十六国:{url:'weijin.html#period=sixteen-kingdoms',label:'十六国专属视觉参考'},南朝:{url:'weijin.html#period=northern-southern',label:'南北朝专属视觉参考'},北朝:{url:'weijin.html#period=northern-southern',label:'南北朝专属视觉参考'},隋:{url:'sui.html',label:'隋代七期场景与专属图库'},金:{url:'jin.html',label:'金代分期与专属图库'},春秋:{url:'spring-autumn.html',label:'春秋诸国专属图库'},战国:{url:'warring-states.html',label:'战国各国视觉档案与图库'},秦:{url:'qin.html',label:'秦代五期场景与专属图库'},商:{url:'shang.html',label:'商代专题图像与文献'},西周:{url:'western-zhou.html',label:'西周专题图像与文献'}};
 const specifics=[['phaseFilters','唐'],['provenanceFilters','唐'],['xiaTopics','夏／二里头文化'],['xiaScope','夏／二里头文化'],['xixiaSceneCards','西夏']];
 for(const [id] of specifics){const el=q('#'+id);if(el)q('#atlasFilterBody').append(id==='xiaScope'?el.closest('.xia-scope'):el)}
 function goToResults(){if(matchMedia('(max-width:760px)').matches){q('.sidebar').classList.remove('mobile-open');q('#toggleChronology').textContent='展开目录';q('#toggleChronology').setAttribute('aria-expanded','false')}q('#explore').scrollIntoView({behavior:'smooth',block:'start'})}
 const oldRender=renderCards,oldView=setView,oldSelect=selectEra,oldChronology=selectChronology;
 function sync(){
  const gallery=['library','tang','xixia','xia'].includes(state.view),era=state.era;
  if(lastEra!==era){pane='images';lastEra=era;filterShelf.open=false}
  document.body.dataset.atlasView=gallery?'gallery':state.view;
  q('.header .nav[data-view="library"]').classList.toggle('active',gallery);
  q('.header .nav[data-view="timeline"]').classList.toggle('active',state.view==='timeline');
  q('.header .nav[data-view="expansion"]').classList.toggle('active',state.view==='expansion');
  q('.header .nav[data-view="standards"]').classList.toggle('active',state.view==='standards');
  qa('.header .nav').forEach(b=>b.setAttribute('aria-current',b.classList.contains('active')?'page':'false'));
  q('#hero').hidden=!gallery||era!=='all'||state.saved||!!state.query||!!state.sourceInstitution||!!state.chronoId;
  q('.evidence-strip').hidden=true;
  const hasReigns=!!window.ARCHIVE_DATA[era==='唐'?'tang':era==='西夏'?'xixia':'none']?.reigns;
  const hasTopics=!state.chronoId&&(['唐','西夏','夏／二里头文化','史前'].includes(era)||!!eraLinks[era]);
  if(pane==='reigns'&&!hasReigns||['topics','reading'].includes(pane)&&!hasTopics)pane='images';
  const node=chronologyNodes.get(state.chronoId);
  q('#resultsTitle').textContent=state.saved?'我的参考集':era==='all'?'影像检索':(era==='夏／二里头文化'?'夏 · 二里头文化':era)+' · '+(node?[node.kind!=='ruler'?node.ruler:null,node.label].filter(Boolean).join(' · ')+' · ':'')+'视觉美术参考';
  q('#atlasEraContext').innerHTML='<span class="atlas-scope">'+e(era==='all'?'全部历史时期':era)+'</span>'+(state.sourceInstitution?'<span class="atlas-selected-source">来源：'+e(state.sourceInstitution)+'</span>':node?'<span>'+e([node.ruler,node.reign||node.label].filter(Boolean).join(' · '))+'</span>':'<span>按年代、主题与来源查找图像</span>')+(era!=='all'||state.sourceInstitution?'<button data-atlas-all>返回全库 ↗</button>':'');
  if(era==='隋')q('#atlasEraContext').insertAdjacentHTML('beforeend','<a data-sui-entry href="sui.html">进入隋代七期专属图库 ↗</a>');
  toolbar.innerHTML=[['images','影像目录',filtered().length],...(hasReigns?[['reigns','执政者与年号',window.ARCHIVE_DATA[era==='唐'?'tang':'xixia'].reigns.profiles.length]]:[]),...(hasTopics?[['topics','专题资料',''],['reading','文献与来源','']]:[])].map(([id,label,n])=>'<button data-atlas-pane="'+id+'" aria-pressed="'+(pane===id)+'" class="'+(pane===id?'selected':'')+'">'+label+(n!==''?'<b>'+n+'</b>':'')+'</button>').join('');
  imagePane.hidden=pane!=='images';reignPane.hidden=pane!=='reigns';topicPane.hidden=pane!=='topics';readingPane.hidden=pane!=='reading';
  for(const id of ['tangReignDossier','xixiaDossierDrawer']){const el=q('#'+id);if(el&&el.parentElement!==reignPane)reignPane.append(el)}
  document.title=(state.view==='expansion'?'10万张扩容计划':q('#resultsTitle').textContent)+' | 中华文明影像库';
  if(q('#xixiaVisualTools'))q('#xixiaVisualTools').hidden=era!=='西夏'||pane!=='images';
  for(const [id,forEra] of specifics){const el=q('#'+id);if(el)(id==='xiaScope'?el.closest('.xia-scope'):el).hidden=era!==forEra}
  filterShelf.hidden=era==='西夏'||!specifics.some(([,forEra])=>forEra===era);
  for(const [id,forEra] of [['tangPanel','唐'],['xixiaPanel','西夏'],['xiaPanel','夏／二里头文化'],['prehistoryPanel','史前'],['tangReading','唐'],['xixiaReading','西夏'],['xiaReading','夏／二里头文化'],['prehistoryReading','史前']]){const el=q('#'+id);if(el)el.hidden=era!==forEra}
  qa('.atlas-dedicated-entry').forEach(el=>el.remove());
  if(eraLinks[era])for(const host of [topicPane,readingPane])host.insertAdjacentHTML('beforeend','<div class="atlas-dedicated-entry"><span class="eyebrow">COLLECTION & RESEARCH</span><h2>'+e(eraLinks[era].label)+'</h2><p>查看分期筛选、馆藏图像、发掘报告与图录。跨期资料在专题内单独标识。</p><a class="primary" href="'+eraLinks[era].url+(host===readingPane&&!eraLinks[era].url.includes('#')?'#literature':'')+'">进入专题 →</a></div>');
  q('#exportBtn').hidden=pane!=='images';
  q('#expansionPanel').hidden=state.view!=='expansion';
 }
 renderCards=function(){oldRender();sync()};
 setView=function(view,scroll=true){oldView(view,false);sync();if(scroll)window.scrollTo({top:0,behavior:'smooth'})};
 selectEra=function(era,polity=null,scroll=true){pane='images';state.sourceInstitution=null;oldSelect(era,polity,false);sync();if(scroll)goToResults()};
 selectChronology=function(id,scroll=true){oldChronology(id,false);pane='images';sync();if(scroll)goToResults()};
 const originalFiltered=filtered;
 filtered=function(options){return originalFiltered(options).filter(r=>!state.sourceInstitution||r.institution===state.sourceInstitution)};
 function clearAll(){state.sourceInstitution=null;selectEra('all',null,false);history.replaceState(null,'',location.pathname);q('#search').value='';renderCards();window.scrollTo({top:0,behavior:'smooth'})}
 document.addEventListener('click',ev=>{
  const b=ev.target.closest('button,a');if(!b)return;
  if(b.classList.contains('brand')){ev.preventDefault();ev.stopImmediatePropagation();clearAll();return}
  if(b.hasAttribute('data-tang-overview')||b.hasAttribute('data-chrono-reign-overview')){ev.preventDefault();ev.stopImmediatePropagation();selectEra(b.hasAttribute('data-tang-overview')?'唐':'西夏',null,false);pane='reigns';sync();q('#explore').scrollIntoView({behavior:'smooth'});return}
  if(b.matches('.header .nav')){ev.preventDefault();ev.stopImmediatePropagation();if(b.dataset.view==='library'){clearAll();goToResults()}else{setView(b.dataset.view);history.replaceState(null,'',b.dataset.view==='timeline'?'#timeline':b.dataset.view==='expansion'?'#expansion':'#sources');if(b.dataset.view==='expansion')requestAnimationFrame(()=>q('#expansionPanel').scrollIntoView({behavior:'smooth',block:'start'}))}return}
  if(b.hasAttribute('data-atlas-all')){state.sourceInstitution=null;selectEra('all');return}
  if(b.hasAttribute('data-xixia-open-evidence')){ev.preventDefault();ev.stopImmediatePropagation();pane='reigns';sync();const drawer=q('#xixiaDossierDrawer');if(drawer){drawer.open=true;drawer.scrollIntoView({behavior:'smooth',block:'start'})}return}
  if(b.dataset.atlasPane){pane=b.dataset.atlasPane;sync();if(pane==='reigns'&&state.era==='西夏'&&q('#xixiaDossierDrawer'))q('#xixiaDossierDrawer').open=true;return}
  if(b.dataset.atlasSource){sourceMode=b.dataset.atlasSource;sourceLimit=18;renderSources();return}
  if(b.dataset.atlasInstitution){state.sourceInstitution=null;selectEra('all',null,false);state.sourceInstitution=b.dataset.atlasInstitution;renderCards();history.replaceState(null,'','#explore');q('#explore').scrollIntoView({behavior:'smooth'});return}
  if(b.id==='atlasSourcesMore'){sourceLimit+=18;renderSources();return}
  if(b.matches('a[href^="#"]')){const id=b.getAttribute('href').slice(1);if(['tang-evidence','tangReading','xixiaSources','xixiaBooks','xiaBooks','prehistoryReading'].includes(id)){pane=id==='tang-evidence'?'topics':'reading';sync();requestAnimationFrame(()=>q('#'+id)?.scrollIntoView({behavior:'smooth'}))}}
 },true);
 q('#clearFilters').addEventListener('click',()=>{state.sourceInstitution=null;renderCards()});
 const sourcePanel=q('#standardsPanel');
 const method=sourcePanel.innerHTML;
 sourcePanel.innerHTML='<div class="atlas-page-heading"><div class="eyebrow">SOURCES & COLLECTIONS</div><h1>收录来源</h1><p>从收藏机构、原始页面与文献书目，回到每条图像的依据。</p></div><div class="atlas-source-tabs"><button data-atlas-source="institutions">来源机构</button><button data-atlas-source="books">文献书目</button><button data-atlas-source="method">收录说明</button></div><label class="atlas-directory-search"><span>⌕</span><input id="atlasSourceSearch" type="search" aria-label="搜索收录来源" placeholder="搜索机构、书名或来源关键词"></label><p id="atlasSourceCount" class="atlas-result-note" aria-live="polite"></p><div id="atlasSourceGrid" class="atlas-source-grid"></div><button id="atlasSourcesMore" class="load-more">查看更多来源 ↓</button><section id="atlasSourceMethod" hidden>'+method+'</section>';
 const institutions=[...new Set(records.map(r=>r.institution))].map(name=>{const list=records.filter(r=>r.institution===name);return{name,records:list,eras:[...new Set(list.map(r=>r.era))],url:list[0].sourceUrl}}).sort((a,b)=>b.records.length-a.records.length);
 const bookRows=[...(window.ARCHIVE_DATA.sui?.bibliography||[]).map(b=>({...b,era:'隋',use:b.note})),...(window.ARCHIVE_DATA.tang?.bibliography||[]).map(b=>({...b,era:'唐'})),...(window.ARCHIVE_DATA.xixia?.bibliography||[]).map(b=>({...b,era:'西夏'})),...(window.ARCHIVE_DATA.xia?.bibliography||[]).map(b=>({...b,era:'夏／二里头文化'})),...(window.ARCHIVE_DATA.prehistory?.reading||[]).map(b=>({...b,era:'史前'}))];
 const books=[...new Map(bookRows.map(b=>[(b.url||b.sourceUrl||'')+'|'+b.title,b])).values()];
 function renderSources(){
  const term=q('#atlasSourceSearch').value.trim().toLowerCase(),methodOn=sourceMode==='method';
  qa('[data-atlas-source]').forEach(b=>{b.classList.toggle('selected',b.dataset.atlasSource===sourceMode);b.setAttribute('aria-pressed',String(b.dataset.atlasSource===sourceMode))});
  q('#atlasSourceMethod').hidden=!methodOn;q('#atlasSourceGrid').hidden=methodOn;q('.atlas-directory-search').hidden=methodOn;q('#atlasSourceCount').hidden=methodOn;
  const list=(sourceMode==='books'?books:institutions).filter(r=>(sourceMode==='books'?[r.title,r.imprint,r.publication,r.era].join(' '):[r.name,...r.eras].join(' ')).toLowerCase().includes(term));
  q('#atlasSourceCount').textContent=methodOn?'':list.length+' '+(sourceMode==='books'?'项文献入口 · 书目收录不表示拥有全书图版':'个来源机构条目 · 数量按主库图像记录计算');
  q('#atlasSourceGrid').innerHTML=list.slice(0,sourceLimit).map((r,i)=>sourceMode==='books'?'<article class="atlas-source-card"><div class="atlas-source-kicker">'+e(r.era)+' · 文献</div><h2>'+e(r.title)+'</h2><p>'+e(r.imprint||r.publication||r.institution||'')+'</p><p>'+e(r.use||'书目入口；具体图版与使用范围见影像条目的原始出处。')+'</p><a target="_blank" rel="noopener noreferrer" href="'+e(r.url||r.sourceUrl)+'">查看文献出处 ↗</a></article>':'<article class="atlas-source-card"><div class="atlas-source-kicker">'+String(i+1).padStart(2,'0')+' / '+r.records.length+' 条影像</div><h2>'+e(r.name)+'</h2><p>'+e(r.eras.slice(0,5).join(' · '))+(r.eras.length>5?' 等':'')+'</p><div><button data-atlas-institution="'+e(r.name)+'">查看相关图像 →</button><a target="_blank" rel="noopener noreferrer" href="'+e(r.url)+'">来源示例 ↗</a></div></article>').join('')||'<p class="atlas-no-results">没有匹配的来源。请缩短关键词或更换机构名称。</p>';
  if(sourceMode==='books'&&!term)q('#atlasSourceGrid').insertAdjacentHTML('afterbegin','<article class="atlas-source-card atlas-source-special"><span>专题文献目录</span><h2>商代与西周</h2><p>发掘报告、图录与铭文资料按专题保存。</p><div><a href="shang.html#literature">商代文献 ↗</a><a href="western-zhou.html#literature">西周文献 ↗</a><a href="spring-autumn.html#literature">春秋诸国资料 ↗</a></div></article>');
  q('#atlasSourcesMore').hidden=methodOn||list.length<=sourceLimit;
  }
 function renderExpansion(){
  if(!expansionPlan)return;
  const fmt=n=>Number(n).toLocaleString('zh-CN');
  const current=records.length,target=expansionPlan.targetTotal,remaining=Math.max(target-current,0);
  q('#expansionCurrent').textContent=fmt(current);
  q('#expansionTarget').textContent=fmt(target);
  q('#expansionRemaining').textContent=fmt(remaining);
  q('#expansionProgressBar').style.width=Math.min(100,current/target*100).toFixed(2)+'%';
  q('#expansionProgressNote').textContent='现有目录规模 '+(current/target*100).toFixed(1)+'%（未完成全库质量复核） · '+records.filter(r=>r.openLicense).length.toLocaleString('zh-CN')+' 张标记为开放许可 · '+records.filter(r=>!r.openLicense).length.toLocaleString('zh-CN')+' 张仍需按来源政策核实 · '+new Set(records.map(r=>r.institution)).size.toLocaleString('zh-CN')+' 家来源机构';
  q('#expansionGroups').innerHTML=expansionPlan.groups.map((group,index)=>{
   const count=records.filter(r=>group.eras.includes(r.era)).length,needed=Math.max(group.target-count,0),ratio=Math.min(100,count/group.target*100);
   return '<article class="expansion-group"><div class="expansion-group-head"><span class="expansion-index">'+String(index+1).padStart(2,'0')+'</span><div><h2>'+e(group.name)+'</h2><p>'+e(group.eras.join(' · '))+'</p></div><strong>'+fmt(count)+' <small>/ '+fmt(group.target)+'</small></strong></div><div class="expansion-bar"><span style="width:'+ratio.toFixed(2)+'%"></span></div><div class="expansion-group-foot"><span>现有目录 '+fmt(count)+' 张</span><b>'+ (needed ? '待补 '+fmt(needed)+' 张' : '已达到配额') +'</b></div><p class="expansion-group-note">'+e(group.note)+'</p></article>';
  }).join('');
 }
  q('#atlasSourceSearch').addEventListener('input',()=>{sourceLimit=18;renderSources()});
 q('#exportAll').onclick=()=>exportRecords(records,'完整目录');
  renderSources();
  renderExpansion();
 q('#timelinePanel .eyebrow').textContent='HISTORICAL INDEX';
 q('#timelinePanel .lead').textContent='沿历史顺序进入资料库，或直接搜索朝代、执政者与年号。';
 q('#timelinePanel .notice').textContent='数字表示主库影像记录。并行政权、文化分期与宽断代分别保留；资料数量不代表历史重要性。';
 q('#timelineGroups').before(Object.assign(document.createElement('div'),{className:'atlas-index-tools',innerHTML:'<label class="atlas-directory-search"><span>⌕</span><input id="atlasIndexSearch" type="search" aria-label="搜索历代索引" placeholder="搜索朝代、执政者或年号，如：唐、李世民、贞观"></label><span id="atlasIndexCount"></span>'}));
 function renderIndex(){
  const term=q('#atlasIndexSearch').value.trim(),norm=ChronologyCore.normalize(term).toLowerCase();
  const visible=periods.map((p,i)=>({p,i,entries:window.CHRONOLOGY_DATA.entries.filter(x=>x.parentEra===p.name&&(!norm||ChronologyCore.normalize([x.ruler,x.reign,x.aliases].join(' ')).toLowerCase().includes(norm)))})).filter(({p,entries})=>!term||ChronologyCore.normalize(p.name).toLowerCase().includes(norm)||entries.length);
  q('#atlasIndexCount').textContent=visible.length+' 个历史分组';
  q('#timelineGroups').innerHTML=visible.map(({p,i,entries})=>{const count=records.filter(r=>r.era===p.name).length;return '<article class="atlas-index-card"><span class="atlas-index-number">'+String(i+1).padStart(2,'0')+'</span><div><h2>'+e(p.name)+'</h2><p>'+count+' 条影像 · '+window.CHRONOLOGY_DATA.entries.filter(x=>x.parentEra===p.name).length+' 条纪年索引</p></div><button class="atlas-index-open" data-era="'+e(p.name)+'" aria-label="浏览'+e(p.name)+'影像">↗</button><div class="atlas-index-tags">'+(term?entries.slice(0,6).map(n=>'<button data-chronology="'+e(n.id)+'">'+e(n.ruler+' · '+n.reign)+'</button>').join(''):p.polities.slice(0,4).map(n=>'<span>'+e(n)+'</span>').join(''))+'</div>'+(eraLinks[p.name]?'<a class="atlas-index-extra" href="'+eraLinks[p.name].url+'">专题资料与文献 →</a>':'')+'</article>'}).join('')||'<p class="atlas-no-results">没有找到匹配的朝代或纪年。</p>';
 }
 q('#atlasIndexSearch').addEventListener('input',renderIndex);renderIndex();
 function applyRoute(hash){
   if(hash==='#timeline'){setView('timeline',false);history.replaceState(null,'',hash)}
   else if(hash==='#expansion'){setView('expansion',false);history.replaceState(null,'',hash)}
  else if(hash==='#sources'){setView('standards',false);history.replaceState(null,'',hash)}
  else if(hash==='#tangReignDossier'||hash==='#xixiaReignDossier'){selectEra(hash.startsWith('#tang')?'唐':'西夏',null,false);pane='reigns';sync();history.replaceState(null,'',hash);requestAnimationFrame(()=>q('#explore').scrollIntoView())}
  else if(hash==='#tang-evidence'){selectEra('唐',null,false);pane='topics';sync();history.replaceState(null,'',hash);requestAnimationFrame(()=>q('#tang-evidence').scrollIntoView())}
  else if(/Reading|Books|Sources/.test(hash)){pane='reading';sync()}
 }
 window.addEventListener('hashchange',()=>applyRoute(location.hash));
 window.addEventListener('load',()=>{if(['#tangReignDossier','#xixiaReignDossier'].includes(initialHash))requestAnimationFrame(goToResults)},{once:true});
 renderCards();applyRoute(initialHash);sync();
})();
