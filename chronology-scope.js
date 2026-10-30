/* Keep one selected historical scope across clicks, URLs, filters and image details. */
function resetScopeFilters(){
 const scope={era:state.era,polity:state.polity,chronoId:state.chronoId,view:state.view};
 const url=location.href;
 reset();Object.assign(state,scope,{chronoMode:'contained',sourceInstitution:null});
 history.replaceState(null,'',url);renderChronology();renderCards();
}
(() => {
 let routing=false,nested=0;
 const oldSelect=selectChronology,oldEra=selectEra,oldRender=renderCards,oldDetail=detail;
 function commit(before,target){
  if(routing||nested){history.replaceState(null,'',target);return}
  if(new URL(target,location.href).href===before)return;
  history.replaceState(null,'',before);history.pushState(null,'',target);
 }
 selectChronology=function(id,scroll=true){
  const before=location.href;nested++;
  try{oldSelect(id,scroll);renderCards();const selected=$('#eraList [data-chronology="'+CSS.escape(state.chronoId)+'"]'),box=$('#chronologyScroll');if(selected&&box)box.scrollTop+=selected.getBoundingClientRect().top-box.getBoundingClientRect().top-box.clientHeight/3}
  finally{nested--}
  commit(before,'#period='+encodeURIComponent(id));if(scroll)scrollToChronologyResults();
 };
 selectEra=function(era,polity=null,scroll=true){const before=location.href;oldEra(era,polity,scroll);if(nested)return;const target=era==='all'?location.pathname+location.search:'#era='+encodeURIComponent(era)+(polity?'&polity='+encodeURIComponent(polity):'');commit(before,target)};
 renderCards=function(){
  oldRender();
  const node=chronologyNodes.get(state.chronoId);
  $('#clearFilters').textContent='清除附加筛选';$('#emptyReset').textContent='清除附加筛选';
  if(state.chronoId){
   const list=filtered(),total=node?chronologyIndex.count(node):0;
   $('#resultCount').textContent='本范围 '+total+' 张 · 当前筛选 '+list.length+' 张 · 已显示 '+Math.min(state.limit,list.length)+' 张';
   if(!node){$('#resultsTitle').textContent='无法识别的历史范围';document.title='时期链接无效 | 中华文明影像库'}
   $('#cards').querySelectorAll('.card').forEach(card=>{card.dataset.period=state.chronoId;card.dataset.recordId=card.querySelector('[data-detail]')?.dataset.detail||''});
  }
 };
 detail=function(id){
  const r=records.find(r=>r.id===id),node=chronologyNodes.get(state.chronoId);
  if(state.chronoId&&(!node||!chronoMatches(r))){toast('该图不属于当前历史范围，请返回本朝全部资料查阅。');return}
  oldDetail(id);
  if(node&&r){const section=document.createElement('section');section.className='detail-section chronology-attribution';section.innerHTML='<h3>本图与当前时期的对应依据</h3><p><strong>'+esc([node.parentEra,node.ruler,node.kind==='ruler'?null:node.label].filter(Boolean).join(' · '))+'</strong></p><p>'+esc(chronologyIndex.explain(r,node))+'</p><p>原始断代：'+esc(r.date)+'</p><a href="'+esc(r.sourceUrl)+'" target="_blank" rel="noopener noreferrer">核对原始著录 ↗</a>';$('#detailContent .meta-grid')?.after(section)}
 };
 function route(){
  const hash=location.hash,p=new URLSearchParams(hash.slice(1));routing=true;
  try{
   if($('#detailDialog').open)$('#detailDialog').close();
   if(p.has('period')){selectChronology(p.get('period'),false);if(p.has('item'))detail(p.get('item'));requestAnimationFrame(scrollToChronologyResults)}
   else if(p.has('era')){const era=p.get('era');if(periods.some(x=>x.name===era)||era==='all')selectEra(era,p.get('polity'),false);else selectChronology('invalid-era:'+era,false)}
   else if(['#xixia','#tang','#xia'].includes(hash))selectEra({'#xixia':'西夏','#tang':'唐','#xia':'夏／二里头文化'}[hash],null,false);
   else if(!hash||hash==='#explore')selectEra('all',null,false);
   else if(p.has('item')){const r=records.find(r=>r.id===p.get('item'));if(r){selectEra(r.era,null,false);detail(r.id)}}
  }finally{routing=false}
 }
 document.addEventListener('click',e=>{if(e.target.closest('summary .chron-select-name'))e.preventDefault()},true);
 $('#clearFilters').onclick=resetScopeFilters;
 $('#emptyReset').onclick=resetScopeFilters;
 const oldClose=closeDialog;
 closeDialog=function(){oldClose();if(state.chronoId)history.replaceState(null,'','#period='+encodeURIComponent(state.chronoId))};
 $('#closeDialog').onclick=closeDialog;
 $('#detailDialog').addEventListener('cancel',()=>{if(state.chronoId)history.replaceState(null,'','#period='+encodeURIComponent(state.chronoId))});
 window.addEventListener('hashchange',route);
 // Initial navigation is reapplied after every extension has installed its filters.
 if(typeof chronologyInitialHash==='string'&&/^#(?:period=|era=)/.test(chronologyInitialHash))history.replaceState(null,'',chronologyInitialHash);
 if(/^#(?:period=|era=)/.test(location.hash))route();else renderCards();
})();
