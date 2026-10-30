/* Exhaustive date assignments, without inventing dates for dynasty-only records. */
(function(root){
 const labels={reign:'可对应年号',ruler:'可对应执政期，年号待分',range:'跨期、关联或存疑',undated:'年代未细分'};
 function rulers(data){
  const entries=data.entries.filter(e=>e.parentEra==='唐');
  return [...new Set(entries.map(e=>e.rulerId))].map(id=>{
   const es=entries.filter(e=>e.rulerId===id),first=es[0];
   return {id:'ruler-'+id,kind:'ruler',parentEra:'唐',polity:first.polity==='唐'?null:first.polity,ruler:first.ruler,label:first.ruler,start:Math.min(...es.map(e=>e.start)),end:Math.max(...es.map(e=>e.end)),entries:es};
  });
 }
 function create(data,records,index){
  const images=records.filter(r=>r.era==='唐'),reigns=data.entries.filter(e=>e.parentEra==='唐').map(e=>({...e,kind:e.kind||'reign'})),rulerNodes=rulers(data);
  const byId=new Map,buckets={reign:[],ruler:[],range:[],undated:[]};
  for(const r of images){
   const date=index.dates.get(r.id),reignIds=reigns.filter(e=>index.match(r,e)).map(e=>e.id),rulerIds=rulerNodes.filter(n=>index.match(r,n)).map(n=>n.id);
   const audit=data.recordAttribution?.[r.id];
   const status=audit?.contextOnly||audit?.dateDisputed?'range':!date?'undated':reignIds.length===1?'reign':rulerIds.length===1?'ruler':'range';
   const item={id:r.id,status,originalDate:r.date,range:date?{start:date.start,end:date.end,relation:date.relation||'object',note:date.note||r.datingBasis||'',points:date.points,evidenceLevel:date.evidenceLevel,sourceUrl:date.sourceUrl,evidenceUrls:date.evidenceUrls,rulerLabel:date.rulerLabel,polity:date.polity}:null,reignIds,rulerIds,sourceUrl:r.sourceUrl,disputed:!!audit?.dateDisputed,attributionNote:audit?.note};
   byId.set(r.id,item);buckets[status].push(r.id);
  }
  return {byId,buckets,labels,reigns,rulers:rulerNodes,total:images.length};
 }
 const api={create,rulers,labels};root.TangChronologyCore=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window==='undefined'?globalThis:window);
