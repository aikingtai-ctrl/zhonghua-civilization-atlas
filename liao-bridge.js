/* Liao visual dossiers are kept distinct from strictly dated chronology results. */
(()=>{'use strict';
const data=window.LIAO_DATA;if(!data)return;
const box=document.createElement('section');box.id='liaoVisualDossier';box.className='liao-visual-dossier';box.hidden=true;document.querySelector('#chronologySelection').after(box);
const byId=new Map(data.records.map(r=>[r.id,r]));
function sync(){
 box.hidden=state.era!=='辽'||state.polity==='西辽';if(box.hidden)return;
 const node=chronologyNodes.get(state.chronoId);const rulerId=node?.kind==='ruler'?node.id:'ruler-'+node?.rulerId;const p=node?.id==='dila-era-815'?data.rulers.find(r=>r.id==='liao-foundation'):data.rulers.find(r=>r.id!=='liao-foundation'&&r.chronologyRulerId===rulerId);
 const reign=p?.reigns.find(e=>e.id===node?.id);const url='liao.html'+(p?'#ruler='+encodeURIComponent(p.id)+(reign?'&reign='+encodeURIComponent(reign.id):''):'');
 const refs=(p?.referenceIds||data.overview.referenceIds).map(id=>byId.get(id)).filter(Boolean);
 box.innerHTML='<div class="liao-bridge-heading"><div><small>辽代专属图库 · '+data.records.length+' 张独立图像</small><h3>'+esc(p?p.label+(reign?' · '+reign.label:'')+'的视觉参考':'辽代各时期 · 人物、器物、壁画与营造')+'</h3></div><a class="primary" href="'+url+'">进入辽代专题 →</a></div><p>'+esc(p?p.summary:'覆盖九位皇帝，另列建国前史与过渡时期。每个入口均提供具体画面、年代说明和原始出处。')+'</p>'+ (p?'<div class="liao-bridge-refs">'+refs.slice(0,4).map(r=>{const l=r.rulerLinks?.find(l=>l.id===p.id);return '<a href="liao.html#ruler='+encodeURIComponent(p.id)+'&item='+encodeURIComponent(r.id)+'"><img src="'+esc(r.previewUrl||r.thumbnailUrl||r.imageUrl)+'" alt="'+esc(r.title)+'" loading="lazy" referrerpolicy="no-referrer"><b>'+esc(r.title)+'</b><small>'+esc(reign?'本执政时期参考 · 年号归属见详情':l?.relation==='direct'?'有本期断代依据':'跨期／形制参考')+'</small></a>'}).join('')+'</div>':'<div class="liao-bridge-periods">'+data.rulers.map(r=>'<a href="liao.html#ruler='+encodeURIComponent(r.id)+'">'+esc(r.label)+'<small>'+r.start+'—'+r.end+'</small></a>').join('')+'</div>')+'<p class="liao-bridge-note">'+esc(p?.notes||data.scopePolicy)+'</p>';
}
const render=renderCards;renderCards=function(...args){const result=render.apply(this,args);sync();return result};
const chron=renderChronology;renderChronology=function(...args){const result=chron.apply(this,args);const root=document.querySelector('#eraList [data-era="辽"]')?.closest('.chron-branch')?.querySelector('.chron-children');if(root&&!root.querySelector('[data-liao-entry]'))root.insertAdjacentHTML('afterbegin','<a class="chron-option whole" data-liao-entry href="liao.html">辽代专属图库 · '+data.records.length+' 图 ↗</a>');return result};
const oldDetail=detail;detail=function(id){const r=byId.get(id);if(r){location.href='liao.html#item='+encodeURIComponent(id);return}return oldDetail(id)};
if(location.hash==='#liao')location.replace('liao.html');renderChronology();sync();
})();
