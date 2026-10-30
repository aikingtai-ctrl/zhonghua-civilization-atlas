/* Tang selection always opens the image results. Unknown dates stay explicit. */
(() => {
 const q=s=>document.querySelector(s),all=records.filter(r=>r.era==='唐');
 const assignment=TangChronologyCore.create(window.CHRONOLOGY_DATA,records,chronologyIndex);
 const evidenceById=new Map;for(const s of window.TANG_DATE_EVIDENCE?.checks||[])for(const id of s.imageIds)evidenceById.set(id,s);
 const periodName=id=>{const n=chronologyNodes.get(id);return n?([n.ruler,n.reign].filter(Boolean).join(' · ')||n.label):''};
 const refinedLabel=(a,s)=>a?.range&&s?.result==='refined'?(s.requiresPolitySeparation?[a.range.rulerLabel,a.range.polity,chronoYears(a.range.start,a.range.end)].filter(Boolean).join(' · '):(s.relation==='burial-context'?'安葬背景 · ':/published|approximate/.test(s.method||'')?'研究断代 · ':'')+(/approximate/.test(s.method||'')?'约':'')+chronoYears(a.range.start,a.range.end)+' · '+(a.reignIds.length?periodName(a.reignIds[0]):a.rulerIds.length?periodName(a.rulerIds[0]):'跨期参考')):'';
 window.tangChronologySearchText=r=>{const a=assignment.byId.get(r.id),s=evidenceById.get(r.id);return [refinedLabel(a,s),...(a?.reignIds||[]).map(periodName),...(a?.rulerIds||[]).map(periodName),a?.disputed?'断代争议':''].join(' ')};
 function syncCardDates(){for(const card of document.querySelectorAll('#cards .card')){const id=card.querySelector('[data-detail]')?.dataset.detail,a=assignment.byId.get(id),s=evidenceById.get(id);if(!a)continue;const label=refinedLabel(a,s),p=card.querySelector('.card-date');if(label&&p){p.textContent=label;p.title='原始著录：'+a.originalDate;p.classList.add('tcn-refined-date')}if(a.disputed){const badge=card.querySelector('.badge');if(badge)badge.textContent='断代有分歧'}}}
 const group=chronologyGroups.find(g=>g.name==='唐');
 const bucketNodes=Object.entries(assignment.labels).map(([key,label])=>{
  const n={id:'tang-date-'+key,kind:'date-bucket',parentEra:'唐',label,dateStatus:key,recordIds:assignment.buckets[key],dateText:'按原始断代归类'};chronologyNodes.set(n.id,n);return n;
 });
 group.undated.label='全部未归入单一年号';group.undated.dateText='含跨期、执政期及载体待核';
 window.renderTangChronologyExtras=()=>'<details class="tcn-left-buckets"><summary>全库年代归属 · '+all.length+' 张</summary>'+bucketNodes.filter(n=>n.kind!=='undated').map(n=>chronoOption(n,n.label)).join('')+'</details>';
 const coverage=document.createElement('section');coverage.id='tangDateCoverage';coverage.className='tcn-coverage';
 q('#atlasImages').prepend(coverage);
 const nearby=document.createElement('section');nearby.id='tangPeriodNearby';nearby.className='tcn-nearby';q('#empty').after(nearby);
 const profiles=window.ARCHIVE_DATA.tang.reigns.profiles;
 function counts(node){return {direct:chronologyIndex.count(node),overlap:chronologyIndex.count(node,'overlap'),context:chronologyIndex.count(node,'context')}}
 function sync(){
  syncCardDates();
  const isTang=state.era==='唐',node=chronologyNodes.get(state.chronoId),specific=isTang&&!!node;
  coverage.hidden=!isTang;nearby.hidden=true;document.body.classList.toggle('tang-period-selected',specific);
  if(!isTang)return;
  coverage.innerHTML='<details '+(!specific?'open':'')+'><summary>唐代 '+all.length+' 张 · 图像年代索引</summary><div class="tcn-buckets">'+bucketNodes.map(n=>'<button data-chronology="'+esc(n.id)+'" aria-pressed="'+(node?.id===n.id)+'"><strong>'+assignment.buckets[n.dateStatus].length+'</strong><span>'+esc(n.label)+'</span></button>').join('')+'</div><p>四组互不重复，合计 '+all.length+' 张。图像详情保留原始著录、补充断代依据与分歧说明。<a href="tang-chronology-assignments.json" download>逐图归属与出处 ↗</a><a href="tang-date-evidence.json.gz" download>断代依据表 ↗</a></p></details>';
  if(!specific){document.title='唐代影像 · 中华文明影像库';return;}
  const isPeriod=['ruler','reign'].includes(node.kind),c=counts(node),periodLabel=node.kind==='ruler'?node.ruler:node.kind==='reign'?node.ruler+' · '+node.reign:node.label;
  q('#resultsTitle').textContent='唐 · '+periodLabel;
  document.title=periodLabel+' · 唐代图像 | 中华文明影像库';
  const shown=filtered().length;q('#resultCount').textContent=periodLabel+'｜当前 '+shown+' 张 · 已显示 '+Math.min(state.limit,shown)+' 张'+(state.chronoMode==='overlap'?' · 含跨期参考':state.chronoMode==='context'?' · 历史关联':'');
  q('#chronologySelection').setAttribute('aria-live','polite');
  if(isPeriod){
   const text=state.chronoMode==='overlap'?'当前含跨期参考：原始断代与所选执政期或年号有交集，不代表确定归属。':state.chronoMode==='context'?'当前为历史关联：题记、事件或创建年代与本期相关，不等于图片载体或全部现存构件的年代。':c.direct?'当前显示年代依据可明确对应本期的图像。':'本期暂无可明确归属的图像；下方另列跨期参考，不能当作本期确证作品。';
   q('#chronologyMatchNote').textContent=text;
   q('#chronologyModes').innerHTML='<button data-chronology-mode="contained" aria-pressed="'+(state.chronoMode==='contained')+'" class="'+(state.chronoMode==='contained'?'selected':'')+'">明确对应 '+c.direct+' 张</button><button data-chronology-mode="overlap" aria-pressed="'+(state.chronoMode==='overlap')+'" class="'+(state.chronoMode==='overlap'?'selected':'')+'">含跨期参考 '+c.overlap+' 张</button>'+(c.context?'<button data-chronology-mode="context" aria-pressed="'+(state.chronoMode==='context')+'" class="'+(state.chronoMode==='context'?'selected':'')+'">历史关联 '+c.context+' 张</button>':'');
   q('#chronologyModes').hidden=false;
   q('#empty h3').textContent=c.direct?'当前筛选条件下没有结果':periodLabel+'：暂无明确归属图像';
   q('#empty p').textContent='所选范围为 '+chronoYears(node.start,node.end)+'。只有馆方断代或可靠纪年支持的图像才列入“明确对应”；其他资料不会自动算作本期作品。';
   if(!c.direct&&state.chronoMode==='contained'&&!state.query&&state.category==='all'){
    const candidates=all.filter(r=>chronologyIndex.match(r,node,'overlap'));
    const contextIds=[...new Set(profiles.filter(p=>node.kind==='ruler'?node.entries.some(e=>e.id===p.reignId):p.reignId===node.id).flatMap(p=>[...(p.recordIds||[]),...(p.contextRecordIds||[])]))];
    const history=all.filter(r=>contextIds.includes(r.id)&&!candidates.some(c=>c.id===r.id));
    nearby.hidden=false;
    const cards=(list,label)=>list.slice(0,6).map(r=>'<button class="tcn-preview" data-tang-cross-detail="'+esc(r.id)+'"><img src="'+esc(r.localImage||r.previewUrl||r.imageUrl)+'" alt="'+esc(r.title)+'" loading="lazy" referrerpolicy="no-referrer"><span><b>'+esc(r.title)+'</b><small>'+esc(label)+' · '+esc(r.date)+'</small><small>'+esc(r.institutionShort||r.institution)+'</small></span></button>').join('');
    nearby.innerHTML=(candidates.length?'<h3>跨期参考 · '+candidates.length+' 张</h3><p>以下图像的馆方断代范围与 '+esc(periodLabel)+' 有交集，但无法据此确定归属。先展示 '+Math.min(6,candidates.length)+' 张。</p><div class="tcn-previews">'+cards(candidates,'跨期参考，未确属本期')+'</div><button class="secondary" data-chronology-mode="overlap">查看全部 '+candidates.length+' 张跨期参考 →</button>':'')+(history.length?'<h3>相关历史材料 · '+history.length+' 张</h3><p>用于理解制度或事件背景，不计入本期确证图像。</p><div class="tcn-previews">'+cards(history,'历史背景，不作本期断代')+'</div>':'')+'<button class="quiet" data-atlas-pane="reigns">查看本期年号档案与依据 →</button>';
    handleImageErrors(nearby);
   }
  }else if(node.dateStatus){
   q('#chronologyMatchNote').textContent=node.dateStatus==='reign'?'这些图像有可对应到单个年号的年代依据；点击详情查看具体归属和出处。':node.dateStatus==='ruler'?'这些图像可限定在某一执政时期，但不能再精确分配到一个年号。':node.dateStatus==='range'?'这些图像涉及跨期范围、历史关联或断代分歧；详情逐条说明。': '这些图像的公开来源仅著录朝代、分期或未提供更细年代，详情保留来源和已知范围。';
   q('#chronologyModes').hidden=true;
  }
 }
 const renderBefore=renderCards;renderCards=function(){renderBefore();sync()};
 const selectBefore=selectChronology;selectChronology=function(id,scroll=true){selectBefore(id,scroll);if(state.era==='唐'){state.tangGrouping='images';renderCards()}};
 const detailBefore=detail;detail=function(id){detailBefore(id);const a=assignment.byId.get(id),s=evidenceById.get(id),meta=q('#detailContent .meta-grid');if(!a||!meta||!q('#detailDialog').open)return;
  const name=id=>{const n=chronologyNodes.get(id);return n?([n.ruler,n.reign].filter(Boolean).join(' · ')||n.label)+'（'+chronoYears(n.start,n.end)+'）':id};
  const periodLinks=[...a.rulerIds,...a.reignIds].map(id=>'<button class="quiet" data-tang-detail-period="'+esc(id)+'">'+esc(name(id))+' →</button>').join('');
  const why=a.disputed?'断代或载体存在分歧，保留各方依据，不计入无争议的明确归属。':a.status==='undated'?'现有公开著录不足以区分执政者与年号。':a.status==='range'?'现有依据涉及跨期范围或历史关联，不能视作单一时期的确证作品。':a.status==='ruler'?'可对应执政时期；年号或年内改元证据不足，保留待细分。':'以原物题记、馆藏断代或明确的研究范围对应年号；不据此推定精确制作日。';
  const urls=[...new Set([a.sourceUrl,s?.evidenceUrl,...(s?.evidenceUrls||[])].filter(u=>/^https?:\/\//.test(u||'')))];
  const links=urls.map((u,i)=>'<a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">'+(i===0?'原始馆藏／图像出处':'断代依据 '+i)+' ↗</a>').join('');
  const explanation=s?.note||a.attributionNote||a.range?.note||'';
  meta.insertAdjacentHTML('afterend','<section class="detail-section tcn-attribution"><h3>纪年归属 · '+esc(assignment.labels[a.status])+'</h3><p class="tcn-date-heading">'+esc(refinedLabel(a,s)||(a.range?chronoYears(a.range.start,a.range.end):'具体年份未定'))+'</p><p class="tcn-original">原始著录：'+esc(a.originalDate)+'</p><p>'+esc(why)+'</p>'+(explanation?'<p>'+esc(explanation)+'</p>':'')+(s?.evidenceText?'<p class="tcn-evidence-text">依据摘要：'+esc(s.evidenceText)+'</p>':'')+(s?.evidenceLocator?'<p>'+esc(s.evidenceLocator)+'</p>':'')+'<div class="tcn-source-links">'+links+'</div>'+periodLinks+'</section>');
 };
 document.addEventListener('click',ev=>{const b=ev.target.closest('[data-tang-detail-period]');if(b){q('#detailDialog').close();selectChronology(b.dataset.tangDetailPeriod)}const cross=ev.target.closest('[data-tang-cross-detail]');if(cross){const r=all.find(r=>r.id===cross.dataset.tangCrossDetail),node=chronologyNodes.get(state.chronoId);if(chronologyIndex.match(r,node,'overlap')){state.chronoMode='overlap';renderCards();detail(r.id)}else{selectEra('唐',null,false);detail(r.id)}}if(ev.target.closest('#eraList .chron-name-select'))ev.preventDefault()});
 function route(){const hash=location.hash,p=new URLSearchParams(hash.slice(1));if(p.has('period')){const id=p.get('period');if(chronologyNodes.get(id)?.parentEra==='唐'&&(state.chronoId!==id||state.era!=='唐')){selectChronology(id,false);if(p.has('item'))detail(p.get('item'))}}else if(hash==='#tang'&&(state.era!=='唐'||state.chronoId))selectEra('唐',null,false)}
 // The shared scope controller owns hash/history changes across all dynasties.
 if(state.era==='唐'&&state.chronoId)state.tangGrouping='images';
 renderChronology();route();renderCards();
})();
