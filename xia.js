function xiaMatches(r){
 if(state.view!=='xia')return true;
 return (state.xiaTopic==='all'||(r.xiaTopics||[]).includes(state.xiaTopic))&&(state.xiaScope==='all'||r.xiaScope===state.xiaScope);
}
function renderXiaFilters(){
 if(!$('#xiaTopics'))return;
 $$('[data-xia-topic]').forEach(b=>{b.classList.toggle('selected',b.dataset.xiaTopic===state.xiaTopic);b.setAttribute('aria-pressed',String(b.dataset.xiaTopic===state.xiaTopic))});
 if($('#xiaScope'))$('#xiaScope').value=state.xiaScope||'all';
}
function xiaDetail(r){
 if(!r.xiaScope)return '';
 return '<section class="detail-section xia-verification"><h3>资料层次与核验</h3><p><b>'+esc(r.xiaScope)+'</b> · '+esc(r.xiaTopics?.join('、'))+'</p><p>'+esc(r.datingBasis)+'</p><p>'+esc(r.verificationText)+'</p>'+(r.caption?'<p><b>原图定位：</b>'+esc(r.caption)+'</p>':'')+(r.collection?'<p><b>收藏著录：</b>'+esc(r.collection)+'</p>':'')+(r.relatedImageIds||[]).map(id=>'<p><button class="secondary" data-detail="'+esc(id)+'">查看关联图像：'+esc(records.find(x=>x.id===id)?.title||id)+' ↗</button></p>').join('')+'</section>';
}
function initXia(){
 const x=window.ARCHIVE_DATA.xia;if(!x)return;
 const list=records.filter(r=>r.era==='夏／二里头文化');
 $('#xiaStats').innerHTML=[['有源图像记录',list.length],['来源页面',new Set(list.map(r=>r.sourceUrl)).size],['书目与研究入口',x.bibliography.length],['原图出处', '逐图']].map(([label,n])=>'<span><b>'+n+'</b>'+label+'</span>').join('');
 $('#xiaTopics').innerHTML=['all',...x.topics].map(t=>'<button data-xia-topic="'+esc(t)+'"><strong>'+esc(t==='all'?'全部图像':t)+'</strong><small>'+list.filter(r=>t==='all'||r.xiaTopics?.includes(t)).length+' 条</small></button>').join('');
 $('#xiaScope').innerHTML='<option value="all">全部资料层次</option>'+[...new Set(list.map(r=>r.xiaScope))].map(t=>'<option>'+esc(t)+'</option>').join('');
 $('#xiaScope').onchange=e=>{state.xiaScope=e.target.value;state.limit=12;renderCards()};
 $('#xiaPdfFigures').innerHTML=x.pdfFigures.map(r=>xixiaResearchCard({...r,notes:r.limits,imprint:r.period+' · '+r.locator})).join('');
 const renderBooks=()=>{const q=$('#xiaBookSearch').value.trim().toLowerCase();const books=x.bibliography.filter(b=>JSON.stringify(b).toLowerCase().includes(q));$('#xiaBookCount').textContent='显示 '+books.length+' / '+x.bibliography.length+' 项；仅有书目者不计作已收图版。';$('#xiaBibliography').innerHTML=books.map(b=>xixiaResearchCard({...b,imprint:b.imprint||[b.author,b.publication].filter(Boolean).join(' · ')})).join('')};
 $('#xiaBookSearch').oninput=renderBooks;renderBooks();
 $('#xiaSources').innerHTML=x.sources.map(s=>'<article class="research-card"><div class="research-kicker">'+esc(s.institution||'来源核验')+'</div><h3>'+esc(s.title)+'</h3><p>'+esc(s.summary||s.notes||'')+'</p>'+xixiaLink(s.url,'打开原始出处 ↗')+'</article>').join('');
 $('#xiaGaps').innerHTML=x.gaps.map(g=>typeof g==='string'?'<li>'+esc(g)+'</li>':'<li><b>'+esc(g.title||g.topic)+'</b> '+esc(g.notes||g.reason||g.description||g.status||'')+(g.url?' '+xixiaLink(g.url):'')+'</li>').join('');
 $('#xiaCoverage').innerHTML=x.coverage.map(c=>'<article><h3>'+esc(c.title)+'</h3><p>'+esc(c.note)+'</p></article>').join('');
 $('#xiaExport').onclick=()=>download(JSON.stringify({...x,records:list,count:list.length},null,2),'夏专属图库-图像与文献资料包.json');
}
document.addEventListener('click',e=>{const b=e.target.closest('[data-xia-topic]');if(!b)return;state.xiaTopic=b.dataset.xiaTopic;state.limit=12;renderCards()});
