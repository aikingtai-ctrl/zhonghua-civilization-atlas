/* Reign dossiers are evidence notes, never substitute image records. */
function renderXixiaReigns(node){
 let host=document.getElementById('xixiaReignDossier');
 if(!host){const drawer=document.createElement('details');drawer.id='xixiaDossierDrawer';drawer.className='visual-evidence-drawer';drawer.innerHTML='<summary><span>年号考据与出处</span><small>查看断代依据、人物身份与证据缺口</small></summary>';host=document.createElement('section');host.id='xixiaReignDossier';host.className='reign-dossier';drawer.append(host);document.getElementById('loadMore').after(drawer)}
 host.hidden=state.era!=='西夏';host.parentElement.hidden=host.hidden;if(host.hidden)return;
 const data=window.ARCHIVE_DATA.xixia.reigns;
 if(!data){host.hidden=true;return}
 const profiles=data.profiles||[], entries=window.CHRONOLOGY_DATA.entries.filter(e=>e.parentEra==='西夏');
 const profileFor=id=>profiles.find(p=>p.reignId===id);
 const counts=e=>chronologyIndex.count({...e,kind:'reign'},'contained');
 const navigation=e=>'<button class="reign-jump '+(node?.id===e.id?'selected':'')+'" data-chronology="'+esc(e.id)+'"><strong>'+esc(e.reign)+'</strong><span>'+esc(chronoYears(e.start,e.end))+'</span><small>'+counts(e)+' 条影像 · '+(profileFor(e.id)?'纪年档案':'待核')+'</small></button>';
 if(!node||node.kind==='undated'){
  const rulers=[...new Set(entries.map(e=>e.rulerId))];
  host.innerHTML='<div class="reign-heading"><div><div class="eyebrow">RULERS · REIGNS · EVIDENCE</div><h3>从景宗到末主，逐年号查找</h3></div><span class="reign-audit-count">10 位执政者 / 32 个年号</span></div><p class="reign-intro">每个年号都有独立的考据与美术参考说明。数字只统计可按年代归入的图像；跨期材料、文字线索和未定年图像分别保留。</p>'+(node?.kind==='undated'?'<p class="reign-context-note">你当前查看的是“断代待细分／待核”，并不是西夏末期。请从下方进入具体执政者和年号。</p>':'')+'<div class="reign-coverage">'+rulers.map(id=>{const rows=entries.filter(e=>e.rulerId===id),r=rows[0];return '<div class="reign-coverage-row"><button class="reign-ruler" data-chronology="ruler-'+esc(id)+'">'+esc(r.ruler)+'<span>查看执政者全部 →</span></button><div>'+rows.map(navigation).join('')+'</div></div>'}).join('')+'</div><p class="reign-footnote">献宗李德旺之后仍有末主李睍（宝义，1226–1227），已单独收录。景宗称帝以前的显道、开运、广运和大庆也保留。</p>';
  return;
 }
 const selected=node.kind==='ruler'?entries.filter(e=>e.rulerId===node.id.replace(/^ruler-/,'')):entries.filter(e=>e.id===node.id);
 if(!selected.length){host.hidden=true;return}
 const pos=entries.findIndex(e=>e.id===node.id);
 host.innerHTML='<div class="reign-heading"><div><div class="eyebrow">VISUAL RESEARCH · REIGN DOSSIER</div><h3>'+ (node.kind==='ruler'?'执政者分年号资料':'本年号的视觉美术参考')+'</h3></div><button class="quiet" data-chrono-reign-overview>年号总览 ↗</button></div>'+(node.kind==='ruler'?'<div class="reign-local-nav">'+selected.map(navigation).join('')+'</div>':'')+selected.map(e=>{
  const p=profileFor(e.id);if(!p)return '';
  const count=counts(e),sources=p.sources||[];
  return '<details class="reign-profile" '+(selected.length===1?'open':'')+'><summary><span>'+esc(e.reign)+' <small>'+esc(chronoYears(e.start,e.end))+'</small></span><b>'+count+' 条影像 · 纪年档案</b></summary><div class="reign-profile-body"><p class="reign-summary">'+esc(p.summary)+'</p><div class="reign-focus-grid">'+(p.visualFocus||[]).map(f=>'<article><h4>'+esc(f.category)+'</h4><p>'+esc(f.content)+'</p></article>').join('')+'</div>'+(p.leads?.length?'<div class="reign-text-leads"><h4>相关文献</h4><ul>'+p.leads.map(l=>'<li>'+(typeof l==='string'?esc(l):'<strong>'+esc(l.title)+'</strong> '+esc(l.note||l.description||'')+(l.url?' '+xixiaLink(l.url,'出处 ↗'):''))+'</li>').join('')+'</ul></div>':'')+(p.gaps?.length?'<p class="reign-gap"><strong>仍缺的直接证据</strong> '+esc(p.gaps.join('；'))+'</p>':'')+'<div class="reign-sources"><h4>原始出处</h4>'+sources.map(s=>'<p>'+xixiaLink(s.url,s.title+' ↗')+(s.note?'<small>'+esc(s.note)+'</small>':'')+'</p>').join('')+'</div>'+(selected.length>1?'<button class="secondary" data-chronology="'+esc(e.id)+'">进入'+esc(e.reign)+'影像 →</button>':'')+'</div></details>';
 }).join('')+xixiaContextCards(node)+(pos>=0?'<nav class="reign-adjacent" aria-label="相邻年号">'+(pos>0?'<button data-chronology="'+esc(entries[pos-1].id)+'">← '+esc(entries[pos-1].ruler.split(' · ')[0]+' · '+entries[pos-1].reign)+'</button>':'<span></span>')+(pos<entries.length-1?'<button data-chronology="'+esc(entries[pos+1].id)+'">'+esc(entries[pos+1].ruler.split(' · ')[0]+' · '+entries[pos+1].reign)+' →</button>':'')+'</nav>':'');
 handleImageErrors(host);
}
function xixiaContextCards(node){
 const list=records.filter(r=>chronologyIndex.match(r,node,'context'));if(!list.length)return '';
 return '<section class="reign-context-images"><h4>创建或编刊关联 · '+list.length+' 条</h4><p>以下文献入口用于追索地点或作品，未计入本年号的确定断代影像。创建年份不代表现状建筑，初刊年份不代表每一张残叶的刷印年份。</p><div>'+list.map(r=>'<p><strong>'+esc(r.title)+'</strong> · '+esc(r.date)+'<br>'+xixiaLink(r.sourceUrl,'仅查阅关联文献出处 ↗')+'</p>').join('')+'</div></section>';
}
document.addEventListener('click',e=>{if(e.target.closest('[data-chrono-reign-overview]')){selectEra('西夏');document.getElementById('xixiaDossierDrawer').open=true;document.getElementById('xixiaReignDossier').scrollIntoView({block:'start',behavior:'smooth'})}});
