'use strict';
const C=FoodViewer, $=id=>document.getElementById(id), platformNames={douyin:'抖音',xiaohongshu:'小红书',bilibili:'B站'};
let rows=[], reviews=Object.create(null), dataset='', filename='', current='', storageKey='';
const label=r=>C.labels[r.priority_tier]||r.priority_label||'未分类';
const review=r=>reviews[C.key(r)]||{status:'未复查',note:''};
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function platformPill(r){const n=el('span',platformNames[r.platform],'pill');n.setAttribute('data-platform',r.platform);return n;}
function statePill(r){const n=el('span',review(r).status,'state');n.setAttribute('data-status',review(r).status);return n;}
function notice(s,error=false){$('notice').textContent=s;$('notice').className=error?'error':'';}
function doc(){return {schema_version:'food_review_v1',dataset_id:dataset,source_file:filename,exported_at:new Date().toISOString(),reviews:Object.entries(reviews).map(([video_key,r])=>({video_key,...r}))};}
function save(){try{localStorage.setItem(storageKey,JSON.stringify(doc()));notice(`${filename} · 已在当前浏览器暂存，请定期导出备份。`);}catch{notice('浏览器无法暂存，请在关闭前导出复查记录。',true);}}
function filtered(){return rows.filter(r=>(!$('platform').value||r.platform===$('platform').value)&&(!$('tier').value||label(r)===$('tier').value)&&(!$('status').value||review(r).status===$('status').value)&&`${r.title} ${r.author_name||''} ${r.content_id}`.toLowerCase().includes($('search').value.toLowerCase().trim()));}
function renderList(){
 const visible=filtered();$('list').replaceChildren();
 for(const r of visible){const b=el('button',undefined,'item');b.type='button';b.setAttribute('aria-pressed',String(current===C.key(r)));const top=el('div',undefined,'item-top'),bottom=el('div',undefined,'item-bottom');top.append(platformPill(r),el('span',label(r),'meta'));bottom.append(el('span',r.author_name||'作者未知','meta'),statePill(r));b.append(top,el('strong',r.title),bottom);b.onclick=()=>{current=C.key(r);render();};$('list').append(b);}
 if(!visible.length)$('list').append(el('div','没有符合筛选条件的记录','empty'));
 const counts=Object.fromEntries(C.statuses.map(s=>[s,rows.filter(r=>review(r).status===s).length]));
 $('progress').textContent=rows.length?`显示 ${visible.length} / ${rows.length} · 保留 ${counts['保留']} · 淘汰 ${counts['淘汰']} · 待确认 ${counts['待确认']} · 未复查 ${counts['未复查']}`:'';
 return visible;
}
function render(){
 let visible=filtered();if(!visible.some(r=>C.key(r)===current))current=visible.length?C.key(visible[0]):'';renderList();
 const host=$('detail');host.replaceChildren();const r=rows.find(r=>C.key(r)===current);
 if(!r){host.append(el('div',rows.length?'没有符合筛选条件的记录':'请先打开候选 JSONL','empty'));return;}
 const badges=el('div',undefined,'badges');badges.append(platformPill(r),el('span',label(r),'badge'));host.append(badges,el('h2',r.title));
 const source=el('div',undefined,'source-row');source.append(el('div',`${r.author_name||'作者未知'} · ID ${r.content_id}`,'meta'));const link=C.safeURL(r);if(link){const a=el('a','打开原视频 ↗','source-link');a.href=link;a.target='_blank';a.rel='noopener noreferrer';source.append(a);}else source.append(el('span','原视频链接缺失或域名异常，已禁用。','warning'));host.append(source);
 host.append(el('p',`采集：${r.captured_at||'未记录'} ｜发布：${r.published_at||r.published_at_raw||'未知'}`,'snapshot'));
 const metrics=el('div',undefined,'metrics');
 for(const [k,name] of Object.entries({views:'播放',likes:'点赞',favorites:'收藏',comments:'评论',coins:'投币',shares:'分享'})){
  const observation=r.metric_observations?.[k], display=r.metrics_display?.[k]??observation?.display??r.metrics?.[k];
  if(display===null||display===undefined||display==='')continue;
  const card=el('div',undefined,'metric');card.append(el('div',name,'meta'),el('div',String(display),'value'));
  if(observation?.kind==='lower_bound')card.append(el('div','下限值 · 数据模糊','meta'));else if(observation?.kind==='approximate')card.append(el('div','平台显示约数','meta'));
  metrics.append(card);
 }host.append(metrics);
 const reason=el('div',undefined,'reason');reason.append(el('div','入选理由','eyebrow'),el('p',Array.isArray(r.selection_reasons)?r.selection_reasons.join('；'):'原始记录，尚无筛选理由'));host.append(reason);
 if(r.food_relevance==='unknown'||r.decision==='review')host.append(el('p','美食相关性需要确认。','warning'));
 if(Array.isArray(r.review_flags)&&r.review_flags.length)host.append(el('p',`待复查提示：${r.review_flags.join('；')}`,'warning'));
 const section=el('div',undefined,'review'),head=el('div',undefined,'review-head'), prompt=el('label','复查判断 '),select=el('select');head.append(el('strong','看完之后，留下判断'));select.id='decision';for(const s of C.statuses){const o=el('option',s);o.value=s;select.append(o);}select.value=review(r).status;select.setAttribute('data-status',select.value);prompt.append(select);head.append(prompt);
 const noteLabel=el('label','值得借鉴的地方，或不保留的原因','note-label'),note=el('textarea');note.id='note';note.maxLength=10000;note.value=review(r).note;note.placeholder='例如：开头先展示成品，再倒叙制作过程，值得参考。';noteLabel.htmlFor='note';
 function record(){reviews[C.key(r)]={status:select.value,note:note.value,updated_at:new Date().toISOString()};select.setAttribute('data-status',select.value);save();renderList();}
 // Keep the edited detail open until the user changes filters or clicks another item.
 select.onchange=record;note.oninput=record;section.append(head,noteLabel,note);host.append(section);
 const details=el('details'),summary=el('summary','查看完整记录');details.append(summary,el('pre',JSON.stringify(r,null,2)));host.append(details);
}
$('open').onclick=()=>$('file').click();$('restore').onclick=()=>$('reviewfile').click();
$('file').onchange=async e=>{
 const file=e.target.files[0];e.target.value='';if(!file)return;
 try{
  if(file.size>20*1024*1024)throw Error('文件超过20MB，请先拆分候选文件');
  const parsed=C.parse(await file.text()), id=C.identity(parsed);
  rows=parsed;dataset=id;filename=file.name;storageKey='food-review-v1:'+dataset;reviews=Object.create(null);current='';
  let saved;try{saved=localStorage.getItem(storageKey);}catch{}
  if(saved){try{reviews=C.validateReview(JSON.parse(saved),dataset,rows);}catch{notice('旧暂存无效，已忽略；可导入之前导出的复查文件。',true);}}
  for(const name of ['platform','tier','status','search'])$(name).value='';$('export').disabled=false;$('restore').disabled=false;render();notice(`${filename} · 共 ${rows.length} 条。复查记录仅暂存在当前浏览器，离开前请导出备份。`);
 }catch(err){notice(err.message,true);}
};
for(const id of ['platform','tier','status'])$(id).onchange=render;$('search').oninput=render;
$('export').onclick=()=>{const blob=new Blob([JSON.stringify(doc(),null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download=filename.replace(/\.[^.]+$/,'')+'_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('reviewfile').onchange=async e=>{const file=e.target.files[0];e.target.value='';if(!file)return;try{if(file.size>30*1024*1024)throw Error('复查文件过大');const imported=C.validateReview(JSON.parse(await file.text()),dataset,rows);reviews=imported;save();render();}catch(err){notice(err.message,true);}};
