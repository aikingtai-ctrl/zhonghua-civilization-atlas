/* Subject access points do not change source attribution or chronological evidence. */
function xixiaSubcategoryItems(){return window.ARCHIVE_DATA.xixia.visualTaxonomy?.items||[]}
function xixiaCategoryMatch(r,category){
 if(category==='all')return true;
 if(state.era!=='西夏'||r.era!=='西夏'||!r.visualSubcategories?.length)return r.category===category||(r.relatedCategories||[]).includes(category);
 return xixiaSubcategoryItems().some(s=>s.category===category&&r.visualSubcategories.includes(s.id));
}
function xixiaSubcategoryMatch(r,options={}){
 return state.era!=='西夏'||options.ignoreXixiaSubcategory||!state.xixiaSubtype||state.xixiaSubtype==='all'||r.visualSubcategories?.includes(state.xixiaSubtype);
}
function xixiaSubcategoryCaption(r){
 if(r.era!=='西夏')return '';
 const items=xixiaSubcategoryItems().filter(s=>r.visualSubcategories?.includes(s.id));
 const selected=items.find(s=>s.id===state.xixiaSubtype);
 const visible=selected?[selected]:items.filter(s=>state.category==='all'||s.category===state.category).slice(0,2);
 return visible.length?'<p class="xixia-subject-caption">'+visible.map(s=>esc(s.label)).join(' · ')+'</p>':'';
}
function renderXixiaSubcategories(){
 let host=$('#xixiaSubcategories');
 if(!host){host=document.createElement('section');host.id='xixiaSubcategories';host.className='xixia-subcategories';host.setAttribute('aria-label','按图像内容细分');$('.filter-line').after(host)}
 host.hidden=state.era!=='西夏';if(host.hidden)return;
 const items=xixiaSubcategoryItems(),active=items.find(s=>s.id===state.xixiaSubtype),list=items.filter(s=>s.category===state.category);
 if(!list.length){host.innerHTML='<div class="xixia-subcategory-intro"><strong>按画面内容，继续细分</strong><span>选择上方主题，展开 '+items.length+' 个子类中的对应分类。</span></div>';return}
 const pool=filtered({ignoreXixiaSubcategory:true});
 const selected=active?.category===state.category?active.id:'all';
 const button=(id,label,count)=>'<button data-xixia-subcategory="'+esc(id)+'" aria-pressed="'+(id===selected)+'" class="'+(id===selected?'selected':'')+'"><span>'+esc(label)+'</span><b>'+count+'</b></button>';
 host.innerHTML='<div class="xixia-subcategory-heading"><strong>'+esc(state.category)+' · 细分</strong><span>数字为当前年代与筛选下的图像数</span></div><div class="xixia-subcategory-options" role="group" aria-label="'+esc(state.category)+'子分类">'+button('all','全部子类',pool.length)+list.map(s=>button(s.id,s.label,pool.filter(r=>r.visualSubcategories?.includes(s.id)).length)).join('')+'</div><p class="xixia-subcategory-note">'+esc(active?.description||'按主体与可见细节归类。同图可归入多个子类，全部结果自动去重。')+'</p>';
}
function renderXixiaSubcategoryDetail(r){
 if(r.era!=='西夏')return;
 const items=xixiaSubcategoryItems().filter(s=>r.visualSubcategories?.includes(s.id));
 if(!items.length)return;
 const host=document.createElement('section');host.className='detail-section xixia-subcategory-detail';
 host.innerHTML='<h3>图像子分类</h3><div>'+items.map(s=>'<button data-xixia-browse-subcategory="'+esc(s.id)+'">'+esc(s.category)+' / '+esc(s.label)+' ↗</button>').join('')+'</div><p>按图像内容建立检索入口，原始断代与出处保留。</p>';
 $('#detailContent .description')?.after(host);
}
document.addEventListener('click',event=>{
 const b=event.target.closest('button');if(!b)return;
 if(b.hasAttribute('data-xixia-subcategory')){
  const id=b.dataset.xixiaSubcategory;
  if(id!=='all'&&!xixiaSubcategoryItems().some(s=>s.id===id&&s.category===state.category))return;
  state.xixiaSubtype=id;state.limit=24;state.xixiaRelatedLimit=12;renderCards();
  $('#xixiaSubcategories [data-xixia-subcategory="'+id+'"]')?.focus({preventScroll:true});
 }
 if(b.dataset.xixiaBrowseSubcategory){
  const s=xixiaSubcategoryItems().find(s=>s.id===b.dataset.xixiaBrowseSubcategory);if(!s)return;
  $('#closeDialog').click();if(state.era!=='西夏')selectEra('西夏',null,false);
  state.category=s.category;state.xixiaSubtype=s.id;state.limit=24;state.xixiaRelatedLimit=12;renderCards();
  $('#xixiaSubcategories').scrollIntoView({behavior:'smooth',block:'center'});
 }
});
