/* Expand the audited Song collection before the shared archive initializes. */
window.expandSong=function(catalog,pack){
 const labels={'northern-song':'北宋','southern-song':'南宋','song-wide':'两宋（未细分）'};
 const categories={'绘画与场景':'服饰与人物','书法与古籍':'纹样与文书','人物与造像':'服饰与人物','服饰与织物':'服饰与人物'};
 const key=u=>String(u||'').replace('/web-large/','/original/').split('#')[0];
 const records=catalog.records.slice(),old=new Map(records.filter(r=>['北宋','南宋','两宋（未细分）'].includes(r.era)).map(r=>[key(r.imageUrl),r])),aliases={};
 for(const s of pack.records){
  const prior=old.get(key(s.imageUrl));const r={...s,id:prior?.id||s.id,originalSongId:s.id,songCollection:true,era:labels[s.dynasty],polity:labels[s.dynasty],songCategory:s.category,category:categories[s.category]||s.category,catalogNumber:prior?.catalogNumber||s.id,sourceTitle:s.institution+' · 馆藏著录',sourceType:'博物馆官方馆藏图像与原始著录',additionalSources:[],notes:[s.evidenceNote,s.groupingNote,s.songDatingReason].filter(Boolean).join(' '),evidence:s.category==='绘画与场景'?'历史绘画':s.category==='书法与古籍'?'古书／书法原迹':'实物照片',relatedCategories:s.category==='绘画与场景'?['建筑与空间','纹样与文书']:[],contextOnly:s.songDatingLimited};
  if(prior){r.localImage=s.localImage||prior.localImage;records[records.indexOf(prior)]=r;}else records.push(r);aliases[s.id]=r.id;
 }
 const entries=pack.entries.map(e=>({...e,referenceIds:e.referenceIds.map(id=>aliases[id])})),profiles=pack.profiles.map(p=>({...p,referenceIds:p.referenceIds.map(id=>aliases[id])}));
 const referenceSets=new Map([...entries.map(p=>[p.id,new Set(p.referenceIds)]),...profiles.map(p=>['ruler-'+p.id,new Set(p.referenceIds)])]);
 window.songEraMatches=(r,era,period)=>era==='all'||r.era===era||(['北宋','南宋'].includes(era)&&referenceSets.get(period)?.has(r.id));
 return {...catalog,records,song:{...pack,images:pack.records.length,objects:new Set(pack.records.map(r=>r.objectKey)).size,entries,profiles,aliases,referenceSets}};
};
window.ARCHIVE_DATA=window.expandSong(window.ARCHIVE_DATA,window.SONG_DATA);
// Renzong initially continued Qianxing; keep the shared tree and dossier consistent.
if(window.CHRONOLOGY_DATA){const inherited=window.CHRONOLOGY_DATA.entries.find(e=>e.id==='dila-era-825');if(inherited)inherited.inherited=true;}
/* Keep direct dating, counts, exports and detail explanations on the same rule. */
(()=>{const original=ChronologyCore.create;ChronologyCore.create=function(data,records){const index=original(data,records),match=index.match,count=index.count,explain=index.explain,reason=index.reason;index.match=function(r,n,mode='contained'){if(!r?.songCollection||!n)return match(r,n,mode);if(r.era!==n.parentEra)return false;if(n.kind==='undated')return !r.songStrictPeriodIds.length;if(mode!=='contained')return false;return (n.kind==='ruler'?r.songStrictRulerIds:r.songStrictPeriodIds).includes(n.id)};index.count=(n,mode='contained')=>['北宋','南宋','两宋（未细分）'].includes(n?.parentEra)?records.filter(r=>index.match(r,n,mode)).length:count(n,mode);index.explain=(r,n)=>r?.songCollection?'馆方原始断代：'+r.date+'。'+(index.match(r,n)&&n.kind!=='undated'?'完整断代落入本期；不据此推定具体事件或制作地点。':r.songDatingReason):explain(r,n);index.reason=r=>r?.songCollection?r.songDatingReason:reason(r);return index;};})();
