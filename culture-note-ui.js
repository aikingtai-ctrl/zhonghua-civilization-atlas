/* Supplemental notes never rewrite the original catalog or its review evidence. */
function cultureNoteURL(value) {
 try { const url=new URL(value);return url.protocol==='https:'&&!url.username&&!url.password?url.href:null; } catch { return null; }
}
function cultureReviewTime(value) {
 if(typeof value!=='string'||!/^\d{4}-\d{2}-\d{2}(?:T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2}))?$/.test(value))return NaN;
 const day=Date.parse(value.slice(0,10)+'T00:00:00Z');
 if(!Number.isFinite(day)||new Date(day).toISOString().slice(0,10)!==value.slice(0,10))return NaN;
 // Date-only review receipts use the project's Shanghai calendar day.
 return Date.parse(value.length===10?value+'T00:00:00+08:00':value);
}
function cultureLegacyText(part) {
 if(part.format!=='html')return part.rawText;
 // Preserve the pre-supplement display conversion only for historical notes.
 // The inert template is never attached to the document; output is escaped.
 const template=document.createElement('template');template.innerHTML=part.rawText;
 template.content.querySelectorAll('script,style').forEach(node=>node.remove());
 return template.content.textContent||'';
}
function cultureNoteV2For(note,record) {
 const text=value=>typeof value==='string'&&Boolean(value.trim()),sha=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
 const rules={
  mia:{institutions:['Minneapolis Institute of Art'],policyId:'mia-metadata-cc0-v1',url:'https://raw.githubusercontent.com/artsmia/collection/dd0c7ead54dc1a593ff119cf659629b0225d7610/readme.md',sha:'af607c55415b0ffb5a495645043d2b503eba4786ce9b1ba44de3a58a9156e9d4',fields:['text']},
  cma:{institutions:['克利夫兰艺术博物馆'],policyId:'cma-metadata-cc0-v1',url:'https://raw.githubusercontent.com/ClevelandMuseumArt/openaccess/a06b18208d99352b57c196c659f0407b21b28e07/README.md',sha:'a526fa5dedfa7fade96faac06499f4cf72407671cf6ba5d9c4aa529181af5bb7',fields:['description','did_you_know']},
  si:{institutions:['史密森尼国家亚洲艺术博物馆','史密森尼库珀·休伊特设计博物馆'],policyId:'si-metadata-cc0-v1',url:'https://raw.githubusercontent.com/Smithsonian/OpenAccess/c2ac3e2a671755e03e1ec439ad7b9b0020636281/README.md',sha:'005707b61d6747b008a87e52aac85c3fd72df873500052e89c37ba90328bb87e'}
 };
 if(!Object.hasOwn(rules,note.provider))return null;
 const rule=rules[note.provider],review=note.narrativeReview,license=note.textLicense,old=note.history?.[0],image=record.verification?.sha256||record.imageSha256;
 if(!rule.institutions.includes(record.institution)||note.id!==record.id||String(note.sourceRecordId)!==String(record.sourceRecordId)||!sha(note.sourceSnapshotSha256)||!sha(note.sourceRecordSha256)||note.sourceRecordSha256!==record.sourceRecordSha256||!sha(note.imageSha256)||note.imageSha256!==image)return null;
 if(record.imageSha256&&record.verification?.sha256&&record.imageSha256!==record.verification.sha256)return null;
 if(note.sourceEvidence!==record.sourceEvidence||!cultureNoteURL(note.sourceUrl)||note.sourceUrl!==record.sourceUrl||(note.metadataUrl??null)!==(record.apiUrl||null)||note.metadataUrl&&!cultureNoteURL(note.metadataUrl))return null;
 if(license?.provider!==note.provider||license.policyId!==rule.policyId||license.code!=='CC0-1.0'||license.url!=='https://creativecommons.org/publicdomain/zero/1.0/'||license.scope!=='馆方说明文字（元数据）；图像许可另列'||license.policyUrl!==rule.url||license.policySha256!==rule.sha)return null;
 if(note.provider==='si'&&(note.metadataLicenseEvidence?.fieldPath!=='content.descriptiveNonRepeating.metadata_usage.access'||note.metadataLicenseEvidence.value!=='CC0'||note.metadataLicenseEvidence.sourceRecordSha256!==record.sourceRecordSha256))return null;
 if(!['ai','human'].includes(review?.reviewerType)||review.metadataOnly!==true||!text(review.reviewedBy)||!text(review.method)||!sha(review.manifestSha256)||!sha(review.reviewSha256)||!Number.isFinite(cultureReviewTime(review.reviewedAt))||cultureReviewTime(review.reviewedAt)>Date.now())return null;
 if(note.history?.length!==1||old?.status!=='pending-research'||old.transition!=='approved-source-narrative-v2'||!sha(old.sha256)||old.sha256!==review.previousNoteSha256||old.entry?.id!==record.id||old.entry.status!=='pending-research'||!Array.isArray(old.entry.parts)||old.entry.parts.length!==0)return null;
 const fields=new Set();
 for(const part of note.parts){
  if(fields.has(part.field)||!sha(part.rawSha256)||!text(part.displayText)||part.displayTextPolicyVersion!=='official-narrative-text-v2'||!['text','html'].includes(part.format)||part.language!=='und'||part.languageHint!=='en'||part.languageNote!=='馆方未提供语言代码；AI识别为英语，未翻译。')return null;
  if(note.provider==='si'){if(!/^content\.freetext\.notes\[\d+\]\.content$/.test(part.field)||!/^(Description|Summary|Label Text|Gallery Label)$/i.test(part.sourceLabel||''))return null;}
  else if(!rule.fields.includes(part.field))return null;
  fields.add(part.field);
 }
 return note;
}
function cultureNoteFor(record) {
 const note=window.ATLAS_CULTURE_NOTES?.records?.[record.id];
 const text=value=>typeof value==='string'&&Boolean(value.trim()),sha=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
 if(!note||note.status!=='official-original'||!Array.isArray(note.parts)||!note.parts.length||note.parts.some(part=>!part||!text(part.rawText)))return null;
 // Existing supplements retain their original contract. New bound notes fail
 // closed rather than attaching a narrative to a changed object or image.
 if(note.schemaVersion===undefined)return Object.hasOwn(note,'imageSha256')||Object.hasOwn(note,'textLicense')||Object.hasOwn(note,'narrativeReview')||note.parts.some(part=>part.displayTextPolicyVersion==='mia-narrative-text-v1')?null:note;
 if(note.schemaVersion==='narrative-supplement-v2')return cultureNoteV2For(note,record);
 if(note.schemaVersion!=='narrative-supplement-v1')return null;
 const imageSha=record.verification?.sha256||record.imageSha256,license=note.textLicense,review=note.narrativeReview;
 if(record.institution!=='Minneapolis Institute of Art'||!Number.isSafeInteger(Number(note.sourceRecordId))||Number(note.sourceRecordId)<1||note.id!=='mia-'+note.sourceRecordId||String(note.sourceRecordId)!==String(record.sourceRecordId)||!sha(note.sourceSnapshotSha256))return null;
 if(note.id!==record.id||!sha(note.sourceRecordSha256)||note.sourceRecordSha256!==record.sourceRecordSha256||!sha(note.imageSha256)||note.imageSha256!==imageSha||record.imageSha256&&record.verification?.sha256&&record.imageSha256!==record.verification.sha256)return null;
 if(!cultureNoteURL(note.sourceUrl)||note.sourceUrl!==record.sourceUrl||!cultureNoteURL(note.metadataUrl)||note.metadataUrl!==record.apiUrl)return null;
 if(note.parts.some(part=>part.field!=='text'||!sha(part.rawSha256)||!['text','html'].includes(part.format)||!text(part.displayText)||part.displayTextPolicyVersion!=='mia-narrative-text-v1'||part.language!=='und'||part.languageHint!=='en'||part.languageNote!=='馆方未提供语言代码；AI识别为英语，未翻译。'))return null;
 if(license?.code!=='CC0-1.0'||license.url!=='https://creativecommons.org/publicdomain/zero/1.0/'||license.scope!=='馆方说明文字（元数据）；图像许可另列'||license.policyUrl!=='https://raw.githubusercontent.com/artsmia/collection/dd0c7ead54dc1a593ff119cf659629b0225d7610/readme.md'||license.policySha256!=='af607c55415b0ffb5a495645043d2b503eba4786ce9b1ba44de3a58a9156e9d4')return null;
 if(!['ai','human'].includes(review?.reviewerType)||review.metadataOnly!==true||!text(review.reviewedBy)||!sha(review.manifestSha256)||!sha(review.reviewSha256)||!text(review.method)||!Number.isFinite(cultureReviewTime(review.reviewedAt))||cultureReviewTime(review.reviewedAt)>Date.now())return null;
 return note;
}
function recordSummaryText(record) {
 if(typeof record.description==='string'&&record.description.trim())return record.description;
 return cultureNoteFor(record)
  ?'馆方已提供原文说明，见下方；原语保留，尚未翻译。'
  :'文化说明待考：尚未取得可核对的馆方叙述。';
}
function cultureNoteHTML(record) {
 const note=cultureNoteFor(record);if(!note)return '';
 const link=(url,label)=>{const safe=cultureNoteURL(url);return safe?'<a class="source-link" target="_blank" rel="noopener noreferrer" href="'+esc(safe)+'">'+esc(label)+' ↗</a>':'';};
 const bound=['narrative-supplement-v1','narrative-supplement-v2'].includes(note.schemaVersion);
 const parts=note.parts.map(part=>{
  const display=bound?part.displayText:cultureLegacyText(part);
  return (part.languageNote?'<p class="disclosure culture-language">语言：'+esc(part.languageNote)+'</p>':'')+'<p class="official-narrative"'+(bound&&part.languageHint==='en'?' lang="en"':'')+'>'+esc(display)+'</p>';
 }).join('');
 const links=[link(note.sourceUrl,'核对馆方原始出处'),link(note.metadataUrl,'馆方元数据')].filter(Boolean);
 if(bound){links.push(link(note.textLicense.url,'馆方说明文字许可：'+note.textLicense.code),link(note.textLicense.policyUrl,'馆方元数据许可政策'));}
 const capture=typeof note.sourceCapturedAt==='string'&&note.sourceCapturedAt.trim()?note.sourceCapturedAt:'未记录，待考';
 const original=typeof note.verificationDate==='string'&&note.verificationDate.trim()?note.verificationDate:'未记录，待考';
 const review=(note.schemaVersion==='narrative-supplement-v2'&&note.provider==='si'?'<p class="disclosure">馆方逐对象元数据标记：CC0；图像许可另列。</p>':'')+(bound?'<p class="disclosure">文字核对：'+(note.narrativeReview.reviewerType==='human'?'人工':'AI')+' · '+esc(note.narrativeReview.reviewedAt)+'；仅核对来源说明，图像审核保持原记录。</p>':'');
 return '<section class="detail-section culture-note"><h3>馆方原文说明</h3><p class="disclosure">保留馆方原文，未翻译；不代表本库独立鉴定。</p><details class="culture-note-expand"><summary>馆方原文 · 未翻译</summary>'+parts+'</details><div class="culture-note-links">'+links.join(' · ')+'</div>'+(bound?'<p class="disclosure">'+esc(note.textLicense.scope)+'</p>':'<p class="disclosure">说明文字许可未在此补充记录中确认；图像许可另列。</p>')+'<p class="disclosure">'+(note.schemaVersion==='narrative-supplement-v2'?'来源快照所记日期：':'来源元数据读取：')+esc(capture)+' · 原记录核验日期：'+esc(original)+'（保留旧记录日期）</p>'+review+'<p class="disclosure">本节仅补充来源文字，不增加入库数量，不改变原有入库、发布日期或审核结论。</p></section>';
}

