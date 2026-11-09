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

