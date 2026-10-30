/* Daily imports use the existing search and chronology filters. */
(()=>{
 const batch=window.ARCHIVE_DATA.dailyImports?.at(-1);if(!batch)return;
 const panel=document.createElement('aside');panel.className='daily-batch-summary';panel.setAttribute('aria-label','最新扩库');
 const text=document.createElement('span');text.textContent=batch.date+' 新增 '+batch.netNewImages+' 张真实图像，涉及 '+batch.newImageObjects+' 件藏品。';
 const label=document.createElement('label'),check=document.createElement('input');check.type='checkbox';check.id='dailyOnly';label.append(check,document.createTextNode('仅看本次新增'));
 const link=document.createElement('a');link.href='daily-'+batch.date+'.json.gz';link.textContent='下载本批出处清单';link.download='';
 panel.append(text,label,link);document.querySelector('#explore').before(panel);
 check.checked=new URLSearchParams(location.search).get('batch')===batch.date;state.batch=check.checked?batch.date:null;
 check.addEventListener('change',()=>{state.batch=check.checked?batch.date:null;state.limit=12;renderCards();document.querySelector('#explore').scrollIntoView({behavior:'smooth'});});
 renderCards();
})();
