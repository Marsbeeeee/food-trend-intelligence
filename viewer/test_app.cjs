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
 elements.file.files=[file];await elements.file.onchange({target:elements.file});assert.equal(elements.list.children.length,36);assert.equal(elements.export.disabled,false);
 elements.platform.value='xiaohongshu';elements.platform.onchange();assert.equal(elements.list.children.length,12);
 elements.tier.value='数据模糊';elements.tier.onchange();assert.equal(elements.list.children.length,3);
 const decision=find(elements.detail,'decision'),note=find(elements.detail,'note');decision.value='待确认';decision.onchange();note.value='测试笔记：先核对下限值';note.oninput();
 const saved=JSON.parse([...storage.values()][0]);assert.equal(saved.reviews.length,1);assert.equal(saved.reviews[0].status,'待确认');assert.equal(saved.reviews[0].note,note.value);
 elements.file.files=[file];await elements.file.onchange({target:elements.file});assert(elements.progress.textContent.includes('待确认 1'));
 const invalid={name:'bad.jsonl',size:10,text:async()=>'{broken'};elements.file.files=[invalid];await elements.file.onchange({target:elements.file});assert.equal(elements.notice.className,'error');assert.equal(elements.list.children.length,36);
 assert.equal(fs.readFileSync('data/2026/1122/priority_36.jsonl','utf8'),original);
 console.log('App interaction checks passed: import, platform/label filtering, notes, storage restore, bad-file recovery; source unchanged.');
})().catch(e=>{console.error(e);process.exitCode=1;});
