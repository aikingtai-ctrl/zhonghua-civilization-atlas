/* One attribution rule is shared by navigation counts, galleries and exports. */
(function(root){
  const normalize=s=>String(s??'').normalize('NFKC').replace(/[祐佑]/g,'祐').replace(/\s/g,'');
  const valid=v=>typeof v==='number'&&Number.isFinite(v)&&v!==0;
  const year=y=>y<0?'前'+Math.abs(y):String(y);
  const years=(a,b)=>valid(a)&&valid(b)?(a===b?year(a):year(a)+'–'+year(b))+'年':'';
  const samePolity=(r,n)=>r.era===n.parentEra&&(n.parentEra==='唐'?(['date-bucket','undated','collection'].includes(n.kind)||!r.polity||r.polity===(n.polity||n.parentEra)):(!n.polity||n.polity===n.parentEra||r.polity===n.polity));
  const contained=(d,n)=>d.points?.length?d.points.some(y=>y>=n.start&&y<=n.end):d.start>=n.start&&d.end<=n.end;
  function spans(entries){
    const out=[];
    for(const e of entries.filter(e=>!e.indexOnly&&valid(e.start)&&valid(e.end)).sort((a,b)=>a.start-b.start)){
      const last=out.at(-1);
      if(last&&e.start<=last.end+1)last.end=Math.max(last.end,e.end);else out.push({start:e.start,end:e.end});
    }
    return out;
  }
  function create(data,records){
    const entries=data.entries||[],overrides=data.recordDates||{},audit=data.recordAttribution||{};
    const inPolity=(r,n)=>samePolity(audit[r.id]?.polity?{...r,polity:audit[r.id].polity}:r,n);
    const dates=new Map,entriesByEra=new Map,countCache=new Map,unassigned=new Map;
    for(const e of entries){if(!entriesByEra.has(e.parentEra))entriesByEra.set(e.parentEra,[]);entriesByEra.get(e.parentEra).push(e)}
    const eligible=r=>!!r.sourceUrl&&!r.contextOnly&&!r.dateDisputed&&!['conditional','later-comparison'].includes(r.visualScope)&&!audit[r.id]?.contextOnly&&(!r.dateRelation||r.dateRelation==='object')&&(!audit[r.id]?.relation||audit[r.id].relation==='object');
    for(const r of records){
      const es=(entriesByEra.get(r.era)||[]).filter(e=>inPolity(r,e)&&!e.indexOnly);
      const broad=/未细分|未作更细|朝代宽断代|不是制造纪年/.test((r.date||'')+(r.datePrecision||''));
      const override=r.era==='唐'&&(r.historicalRange||valid(r.dateStart)&&valid(r.dateEnd))&&!overrides[r.id]?.attribution?null:overrides[r.id];
      let d=override?{...override}:r.historicalRange?{...r.historicalRange}:valid(r.dateStart)&&valid(r.dateEnd)&&!broad?{start:r.dateStart,end:r.dateEnd,note:r.datePrecision||r.datingBasis||'来源著录的年代范围'}:null;
      if(r.id==='arch-tang-foguang-landscape'&&d)d={...d,relation:'foundation',note:'857为东大殿创建纪年；建筑群现状含后世遗存，只作历史关联。'};
      const named=es.filter(e=>e.reign&&normalize(r.date).includes(normalize(e.reign))&&(!d||d.start<=e.end&&d.end>=e.start));
      if(!d&&named.length===1&&!broad&&!r.contextOnly&&valid(named[0].start)&&valid(named[0].end))d={start:named[0].start,end:named[0].end,note:'来源著录标明年号；公元范围据纪年目录对照'};
      if(d){
        d.relation=audit[r.id]?.relation||r.dateRelation||d.relation||'object';
        d.contextOnly=!eligible(r);
        d.reignIds=d.reignIds?.length?d.reignIds:d.ignoreOriginalReign?[]:r.reignIds?.length?r.reignIds:named.map(e=>e.id);
        d.note=audit[r.id]?.note||d.note;
        const possible=es.filter(e=>!e.recordIds&&valid(e.start)&&valid(e.end)&&contained(d,e)&&(!d.reignIds.length||d.reignIds.includes(e.id)));
        d.ambiguousReign=!d.points?.length&&possible.length>1;
        const rulerIds=[...new Set(es.map(e=>e.rulerId).filter(Boolean))];
        const possibleRulers=rulerIds.filter(id=>{const children=es.filter(e=>e.rulerId===id);return (!d.reignIds.length||children.some(e=>d.reignIds.includes(e.id)))&&spans(children).some(n=>contained(d,n))});
        d.ambiguousRuler=!d.points?.length&&possibleRulers.length>1;
      }
      dates.set(r.id,d);
    }
    function match(r,node,mode='contained'){
      // Invalid scopes fail closed. The all-dynasties view bypasses this function.
      if(!r||!node||!inPolity(r,node))return false;
      if(node.parentEra==='唐'&&node.kind==='date-bucket')return !!node.recordIds?.includes(r.id);
      if(node.kind==='collection')return !!node.recordIds?.includes(r.id);
      if(node.kind==='undated'){
        if(!unassigned.has(r.id))unassigned.set(r.id,!(entriesByEra.get(r.era)||[]).some(e=>match(r,{...e,kind:e.kind||'reign'},'contained')));
        return unassigned.get(r.id);
      }
      if(node.indexOnly)return false;
      const d=dates.get(r.id);
      if(mode==='contained'&&node.kind==='reign'&&d?.rulerOnly)return false;
      if(node.kind==='ruler'&&d?.rulerIds?.length&&!d.rulerIds.includes(node.id))return false;
      if(mode==='contained'&&(!eligible(r)||d?.contextOnly||d?.relation&&d.relation!=='object'))return false;
      if(node.recordIds){
        if(!node.recordIds.includes(r.id)||node.qinRulerId&&!(r.qinRulerLinks||[]).some(l=>l.id===node.qinRulerId&&l.relation==='direct'))return false;
        // An explicit collection link cannot override a known date outside this scope.
        if(d&&valid(d.start)&&valid(d.end)&&valid(node.start)&&valid(node.end))return contained(d,node);
        return true;
      }
      if(!d||!valid(d.start)||!valid(d.end)||!valid(node.start)||!valid(node.end))return false;
      if(Boolean(d.relation&&d.relation!=='object')!==(mode==='context'))return false;
      if(node.kind==='reign'&&d.reignIds?.length&&!d.reignIds.includes(node.id))return false;
      if(node.kind==='ruler'&&node.entries&&d.reignIds?.length&&!node.entries.some(e=>d.reignIds.includes(e.id)))return false;
      if(mode==='contained'&&(node.kind==='reign'&&d.ambiguousReign||node.kind==='ruler'&&d.ambiguousRuler))return false;
      const ranges=node.kind==='ruler'&&node.entries?spans(node.entries):[node];
      return ranges.some(n=>mode==='overlap'?d.points?.length?d.points.some(y=>y>=n.start&&y<=n.end):d.start<=n.end&&d.end>=n.start:contained(d,n));
    }
    function reason(r){
      const d=dates.get(r.id);
      if(audit[r.id]?.note)return audit[r.id].note;
      if(!eligible(r)||d?.contextOnly||d?.relation&&d.relation!=='object')return '关联背景、载体差异或存疑资料，不能作为具体纪年的直接图证';
      if(!d)return '来源未提供可归入具体纪年的断代';
      if(d.ambiguousReign)return '同年改元或纪年重叠，现有依据无法唯一确定年号';
      return '原始断代跨度超过单个纪年，或尚无明确的纪年归属依据';
    }
    function explain(r,node){
      if(node?.kind==='undated')return reason(r);
      const d=dates.get(r.id);
      if(node?.qinRulerId)return (r.qinRulerLinks||[]).find(l=>l.id===node.qinRulerId&&l.relation==='direct')?.reason||'以直接纪年和铭文为据';
      if(node?.recordIds)return '依据馆藏、铭文或考古分期关联；未推定公元确年';
      if(d?.points?.length)return '依据分立题记年份 '+d.points.filter(y=>y>=node.start&&y<=node.end).map(year).join('、')+'；不是连续制作年代';
      return (d?.note||'来源断代完整落入所选时期')+'（'+years(d?.start,d?.end)+'）';
    }
    function count(node,mode='contained'){
      if(!node)return 0;
      const key=[node.id,node.kind,node.start,node.end,node.polity,mode].join('|');
      if(!countCache.has(key))countCache.set(key,records.filter(r=>match(r,node,mode)).length);
      return countCache.get(key);
    }
    return {dates,match,count,explain,reason};
  }
  const api={normalize,year,years,create};root.ChronologyCore=api;
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window==='undefined'?globalThis:window);

