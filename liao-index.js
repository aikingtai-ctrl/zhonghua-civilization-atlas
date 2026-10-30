window.ARCHIVE_DATA=(function(catalog,pack){
 const byId=new Map(pack.records.map(r=>[r.id,r]));
 return {...catalog,records:catalog.records.map(r=>{if(r.era!=='辽'||(r.batch&&r.localImage&&r.sourceUrl))return r;const full=byId.get(r.id);if(!full)throw Error('Missing Liao detail '+r.id);return {...full};})};
})(window.ARCHIVE_DATA,window.LIAO_DATA);
