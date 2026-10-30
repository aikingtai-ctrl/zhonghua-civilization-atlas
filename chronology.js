function renderSuiChronologyLinks(){return '<a class="chron-option whole" href="sui.html">隋代七期专属图库 ↗</a>'+ (window.ARCHIVE_DATA.sui?.periods||[]).map(p=>'<a class="chron-option" href="sui.html#chapter='+p.id+'"><span>'+esc(p.label)+'<small>'+esc(p.years)+' · 3组场景参考</small></span><span>↗</span></a>').join('')}
let chronologyIndex,chronologyNodes=new Map(),chronologyGroups=[],chronologySearch='',chronologyOpen=new Set(),chronologySavedOpen=null;
const chronoYears=(a,b)=>ChronologyCore.years(a,b);
function initChronology(){
 const data=window.CHRONOLOGY_DATA;
 chronologyIndex=ChronologyCore.create(data,records);
 chronologyGroups=periods.map((p,index)=>{
  const entries=data.entries.filter(e=>e.parentEra===p.name).map(e=>({...e,kind:e.kind||'reign',label:e.reign}));
  entries.forEach(e=>chronologyNodes.set(e.id,e));
  const polities=[...new Set([...p.polities,...entries.map(e=>e.polity).filter(Boolean)])].map((polity,pi)=>{
   const rows=entries.filter(e=>(e.polity||p.name)===polity),rulers=[];
   for(const id of [...new Set(rows.map(e=>e.rulerId))]){
    const es=rows.filter(e=>e.rulerId===id).sort((a,b)=>a.displayOrder!==undefined&&b.displayOrder!==undefined?a.displayOrder-b.displayOrder:(a.start??0)-(b.start??0)),first=es[0];
    const dated=es.filter(e=>typeof e.start==='number'&&typeof e.end==='number');
    const n={id:'ruler-'+id,kind:'ruler',parentEra:p.name,polity:polity===p.name?null:polity,ruler:first.ruler,label:first.ruler,start:dated.length?Math.min(...dated.map(e=>e.start)):null,end:dated.length?Math.max(...dated.map(e=>e.end)):null,entries:es};
    if(es.every(e=>e.recordIds))n.recordIds=[...new Set(es.flatMap(e=>e.recordIds))];
    const qin=(window.ARCHIVE_DATA.qin?.rulers||[]).find(r=>r.nodeId===n.id);if(qin)Object.assign(n,{recordIds:qin.recordIds,qinRulerId:qin.id,label:qin.name,ruler:qin.name});
    chronologyNodes.set(n.id,n);rulers.push(n);
   }
   rulers.sort((a,b)=>(a.start??-9999)-(b.start??-9999));
   return {id:'polity-'+index+'-'+pi,name:polity,rulers};
  });
  const undated={id:'undated-'+index,kind:'undated',parentEra:p.name,label:'断代待细分／待核',dateText:'未能归入具体纪年 · 不代表末期'};chronologyNodes.set(undated.id,undated);
  return {id:'era-'+index,name:p.name,polities,undated,note:data.eraNotes?.[p.name]||''};
 });
 chronologyNodes.set('qin-all',{id:'qin-all',kind:'collection',parentEra:'秦',label:'秦代全部图像',recordIds:records.filter(r=>r.era==='秦').map(r=>r.id)});
 if(state.era!=='all'){const g=chronologyGroups.find(g=>g.name===state.era);if(g)chronologyOpen.add(g.id)}
 $('#chronologySearch').addEventListener('input',e=>{const q=e.target.value.trim();if(q&&!chronologySearch)chronologySavedOpen=new Set(chronologyOpen);if(!q&&chronologySavedOpen){chronologyOpen=chronologySavedOpen;chronologySavedOpen=null}chronologySearch=q;renderChronology();$('#chronologyScroll').scrollTop=0});
 $('#eraList').addEventListener('toggle',e=>{const id=e.target.dataset.branch;if(!id||chronologySearch)return;e.target.open?chronologyOpen.add(id):chronologyOpen.delete(id)},true);
 $('#collapseChronology').onclick=()=>{chronologySearch='';$('#chronologySearch').value='';chronologySavedOpen=null;chronologyOpen.clear();renderChronology()};
 $('#toggleChronology').onclick=()=>{const opened=$('.sidebar').classList.toggle('mobile-open');$('#toggleChronology').textContent=opened?'收起目录':'展开目录';$('#toggleChronology').setAttribute('aria-expanded',String(opened))};
 $('#chronologySources').onclick=showChronologySources;
 $('#closeChronologySources').onclick=()=>$('#chronologySourceDialog').close();
 $('#chronologySourceDialog').addEventListener('click',e=>{if(e.target===$('#chronologySourceDialog'))e.target.close()});
 renderChronology();
}
function chronoSearchMatch(e,q){
 if(!q)return true;
 if(/^(?:公元)?(?:前|-)?\d{1,4}年?$/.test(q)){const y=Number(q.replace('公元','').replace('前','-').replace('年',''));return typeof e.start==='number'&&typeof e.end==='number'&&y>=e.start&&y<=e.end}
 return ChronologyCore.normalize([e.parentEra,e.polity,e.ruler,e.reign,e.originalRuler,e.originalReign,e.aliases,...(e.searchAliases||[])].join(' ')).toLowerCase().includes(ChronologyCore.normalize(q).toLowerCase());
}
function chronoOption(node,label=node.label,whole=false){
 const count=chronologyIndex.count(node,'contained'),chosen=state.chronoId===node.id,hasTangDossier=[window.ARCHIVE_DATA.tang?.reigns,window.ARCHIVE_DATA.xixia?.reigns].some(d=>d?.profiles.some(p=>p.reignId===node.id));
 return '<button class="chron-option '+(whole?'whole ':'')+(chosen?'selected':'')+'" data-chronology="'+esc(node.id)+'" aria-pressed="'+chosen+'"><span>'+esc(label)+'<small>'+esc(node.dateLabel||chronoYears(node.start,node.end)||node.dateText||'起止未定')+(node.certainty==='secondary-chronology'?' · 补充年表':'')+'</small></span><span class="chron-count">'+(node.parentEra==='唐'?count+' 图':count?count+' 图':hasTangDossier?'纪年档案':'待补充')+'</span></button>';
}
function renderChronology(){
 if(!chronologyIndex)return;
 const q=chronologySearch, groups={'史前':'文明起源','秦':'统一与分合','隋':'隋唐与五代','辽':'宋辽金夏 · 并行政权','元':'元明清'};
 const html=chronologyGroups.map(g=>{
  const rootMatch=!!q&&ChronologyCore.normalize(g.name).includes(ChronologyCore.normalize(q));
  const visible=g.polities.map(p=>({...p,rulers:p.rulers.map(r=>({...r,visibleEntries:r.entries.filter(e=>rootMatch||chronoSearchMatch(e,q))})).filter(r=>r.visibleEntries.length)}));
  const any=visible.some(p=>p.rulers.length);
  if(q&&!rootMatch&&!any)return '';
  const count=records.filter(r=>r.era===g.name).length;
  const branch=visible.filter(p=>p.rulers.length).map(p=>{
   const body=p.rulers.map(r=>'<details class="chron-ruler" data-branch="'+esc(r.id)+'" '+(q||chronologyOpen.has(r.id)?'open':'')+'><summary><button class="ruler-name chron-select-name" data-chronology="'+esc(r.id)+'" aria-pressed="'+(state.chronoId===r.id)+'">'+esc(r.ruler)+'</button><small>'+esc(chronoYears(r.start,r.end).replace('年',''))+'</small></summary><div class="chron-reigns">'+chronoOption(r,'此执政者全部',true)+r.visibleEntries.map(e=>chronoOption(e,e.reign+(e.inherited?' · 沿用':''))).join('')+'</div></details>').join('');
   if(g.polities.length===1)return body;
   return '<details class="chron-polity" data-branch="'+p.id+'" '+(q||chronologyOpen.has(p.id)?'open':'')+'><summary>'+esc(p.name)+'</summary><div class="chron-children"><button class="chron-option whole" data-chrono-polity="'+esc(p.name)+'" data-chrono-era="'+esc(g.name)+'">全部'+esc(p.name)+' →</button>'+body+'</div></details>';
  }).join('');
  return (groups[g.name]?'<div class="chron-group">'+groups[g.name]+'</div>':'')+'<details class="chron-branch '+(state.era===g.name?'active':'')+'" data-branch="'+g.id+'" '+(q||chronologyOpen.has(g.id)?'open':'')+'><summary><button class="chron-name chron-select-name" data-era="'+esc(g.name)+'">'+esc(g.name==='夏／二里头文化'?'夏 · 二里头':g.name)+'</button><span class="chron-total">'+count+' 图</span></summary><div class="chron-children"><button class="chron-option whole '+(state.era===g.name&&!state.chronoId&&!state.polity?'selected':'')+'" data-era="'+esc(g.name)+'">全部'+esc(g.name)+'资料 <span>→</span></button>'+(g.name==='战国'?'<a class="chron-option whole" href="warring-states.html">战国各国专属图库 ↗</a>':'')+(g.name==='隋'?renderSuiChronologyLinks():'')+(g.name==='东汉'?'<a class="chron-option whole" href="eastern-han.html">东汉七期专属图库 ↗</a>':'')+(g.note?'<p class="chron-note">'+esc(g.note)+'</p>':'')+(g.name==='西汉'?'<a class="chron-option whole" href="western-han.html">西汉六期专属图库 ↗</a>':'')+(g.name==='秦'?'<a class="chron-option whole" href="qin.html">秦代五期专属图库 ↗</a>':'')+(g.name==='西夏'?chronoOption(g.undated,g.undated.label):'')+(g.name==='唐'&&typeof renderTangChronologyExtras==='function'?renderTangChronologyExtras(g):'')+branch+(!any?'<p class="chron-note">本组的执政者与纪年资料仍待核补；现有影像可从本朝全部资料查看。</p>':'')+(g.name==='西夏'?'':chronoOption(g.undated,g.undated.label))+'</div></details>';
 }).join('');
 $('#eraList').innerHTML=html||'<p class="chron-no-results">没有找到该朝代、执政者或年号。<br>可试试“开元”“仁宗”或“1200”。</p>';
 $('#chronologyAll').classList.toggle('selected',state.era==='all');
 $('#chronologyStatus').textContent=q?'已筛选目录 · 清空搜索可恢复全部':'点击名称筛选图像 · 点击箭头展开年号';
}
function syncChronology(){
 if(!chronologyIndex)return;
 const node=chronologyNodes.get(state.chronoId)||(state.chronoId?{id:state.chronoId,kind:'invalid',label:'无法识别的历史范围',parentEra:'请重新选择目录'}:null),selected=$('#chronologySelection');
 if(typeof renderTangReigns==='function')renderTangReigns(node);
 if(typeof renderXixiaReigns==='function')renderXixiaReigns(node);
 selected.hidden=!node;
 if(node){
  const path=[node.parentEra,node.polity&&node.polity!==node.parentEra?node.polity:null,node.kind!=='ruler'?node.ruler:null].filter(Boolean);
  $('#chronologyBreadcrumb').textContent=path.join(' / ');
  $('#chronologyCurrent').textContent=node.label+(chronoYears(node.start,node.end)?' · '+chronoYears(node.start,node.end):'');
  const strict=chronologyIndex.count(node,'contained');
  $('#chronologyMatchNote').textContent=node.kind==='invalid'?'此链接的时期不存在，已停止显示图像。请从左侧重新选择有效的执政者或年号。':node.kind==='undated'?'本栏收纳宽断代、同年改元待辨、载体差异或其他待核材料；不是朝代末期。每图保留原始断代与待定原因。':node.recordIds?'按馆藏著录的文化分期、君主或王年关联；未补写不确定的公元年份。':'本范围共 '+strict+' 张有归属依据的图像。主题与关键词只在本范围内进一步筛选；跨期、同年改元未辨及仅有背景关联的图像不混入。';
  if(node.indexOnly)$('#chronologyMatchNote').textContent='本条为年号归属说明索引，不自动分配805年图像；请阅读下方传位与追改纪年的说明。';
  $('#chronologySelectedSource').innerHTML=(node.sourceUrl?'<a href="'+esc(node.sourceUrl)+'" target="_blank" rel="noopener noreferrer">'+(node.certainty==='secondary-chronology'?'补充年表 · 待核专著':'查看纪年出处')+' ↗</a>':'')+(node.note||node.notes?'<span> '+esc(node.note||node.notes)+'</span>':'');
  $('#chronologyModes').hidden=true;
  $$('[data-chronology-mode]').forEach(b=>{const s=b.dataset.chronologyMode===state.chronoMode;b.classList.toggle('selected',s);b.setAttribute('aria-pressed',String(s))});
  $('#empty h3').textContent='该范围暂无符合条件的影像';
  $('#empty p').textContent='清除主题或关键词可恢复本范围全部结果；若仍为空，表示尚无可确证归入本期的图像。可明确返回本朝全部资料继续查阅。';
 }else{$('#empty h3').textContent='没有符合条件的影像';$('#empty p').textContent='尝试减少筛选条件，或查看该时期的待补充目录。'}
 $$('#eraList [data-chronology]').forEach(b=>{const s=b.dataset.chronology===state.chronoId;b.classList.toggle('selected',s);b.setAttribute('aria-pressed',String(s))});
 $$('#eraList .chron-branch').forEach(b=>{const g=chronologyGroups.find(g=>g.id===b.dataset.branch);b.classList.toggle('active',g?.name===state.era)});
 $$('#eraList [data-era]').forEach(b=>b.classList.toggle('selected',b.dataset.era===state.era&&!state.chronoId&&!state.polity));
}
function chronoMatches(record){return !state.chronoId||chronologyIndex.match(record,chronologyNodes.get(state.chronoId),state.era==='唐'?state.chronoMode:'contained')}
function chronoCardNote(record){
 const node=chronologyNodes.get(state.chronoId);if(!node)return '';
 const d=chronologyIndex.dates.get(record.id);
 const label=node.parentEra==='唐'&&state.chronoMode==='overlap'&&!chronologyIndex.match(record,node)?'跨期参考 · 不确定归属本期':node.parentEra==='唐'&&state.chronoMode==='context'?'历史关联 · 非本期原物':node.kind==='undated'?chronologyIndex.reason(record):'归入：'+[node.ruler,node.kind==='ruler'?null:node.label].filter(Boolean).join(' · ');
 return '<p class="chron-match" title="'+esc(chronologyIndex.explain(record,node))+'">'+label+'</p>';
}
function selectChronology(id,scroll=true){
 const node=chronologyNodes.get(id);if(!node){state.view='library';reset();state.chronoId=id;state.era='all';setView('library',false);renderChronology();renderCards();history.replaceState(null,'','#period='+encodeURIComponent(id));return}
 selectEra(node.parentEra,node.polity||null,false);
 state.chronoId=id;state.chronoMode='contained';state.limit=12;
 const group=chronologyGroups.find(g=>g.name===node.parentEra);chronologyOpen.add(group.id);
 group.polities.forEach(p=>{const r=p.rulers.find(r=>r.id===id||r.entries.some(e=>e.id===id));if(r){chronologyOpen.add(p.id);chronologyOpen.add(r.id)}});
 renderChronology();renderCards();history.replaceState(null,'','#period='+encodeURIComponent(id));
 if(scroll)scrollToChronologyResults();
}
function scrollToChronologyResults(){if(matchMedia('(max-width:760px)').matches){$('.sidebar').classList.remove('mobile-open');$('#toggleChronology').textContent='展开目录';$('#toggleChronology').setAttribute('aria-expanded','false')}window.scrollTo({top:window.scrollY+$('#explore').getBoundingClientRect().top-($('.header')?.offsetHeight||80)-18,behavior:'instant'})}
function showChronologySources(){
 const d=window.CHRONOLOGY_DATA;
 $('#chronologySourceContent').innerHTML='<div class="eyebrow">CHRONOLOGY · SOURCES</div><h2>纪年目录与筛选依据</h2><p>本目录覆盖 '+periods.length+' 个历史分组、'+d.entries.length+' 个年号或纪年条目。各条目用于寻找图像，不表示本库已拥有该时段的影像。</p><ul>'+(d.sources||[]).map(s=>'<li><a href="'+esc(s.url)+'" target="_blank" rel="noopener noreferrer">'+esc(s.title)+' ↗</a><br>'+esc(s.note||'')+'</li>').join('')+'</ul><div class="chron-policy"><strong>怎样理解筛选结果</strong><p>朝代、并行政权、执政者与年号分别记录。部分执政者沿用前任或其他政权年号，目录注明“沿用”；执政者旁的年份是本表所收纪年的覆盖范围，不是生卒年份。</p><p>时期检索只显示有归属依据的图像。宽断代不按交集分配，同年改元无法区分者不自动落入年号；背景关联及后世载体单列待核。无法细分的资料列入“断代待细分／待核”，原始图像仍完整保留。</p><p>公元前不设零年。先秦使用文化分期、君主或王年。现存建筑、墓葬、出版及拍摄的年份分别理解；筛选不改变原始著录。</p></div><p>'+esc(d.coverageNote||'')+'</p><p>年号数据整理与简体显示依据法鼓文理学院时间规范数据库，按 <a href="https://creativecommons.org/licenses/by-sa/3.0/" target="_blank" rel="noopener noreferrer">CC BY-SA 3.0</a> 提供；本地转换和补校已标注。图像许可仍以各条目为准。</p><a class="secondary" href="chronology-data.json.gz" download>下载纪年与来源目录 ↓</a>';
 $('#chronologySourceContent').insertAdjacentHTML('beforeend','<p>地方政权补充年表来自维基百科，采用 CC BY-SA 4.0。综合整理版按 CC BY-SA 4.0 提供；两套数据的来源、核验程度和原许可分别保留。</p>');
 $('#chronologySourceDialog').showModal();
}
document.addEventListener('click',e=>{
 const b=e.target.closest('button');if(!b)return;
 if(b.dataset.chronology){e.preventDefault();selectChronology(b.dataset.chronology);return}
 if(b.dataset.chronoPolity){selectEra(b.dataset.chronoEra,b.dataset.chronoPolity);return}
 if(b.dataset.chronologyMode){state.chronoMode=state.era==='唐'?b.dataset.chronologyMode:'contained';state.limit=12;renderCards();return}
 if(b.id==='clearChronology')selectEra(state.era,state.era==='唐'?null:state.polity);
});

function qinRulerInfo(node){return(window.ARCHIVE_DATA.qin?.rulers||[]).find(r=>r.id===node?.qinRulerId)}
function qinRulerLink(record,node=chronologyNodes.get(state.chronoId)){return(record.qinRulerLinks||[]).find(r=>r.id===node?.qinRulerId)}
function qinRulerRank(record){const link=qinRulerLink(record);return link?({direct:0,associated:1,context:2}[link.relation]??3):3}
function qinRulerDetail(record){if(record.era!=='秦')return '';return '<section class="detail-section"><h3>执政者分类与依据</h3>'+(record.qinRulerLinks||[]).map(link=>{const ruler=(window.ARCHIVE_DATA.qin?.rulers||[]).find(r=>r.id===link.id);return '<p><strong>'+esc(ruler?.name||link.id)+' · '+esc(link.label)+'</strong><br>'+esc(link.reason)+'</p>'}).join('')+'</section>'}
