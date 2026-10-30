function xixiaLink(url,label='查看核验依据 ↗'){
 if(!url)return '';
 try{if(!['https:','http:'].includes(new URL(url).protocol))return '';}catch{return '';}
 return '<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+'</a>';
}
function xixiaResearchCard(b){
 return '<article class="research-card"><div class="research-kicker">'+esc(b.kind||b.category||'研究线索')+(b.priority?' · '+esc(b.priority):'')+'</div><h3>'+esc(b.title)+'</h3>'+(b.imprint?'<p>'+esc(b.imprint)+'</p>':'')+'<span class="research-status">'+esc(b.status||'已核公开资料')+'</span>'+(b.use?'<p><b>参考用途</b> '+esc(b.use)+'</p>':'')+(b.notes?'<p>'+esc(b.notes)+'</p>':'')+(b.description?'<p>'+esc(b.description)+'</p>':'')+(b.blocker?'<p><b>待核原因</b> '+esc(b.blocker)+'</p>':'')+(b.nextStep?'<p><b>续查路径</b> '+esc(b.nextStep)+'</p>':'')+(b.bibliography||[]).map(s=>'<p>'+esc(s.title)+' · '+esc(s.publication)+'</p>').join('')+xixiaLink(b.url)+(b.additionalSources||[]).map(s=>'<div>'+xixiaLink(s.url,s.title+' ↗')+'</div>').join('')+'</article>';
}
function renderXixiaReading(){
 const x=window.ARCHIVE_DATA.xixia||{};
 const query=($('#xixiaResearchSearch')?.value||'').trim().toLowerCase();
 const matches=b=>!query||JSON.stringify(b).toLowerCase().includes(query);
 const bib=(x.bibliography||[]).filter(matches),media=(x.media||[]).filter(matches),leads=(x.leads||[]).filter(matches);
 $('#xixiaBibliography').innerHTML=bib.map(xixiaResearchCard).join('')||'<p>没有匹配的书目或史料。</p>';
 $('#xixiaMedia').innerHTML=media.map(xixiaResearchCard).join('')||'<p>没有匹配的现代影像参考。</p>';
 $('#xixiaLeads').innerHTML=leads.map(xixiaResearchCard).join('')||'<p>没有匹配的待核线索。</p>';
 $('#xixiaResearchCount').textContent='当前显示 '+bib.length+' 项书目／史料、'+media.length+' 项现代影像、'+leads.length+' 项待核或关联资料。';
}
function initXixia(){
 const x=window.ARCHIVE_DATA.xixia||{},list=records.filter(r=>r.era==='西夏');
 $('#xixiaStats').innerHTML=[['条生活场景图',list.filter(r=>r.lifeFocus).length],['条西夏影像',list.length],['个生活场景',7],['项书目与史料',(x.bibliography||[]).length]].map(([label,n])=>'<span><b>'+n+'</b>'+label+'</span>').join('');
 const descriptions=['供养人、侍从、木俑与甲片','瓷器、金银饰、工具与生产场景','陵园、石窟与出土建筑构件','碑铭、经卷、契约、符牌与纹饰'];
 $('#xixiaCategories').innerHTML=(x.categories||[]).map((c,i)=>'<button data-xixia-category="'+esc(c)+'"><small>0'+(i+1)+'</small><strong>'+esc(c)+'</strong><span>'+esc(descriptions[i])+'</span><b>'+list.filter(r=>r.category===c).length+' 条影像 ↗</b></button>').join('');
 $('#xixiaDatePolicy').textContent=x.datePolicy||'';
 $('#xixiaCategoryPolicy').textContent=x.categoryPolicy||'';
 $('#xixiaPriorities').innerHTML=(x.priorities||[]).map((p,i)=>'<article><span>0'+(i+1)+'</span><div><h3>'+esc(p.title)+'</h3><p>'+esc(p.route)+'</p><small>'+esc(p.boundary)+'</small></div></article>').join('');
 $('#xixiaCorrections').innerHTML=(x.corrections||[]).filter(c=>c.text).map(c=>'<li><strong>'+esc(c.title)+'</strong><p>'+esc(c.text)+'</p>'+xixiaLink(c.url)+'</li>').join('');
 $('#xixiaInstitutions').innerHTML=(x.institutions||[]).map(m=>{
  const n=list.filter(r=>(m.terms||[m.name]).some(t=>r.institution.includes(t))).length;
  return '<article class="institution-card"><h3>'+esc(m.name)+'</h3><span class="research-status">'+(n?n+' 条馆藏／来源影像':'专题线索保留')+'</span><p>'+esc(m.notes)+'</p>'+xixiaLink(m.url,'查看机构／馆藏依据 ↗')+(n?'<button class="quiet" data-xixia-institution="'+esc(m.name)+'">筛选相关影像 →</button>':'')+'</article>';
 }).join('');
 $('#xixiaResearchSearch').addEventListener('input',renderXixiaReading);
 $('#xixiaExport').onclick=()=>{download(JSON.stringify({title:'中华文明影像库·西夏专题资料包',version:window.ARCHIVE_DATA.version,count:list.length,records:list,research:x},null,2),'中华文明影像库-西夏专题完整资料包.json');toast('已导出西夏影像、书目、机构、考据和待核线索。')};
 initXixiaLife();
 renderXixiaReading();
}
document.addEventListener('click',e=>{
 const b=e.target.closest('button');if(!b)return;
 if(b.dataset.xixiaCategory){reset();state.lifeScene='all';state.socialGroup='all';state.category=b.dataset.xixiaCategory;renderCards();$('#explore').scrollIntoView({behavior:'smooth'});}
 if(b.dataset.xixiaInstitution){reset();state.lifeScene='all';state.socialGroup='all';state.institution=b.dataset.xixiaInstitution;renderCards();$('#explore').scrollIntoView({behavior:'smooth'});}
});

function initXixiaLife(){
 const x=window.ARCHIVE_DATA.xixia.life||{},list=records.filter(r=>r.era==='西夏');
 const picks=['xixia-wuwei-daliu-horse-handler',...list.filter(r=>r.addedIn&&/酿酒|牛耕|水月观音/.test(r.title)).map(r=>r.id)].slice(0,3).map(id=>list.find(r=>r.id===id)).filter(Boolean);
 $('#xixiaLifeSpotlight').innerHTML=picks.map(r=>'<button data-detail="'+esc(r.id)+'"><img src="'+esc(r.imageUrl)+'" alt="'+esc(r.title)+'" referrerpolicy="no-referrer"><span><small>'+esc((r.lifeScenes||[])[0]||r.category)+'</small><strong>'+esc(r.title)+'</strong><em>查看原图与可参考细节 ↗</em></span></button>').join('');
 const captions=['衣领、发式、束腰与持物','耕作、粮食加工、酿造与制陶','照明、炊煮、盛食与梳洗','家具结构、房址与作坊布局','牵马、携行与驿传','乐舞人物、仪式与供养','书写、称量与凭证'];
 $('#xixiaSceneCards').innerHTML=(x.scenes||[]).map((s,i)=>'<button data-life-scene="'+esc(s)+'"><small>0'+(i+1)+'</small><strong>'+esc(s)+'</strong><span>'+captions[i]+'</span><b>'+list.filter(r=>r.lifeScenes?.includes(s)).length+' 条参考 →</b></button>').join('');
 $('#xixiaLifeBoundary').textContent=x.boundary||'';$('#xixiaLifeGaps').textContent=x.gaps||'';
 $('#xixiaRemoteSources').innerHTML=(x.remoteOnly||[]).map(r=>'<article class="research-card"><span class="research-status">已核馆方图文 · 原站查看</span><h3>'+esc(r.title)+'</h3><p>'+esc(r.date)+' · '+esc(r.institution)+'</p><p>'+esc(r.description||r.sceneUse||'')+'</p><p>'+esc((r.visibleDetails||[]).join('；'))+'</p><p>'+esc(Array.isArray(r.reconstructionLimits)?r.reconstructionLimits.join('；'):r.reconstructionLimits||r.notes)+'</p>'+xixiaLink(r.sourceUrl,'馆方著录与图注 ↗')+' · '+xixiaLink(r.imageUrl,'打开原图 ↗')+'</article>').join('');
 handleImageErrors($('#xixiaLifeSpotlight'));
}
function renderXixiaLifeFilters(){
 if(!$('#xixiaLifeFilters'))return;
 const life=window.ARCHIVE_DATA.xixia.life||{},list=records.filter(r=>r.era==='西夏'&&chronoMatches(r));
 const groups=[...new Set(list.flatMap(r=>r.socialGroups||[]))];
 $('#xixiaLifeFilters').innerHTML='<div class="life-filter-row"><span>场景</span>'+[['life','生活场景'],['all','全部西夏'],...(life.scenes||[]).map(s=>[s,s])].map(([id,label])=>'<button data-life-scene="'+esc(id)+'" class="'+(state.lifeScene===id?'selected':'')+'" aria-pressed="'+(state.lifeScene===id)+'">'+esc(label)+'</button>').join('')+'</div><div class="life-filter-row"><span>人物</span>'+['all',...groups].map(g=>'<button data-life-group="'+esc(g)+'" class="'+(state.socialGroup===g?'selected':'')+'" aria-pressed="'+(state.socialGroup===g)+'">'+esc(g==='all'?'全部角色':g)+'</button>').join('')+'</div><div class="life-filter-row"><span>断代</span>'+[['all','保留全部原始断代'],['bounded','隐藏跨1227年项']].map(([v,t])=>'<button data-life-dating="'+v+'" class="'+(state.lifeDating===v?'selected':'')+'" aria-pressed="'+(state.lifeDating===v)+'">'+t+'</button>').join('')+'</div><p>人物标签只标有依据的角色；日用器物不据材质臆定使用者阶层。</p>';
}
function xixiaLifeDetail(r){
 if(!r.lifeFocus)return '';
 const arr=v=>Array.isArray(v)?v:[v];
 return '<section class="detail-section life-use"><div class="eyebrow">FOR COSTUME · PROPS · SET DESIGN</div><h3>这张图，能用于什么场次</h3><p class="life-detail-tags">'+esc((r.lifeScenes||[]).join(' · '))+'</p>'+(r.socialGroups?.length?'<p><b>人物角色：</b>'+esc(r.roleDescription||r.socialGroups.join('、'))+'</p>':'')+(r.sceneUse?'<p>'+esc(r.sceneUse)+'</p>':'')+'<h4>原图中可核对</h4><ul>'+(r.visibleDetails||[]).map(d=>'<li>'+esc(d)+'</li>').join('')+'</ul>'+(r.reconstructionLimits?'<h4>需要另证</h4><p>'+esc(arr(r.reconstructionLimits).join('；'))+'</p>':'')+'</section>';
}
document.addEventListener('click',e=>{
 const b=e.target.closest('button');if(!b)return;
 if(b.dataset.lifeScene){Object.assign(state,{lifeScene:b.dataset.lifeScene,socialGroup:'all',category:'all',institution:null,query:'',evidence:'all',limit:12});$('#search').value='';$('#evidenceFilter').value='all';renderCards();$('#explore').scrollIntoView({behavior:'smooth'});}
 if(b.dataset.lifeDating){state.lifeDating=b.dataset.lifeDating;state.limit=12;renderCards();}
 if(b.dataset.lifeGroup){state.socialGroup=b.dataset.lifeGroup;state.limit=12;renderCards();}
});
