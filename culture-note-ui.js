/* Supplemental notes never rewrite the original catalog or its review evidence. */
function cultureNoteHTML(record) {
 const note=window.ATLAS_CULTURE_NOTES?.records?.[record.id];
 if(!note)return '';
 if(note.status!=='official-original')return '<p class="disclosure">文化说明待考：已保存的馆方来源未提供可核对的叙述。</p>';
 const plain=part=>{if(part.format!=='html')return part.rawText;const template=document.createElement('template');template.innerHTML=part.rawText;template.content.querySelectorAll('script,style').forEach(n=>n.remove());return template.content.textContent||'';};
 return '<section class="detail-section"><h3>馆方原文说明</h3><p class="disclosure">保留官方原文，尚未翻译；不代表本库独立鉴定。</p>'+note.parts.map(p=>'<p class="official-narrative">'+esc(plain(p))+'</p>').join('')+'<a class="source-link" target="_blank" rel="noopener noreferrer" href="'+esc(note.sourceUrl)+'">核对馆方原始出处 ↗</a><p class="disclosure">元数据读取：'+esc(note.sourceCapturedAt||'日期未记录，待考')+' · 原记录核验：'+esc(note.verificationDate||'待考')+'</p></section>';
}

