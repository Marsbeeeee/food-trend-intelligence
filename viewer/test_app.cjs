// DOM-level interaction checks; browser appearance is checked separately.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),C=require('./core.js');
class Element {
 constructor(tag){this.tagName=tag;this.children=[];this.value='';this.textContent='';this.files=[];this.disabled=true;this.attributes={};}
 append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=nodes;}setAttribute(k,v){this.attributes[k]=v;}click(){}
}
const ids=['open','export','restore','progress','notice','file','reviewfile','platform','tier','status','search','list','detail'];
const elements=Object.fromEntries(ids.map(k=>[k,new Element('div')])),storage=new Map();
const document={getElementById:id=>elements[id],createElement:tag=>new Element(tag)};
vm.runInNewContext(fs.readFileSync(__dirname+'/app.js','utf8'),{FoodViewer:C,document,localStorage:{setItem:(k,v)=>storage.set(k,v),getItem:k=>storage.get(k)||null},URL,Blob,setTimeout,Date,console});
function find(root,id){if(root.id===id)return root;for(const n of root.children){const match=find(n,id);if(match)return match;}}
(async()=>{
 const original=fs.readFileSync('data/2026/1122/priority_36.jsonl','utf8'),file={name:'priority_36.jsonl',size:Buffer.byteLength(original),text:async()=>original};
 assert.equal(elements.restore.disabled,false);
 const pending={schema_version:'food_review_v1',dataset_id:C.identity(C.parse(original)),source_file:file.name,reviews:[]};
 elements.reviewfile.files=[{size:100,text:async()=>JSON.stringify(pending)}];await elements.reviewfile.onchange({target:elements.reviewfile});assert(elements.notice.textContent.includes('请先打开对应候选文件'));
 elements.file.files=[file];await elements.file.onchange({target:elements.file});assert.equal(elements.list.children.length,36);assert.equal(elements.export.disabled,false);
 assert(elements.notice.textContent.includes('已恢复 0 条'));
 elements.platform.value='xiaohongshu';elements.platform.onchange();assert.equal(elements.list.children.length,12);
 elements.tier.value='数据模糊';elements.tier.onchange();assert.equal(elements.list.children.length,3);
 const decision=find(elements.detail,'decision'),note=find(elements.detail,'note');decision.value='待确认';decision.onchange();note.value='测试笔记：先核对下限值';note.oninput();
 const saved=JSON.parse([...storage.values()][0]);assert.equal(saved.reviews.length,1);assert.equal(saved.reviews[0].status,'待确认');assert.equal(saved.reviews[0].note,note.value);
 elements.file.files=[file];await elements.file.onchange({target:elements.file});assert(elements.progress.textContent.includes('待确认 1'));
 const invalid={name:'bad.jsonl',size:10,text:async()=>'{broken'};elements.file.files=[invalid];await elements.file.onchange({target:elements.file});assert.equal(elements.notice.className,'error');assert.equal(elements.list.children.length,36);
 assert.equal(fs.readFileSync('data/2026/1122/priority_36.jsonl','utf8'),original);
 if(process.argv[2]){
  const text=fs.readFileSync(process.argv[2],'utf8'),doc=JSON.parse(text.replace(/^\uFEFF/,''));
  elements.reviewfile.files=[{size:Buffer.byteLength(text),text:async()=>text}];await elements.reviewfile.onchange({target:elements.reviewfile});assert(elements.notice.textContent.includes(`已恢复 ${doc.reviews.length} 条`));
  const restored=JSON.parse([...storage.values()][0]);assert.deepEqual(restored.reviews,doc.reviews);
  elements.file.files=[{name:'priority_36_review.json',size:Buffer.byteLength(text),text:async()=>text}];await elements.file.onchange({target:elements.file});assert(elements.notice.textContent.includes(`已恢复 ${doc.reviews.length} 条`));
  console.log(`Actual review backup restored: ${doc.reviews.length} records, statuses and notes unchanged.`);
 }
 console.log('App interaction checks passed: import, platform/label filtering, notes, storage restore, bad-file recovery; source unchanged.');
})().catch(e=>{console.error(e);process.exitCode=1;});
