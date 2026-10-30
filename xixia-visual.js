/* Images lead the browsing experience; evidence remains attached to each image. */
function xixiaObjectKey(r){return r.visualObjectId||r.id}
function xixiaVisualMatch(r,options={}){return state.era!=='西夏'||(xixiaSubcategoryMatch(r,options)&&(state.xixiaImageMode!=='objects'||!r.imageViewIndex)&&(state.xixiaScope!=='bounded'||(!r.crosses1227&&!r.dateDisputed&&!['conditional','later-comparison'].includes(r.visualScope))))}
function xixiaVisualRank(r){return (r.imageViewIndex?600:0)+({'服饰与人物':0,'建筑与空间':100,'器物与工艺':200,'纹样与文书':300}[r.category]??400)-((r.visualPriority||0)>=90?1000+r.visualPriority:r.visualPriority||0)}
function xixiaImageScope(r){return r.dateDisputed?'断代有争议':r.visualScope==='conditional'?'有条件参考':r.visualScope==='later-comparison'?'后世比较':r.crosses1227?'跨期参考':r.dateRelation&&r.dateRelation!=='object'?'创建／编刊关联':r.dateStart&&r.dateEnd?'有年代范围':'仅有朝代断代'}
function xixiaVisualCard(r){return '<article class="card xixia-card"><button class="card-picture" data-detail="'+esc(r.id)+'" aria-label="查看'+esc(r.title)+'的影像与出处"><img src="'+esc(r.localImage||r.previewUrl||r.imageUrl)+'" alt="'+esc(r.title)+'" loading="lazy" referrerpolicy="no-referrer"><span class="badge">'+esc(xixiaImageScope(r))+'</span></button><button class="save '+(saved.has(r.id)?'active':'')+'" data-save="'+esc(r.id)+'" aria-label="加入参考集：'+esc(r.title)+'">'+(saved.has(r.id)?'♥':'♡')+'</button><div class="card-body"><div class="card-kicker">'+esc(r.category)+'</div><button class="card-title" data-detail="'+esc(r.id)+'">'+esc(r.title)+'</button><p class="card-date">'+esc(r.date)+'</p>'+xixiaSubcategoryCaption(r)+'<p class="visual-unassigned">形制参考 · 未确定属于所选年号</p><div class="card-bottom"><span>'+esc(r.institutionShort||r.institution)+'</span><b>↗ 出处可查</b></div></div></article>'}
function renderXixiaVisual(){
 const active=state.era==='西夏';document.body.classList.toggle('xixia-visual-first',active);
 let tools=$('#xixiaVisualTools');if(!tools){tools=document.createElement('div');tools.id='xixiaVisualTools';tools.className='visual-tools';$('#chronologySelection').after(tools)}
 tools.hidden=!active;
 let scene=$('#xixiaSceneDrawer');if(!scene){scene=document.createElement('details');scene.id='xixiaSceneDrawer';scene.className='visual-scene-drawer';scene.innerHTML='<summary>场景、人物与断代筛选 <span>展开 ↓</span></summary>';$('#xixiaLifeFilters').before(scene);scene.append($('#xixiaLifeFilters'))}
 scene.hidden=!active;
 let support=$('#xixiaRelatedVisuals');if(!support){support=document.createElement('section');support.id='xixiaRelatedVisuals';support.className='visual-related';$('#loadMore').after(support)}
 support.hidden=true;support.innerHTML='';
 renderXixiaSubcategories();
 if(!active)return;
 const all=records.filter(r=>r.era==='西夏'&&chronoMatches(r)),objects=new Set(all.map(xixiaObjectKey)).size,node=chronologyNodes.get(state.chronoId),mode=state.xixiaImageMode||'images';
 tools.innerHTML='<div class="visual-total"><strong>'+all.length+'</strong> 张参考图像 <span>/ '+objects+' 个对象／图版组 · 当前历史范围</span></div><div class="visual-tools-actions"><button data-xixia-image-mode="images" class="'+(mode==='images'?'selected':'')+'">全部视图</button><button data-xixia-image-mode="objects" class="'+(mode==='objects'?'selected':'')+'">每件主图</button><button data-xixia-scope class="'+(state.xixiaScope==='bounded'?'selected':'')+'">'+(state.xixiaScope==='bounded'?'已排除跨期／争议 ✓':'排除跨期／争议')+'</button><button data-xixia-open-evidence>年号考据 ↗</button></div>';
 const label=$('#chronologyCurrent');if(node&&label){$('#resultsTitle').textContent='西夏 · '+node.label+' · 视觉美术参考'}
 const results=filtered();$('#resultCount').textContent=results.length+' 张图像 · '+new Set(results.map(xixiaObjectKey)).size+' 个对象／图版'+(node?' · 当前年代范围':'');
 const overview=$('#xixiaReading');if(overview)overview.classList.add('visual-reading');
}
document.addEventListener('click',e=>{
 const b=e.target.closest('button');if(!b)return;
 if(b.dataset.xixiaImageMode){state.xixiaImageMode=b.dataset.xixiaImageMode;state.limit=24;renderCards()}
 if(b.hasAttribute('data-xixia-scope')){state.xixiaScope=state.xixiaScope==='bounded'?'all':'bounded';state.limit=24;renderCards()}
 if(b.hasAttribute('data-xixia-open-evidence')){const d=$('#xixiaDossierDrawer');if(d){d.open=true;d.scrollIntoView({behavior:'smooth',block:'start'})}}
 if(b.hasAttribute('data-xixia-more-related')){state.xixiaRelatedLimit=(state.xixiaRelatedLimit||12)+12;renderXixiaVisual()}
});

function renderXixiaImageDetail(r){
 if(r.era!=='西夏')return;
 renderXixiaSubcategoryDetail(r);
 const imageHost=document.querySelector('#detailContent .detail-image'),textHost=document.querySelector('#detailContent .detail-text');
 if(r.imageUrlIsDocument){const a=imageHost?.querySelector('a');if(a){a.textContent='查看原始文献图版 ↗';a.href=r.sourceUrl}}
 if(r.resolutionLabel||r.highResolutionSourceUrl){const n=document.createElement('p');n.className='visual-resolution';n.innerHTML=esc(r.resolutionLabel||'公开来源预览')+(r.highResolutionSourceUrl?'<br><a href="'+esc(r.highResolutionSourceUrl)+'" target="_blank" rel="noopener noreferrer">高清图／原始出版来源 ↗</a>':'')+(r.highResolutionAccessNote?'<br>'+esc(r.highResolutionAccessNote):'');imageHost?.append(n)}
 if(r.dateDisputed||r.crosses1227||r.visualScope==='conditional'){const n=document.createElement('p');n.className='visual-dating-alert';n.textContent=xixiaImageScope(r)+'：'+(r.datingBasis||r.date);textHost?.querySelector('h2')?.after(n)}
 const group=r.visualObjectId&&records.filter(v=>v.era==='西夏'&&v.visualObjectId===r.visualObjectId&&chronoMatches(v));
 if(group?.length>1){const n=document.createElement('section');n.className='visual-object-views';n.innerHTML='<h3>同件／同图组 · '+group.length+' 个已收录视图</h3><p>不同视角或来源图版；不等于'+group.length+'件文物。</p><div>'+group.map(v=>'<button data-detail="'+esc(v.id)+'" class="'+(v.id===r.id?'selected':'')+'" title="'+esc(v.title)+'"><img src="'+esc(v.localImage||v.previewUrl||v.imageUrl)+'" alt="'+esc(v.title)+'" loading="lazy"><span>'+esc(v.title)+'</span></button>').join('')+'</div>';imageHost?.append(n)}
}
