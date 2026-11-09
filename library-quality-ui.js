(()=>{
 const advanced=document.querySelector('#advanced');if(!advanced)return;
 const label=document.createElement('label');label.textContent='收藏／来源机构';
 const select=document.createElement('select');select.id='institutionFilter';select.setAttribute('aria-label','筛选收藏或来源机构');
 const all=document.createElement('option');all.value='';all.textContent='全部机构';select.append(all);
 [...new Set(records.map(r=>r.institution))].sort((a,b)=>a.localeCompare(b,'zh-CN')).forEach(name=>{const option=document.createElement('option');option.value=name;option.textContent=name;select.append(option);});
 label.append(select);advanced.prepend(label);
 select.addEventListener('change',()=>{state.sourceInstitution=select.value||null;state.limit=12;renderCards();});
 const render=renderCards;renderCards=function(){select.value=state.sourceInstitution||'';render();};
})();

/* Version-bound source notices supplement, never rewrite, retained records. */
(()=>{
 if(typeof detail!=='function'||typeof fetch!=='function')return;
 const issuesById=new Map();let proofBuildId=null;
 const issueFor=record=>{
  const issue=issuesById.get(record?.id);
  return issue&&/^[a-f0-9]{64}$/.test(issue.sourceRecordSha256||'')&&/^[a-f0-9]{64}$/.test(issue.imageSha256||'')&&issue.sourceRecordSha256===record.sourceRecordSha256&&issue.imageSha256===record.verification?.sha256?issue:null;
 };
 const supplement=record=>{const issue=issueFor(record);return issue?{status:'review-required',proofBuildId,issues:[...issue.issues],sourceRecordSha256:issue.sourceRecordSha256,imageSha256:issue.imageSha256}:null;};
 function annotate(id){
  const target=document.querySelector('#detailContent');if(!target)return;
  target.querySelector('[data-source-quality]')?.remove();
  const record=records.find(row=>row.id===id),issue=issueFor(record);if(!issue)return;
  const section=document.createElement('section');section.className='detail-section';section.dataset.sourceQuality='';section.setAttribute('role','note');
  const heading=document.createElement('h3');heading.textContent='来源复核：待考';
  const note=document.createElement('p');note.className='disclosure';note.textContent='原始著录、入库记录及审核历史保留。当前来源证据仍有待考项，未计入本构建的来源核验通过数。';
  const list=document.createElement('ul');for(const text of issue.issues){const item=document.createElement('li');item.textContent=text;list.append(item);}
  section.append(heading,note,list);target.prepend(section);
 }
 const originalDetail=detail;detail=function(id){originalDetail(id);annotate(id);};
 if(typeof recordForExport==='function'){
  const originalExport=recordForExport;recordForExport=function(record){const value=originalExport(record),notice=supplement(record);return notice?{...value,sourceQualitySupplement:notice}:value;};
 }
 fetch('/publication-proofs/build-report.json',{cache:'no-store',redirect:'error'}).then(response=>{if(!response.ok)throw Error('Source quality unavailable');return response.json();}).then(report=>{
  if(report.schemaVersion!==1||typeof report.buildId!=='string'||!Array.isArray(report.unverifiedRecords))return;
  proofBuildId=report.buildId;
  for(const issue of report.unverifiedRecords)if(typeof issue.id==='string'&&Array.isArray(issue.issues)&&issue.issues.length&&issue.issues.every(text=>typeof text==='string'))issuesById.set(issue.id,issue);
  if(location.hash.startsWith('#item=')){try{annotate(decodeURIComponent(location.hash.slice(6)));}catch{}}
 }).catch(()=>{});
})();

