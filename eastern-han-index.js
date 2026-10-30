window.ARCHIVE_DATA=(function expandEasternHan(catalog,pack){
 const categories={'人物与衣饰':'服饰与人物','建筑与空间':'建筑与空间','画像与生活':'纹样与文书','碑刻与文书':'纹样与文书'};
 const full=new Map(pack.records.map(r=>{const x={...r,easternHanCategory:r.category,category:categories[r.category]||'器物与工艺'};delete x.reignIds;delete x.phaseIds;return [x.id,x]}));
 return {...catalog,records:catalog.records.map(r=>{if(r.era!=='东汉'||(r.batch&&r.localImage&&r.sourceUrl))return r;if(!full.has(r.id))throw Error('Missing Eastern Han detail '+r.id);return full.get(r.id)})};
})(window.ARCHIVE_DATA,window.EASTERN_HAN_DATA);
