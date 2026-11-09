function citationForRecord(record){
 if(typeof record.citation==='string'&&record.citation.trim())return record.citation;
 return window.ATLAS_CITATION_SUPPLEMENTS?.records?.[record.id]?.citation||'参考引用待考：现有来源字段不足，尚未整理。';
}
function citationIsAssembled(record){
 return !record.citation?.trim()&&window.ATLAS_CITATION_SUPPLEMENTS?.records?.[record.id]?.status==='assembled-reference';
}
function recordForExport(record){
 const citation=window.ATLAS_CITATION_SUPPLEMENTS?.records?.[record.id],culture=window.ATLAS_CULTURE_NOTES?.records?.[record.id];
 return {...record,...(citation?{citationSupplement:citation}:{}),...(culture?{cultureNoteSupplement:culture}:{})};
}
