/* Image counts describe source images; grouped browsing preserves every actual view. */
(() => {
 const tang=records.filter(r=>r.era==='唐'), q=s=>document.querySelector(s);
 const groupKey=r=>r.browseGroupKey||r.objectKey||r.sourceUrl||r.id;
 const groups=new Map;
 for(const r of tang){const key=groupKey(r);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(r)}
 const topicDefs=window.ARCHIVE_DATA.tang?.gallery?.topics||[];
 state.tangTopic='all';state.tangGrouping='objects';state.tangDating='all';state.tangInstitution='all';state.tangContextRecords=null;
 const panel=document.createElement('section');panel.id='tangGalleryTools';panel.className='tg-tools';panel.setAttribute('aria-label','唐代视觉参考主题');
 q('#atlasImages .search-row').before(panel);
 panel.innerHTML='<div class="tg-heading"><div><span class="eyebrow">TANG · VISUAL REFERENCES</span><h3>从服饰、人物与空间开始</h3><p id="tgCollectionSize"></p></div><a href="tang-image-audit.json" download>下载收录统计 ↗</a></div><div class="tg-topics" id="tgTopics"></div><div class="tg-controls"><label>收藏与来源<select id="tgInstitution"><option value="all">全部机构</option></select></label><label>浏览方式<select id="tgGrouping"><option value="objects">按来源记录合并多视角</option><option value="images">逐张查看全部图像</option></select></label><label>年代范围<select id="tgDating"><option value="all">全部 · 保留跨期标记</option><option value="tang">排除跨唐前后时期</option><option value="dated">有进一步年代依据</option></select></label></div><p class="tg-help">按馆方记录合并多视角，详情可切换。敦煌局部保留所属壁面；俑与画中人物不等于执政者肖像。</p>';
 const institutions=[...new Set(tang.map(r=>r.institution))].sort((a,b)=>tang.filter(r=>r.institution===b).length-tang.filter(r=>r.institution===a).length);
 q('#tgInstitution').insertAdjacentHTML('beforeend',institutions.map(name=>'<option value="'+esc(name)+'">'+esc(name)+' · '+tang.filter(r=>r.institution===name).length+' 图</option>').join(''));
 const baseFiltered=filtered;
 function selection(options){return baseFiltered(options).filter(r=>state.era!=='唐'||((!state.tangContextRecords||state.tangContextRecords.includes(r.id))&&(state.tangTopic==='all'||(r.tangTopics||[]).includes(state.tangTopic))&&(state.tangInstitution==='all'||r.institution===state.tangInstitution)&&(state.tangDating!=='tang'||!r.crossPeriod)&&(state.tangDating!=='dated'||!!chronologyIndex.dates.get(r.id))))}
 filtered=function(options){const list=selection(options);if(state.era!=='唐'||state.chronoId||state.tangGrouping==='images')return list;const seen=new Set;return list.filter(r=>{const key=groupKey(r);if(seen.has(key))return false;seen.add(key);return true})};
 const baseReset=reset;
 reset=function(){state.tangTopic='all';state.tangGrouping='objects';state.tangDating='all';state.tangInstitution='all';state.tangContextRecords=null;baseReset()};
 function sync(){
  panel.hidden=state.era!=='唐';if(panel.hidden)return;
  const audit=window.ARCHIVE_DATA.tang.gallery,scope=tang.filter(chronoMatches);
  q('#tgCollectionSize').textContent=scope.length.toLocaleString('zh-CN')+' 张图像 · 当前历史范围 · '+new Set(scope.map(groupKey)).size+' 个来源记录／壁面组';
  q('#tgTopics').innerHTML=[{id:'all',label:'全部参考'},...topicDefs].map(t=>'<button data-tang-topic="'+esc(t.id)+'" aria-pressed="'+(state.tangTopic===t.id)+'" class="'+(state.tangTopic===t.id?'selected':'')+'"><span>'+esc(t.label)+'</span><b>'+scope.filter(r=>t.id==='all'||(r.tangTopics||[]).includes(t.id)).length+'</b></button>').join('');
  q('#tgGrouping').disabled=!!state.chronoId;if(state.chronoId)state.tangGrouping='images';q('#tgInstitution').value=state.tangInstitution;q('#tgGrouping').value=state.tangGrouping;q('#tgDating').value=state.tangDating;
  q('.tg-help').textContent=state.tangContextRecords?'正在查看洞窟等来源的历史背景参考；这些图像不等于该年号的确证作品。点击“重置”返回唐代全部图像。':'按馆方记录合并多视角，详情可切换。敦煌局部保留所属壁面；俑与画中人物不等于执政者肖像。';
  const list=selection(),n=new Set(list.map(groupKey)).size;
  q('#resultCount').textContent='当前 '+list.length+' 张图像 · '+n+' 个浏览组'+(state.tangGrouping==='objects'?' · 同件多视角已合并':' · 逐张显示');
  const menu=q('[data-atlas-pane="images"]');if(menu)menu.innerHTML='影像目录<b>'+list.length+'</b>';
  q('#cards').querySelectorAll('.card').forEach(card=>{const id=card.querySelector('[data-detail]')?.dataset.detail,r=tang.find(x=>x.id===id);if(!r)return;const siblings=groups.get(groupKey(r))||[];const text=[r.crossPeriod?'跨期材料':null,r.imageRole==='institution-published-detail'?'官方壁画局部':null,siblings.length>1?siblings.length+' 张同件图像':null].filter(Boolean).join(' · ');if(text)card.querySelector('.card-body').insertAdjacentHTML('beforeend','<p class="tg-card-note">'+esc(text)+'</p>')});
 }
 const baseRender=renderCards;renderCards=function(){baseRender();sync()};
 const baseDetail=detail;
 detail=function(id){baseDetail(id);const r=tang.find(x=>x.id===id);if(!r)return;const list=(groups.get(groupKey(r))||[]).filter(chronoMatches);const meta=q('#detailContent .meta-grid');if(meta&&r.imageValidation?.width)meta.insertAdjacentHTML('beforeend','<dt>所链图像尺寸</dt><dd>'+r.imageValidation.width+' × '+r.imageValidation.height+' 像素'+(r.imageAccess==='public-preview'?' · 官方公开预览，保留原有水印；不是授权高清文件':'')+'</dd>');if(r.imageAccess==='public-preview'){const link=q('#detailContent .detail-image a');if(link)link.textContent='查看官方公开预览 ↗'}if(meta)meta.insertAdjacentHTML('beforeend',(r.sourceObjectId?'<dt>官网记录编号</dt><dd>'+esc(r.sourceObjectId)+'</dd>':'')+(r.parentWallId?'<dt>所属壁面</dt><dd>'+esc(r.parentWallId)+'</dd>':'')+(r.imageValidation?'<dt>图像核验</dt><dd>'+esc(r.imageVerified||'已核对官方图像地址及响应；详见原始著录')+'</dd>':''));if(list.length>1){q('#detailContent .detail-image').insertAdjacentHTML('beforeend','<section class="tg-views"><h3>同件 '+list.length+' 张图像</h3><p>馆方独立视角；选择后查看对应原图与出处。</p><div>'+list.map((v,i)=>'<button data-detail="'+esc(v.id)+'" aria-pressed="'+(v.id===id)+'" class="'+(v.id===id?'selected':'')+'">'+esc(v.viewLabel||'视图 '+(i+1))+'</button>').join('')+'</div></section>')}};
 document.addEventListener('click',ev=>{const b=ev.target.closest('[data-tang-topic]');if(b){state.tangTopic=b.dataset.tangTopic;state.limit=12;renderCards()}const c=ev.target.closest('[data-tang-context-reign]');if(c){const p=window.ARCHIVE_DATA.tang.reigns.profiles.find(p=>p.reignId===c.dataset.tangContextReign);if(p){selectEra('唐',null,false);state.tangContextRecords=p.contextRecordIds||[];renderCards();q('[data-atlas-pane="images"]').click();q('#tangGalleryTools').scrollIntoView({block:'start',behavior:'smooth'})}}});
 for(const [id,key] of [['tgInstitution','tangInstitution'],['tgGrouping','tangGrouping'],['tgDating','tangDating']])q('#'+id).addEventListener('change',ev=>{state[key]=ev.target.value;state.limit=12;renderCards()});
 renderCards();
})();
