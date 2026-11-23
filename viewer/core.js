(function (root) {
  'use strict';
  const labels = {multi_metric:'多项数据靠前',lower_bound_review:'数据模糊',single_metric_backup:'一项数据靠前'};
  const statuses = ['未复查','保留','淘汰','待确认'];
  function key(r) { return JSON.stringify([r.platform,r.content_id]); }
  function parse(text) {
    const seen = new Set();
    const rows = text.replace(/^\uFEFF/,'').split(/\r?\n/).flatMap((line,i) => {
      if (!line.trim()) return [];
      let r; try { r=JSON.parse(line); } catch { throw Error(`第 ${i+1} 行不是有效 JSON`); }
      if (!r || !['douyin','xiaohongshu','bilibili'].includes(r.platform) || typeof r.content_id!=='string' || !r.content_id || typeof r.title!=='string' || !r.title.trim()) throw Error(`第 ${i+1} 行缺少平台、字符串 content_id 或标题`);
      if (seen.has(key(r))) throw Error(`第 ${i+1} 行的平台和视频 ID 重复，请先去重`);
      seen.add(key(r)); return [r];
    });
    if (!rows.length) throw Error('文件中没有视频记录');
    return rows;
  }
  function identity(rows) {
    // Include observation time and values: different snapshots must not share review notes.
    return JSON.stringify(rows.map(r=>[r.platform,r.content_id,r.captured_at||'',r.metrics||{},r.metrics_display||{}]).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b))));
  }
  function safeURL(r) {
    try {
      const u=new URL(r.url); const domains={douyin:['douyin.com'],xiaohongshu:['xiaohongshu.com','xhslink.com'],bilibili:['bilibili.com','b23.tv']}[r.platform]||[];
      return u.protocol==='https:' && !u.username && !u.password && domains.some(d=>u.hostname===d||u.hostname.endsWith('.'+d)) ? u.href : null;
    } catch {return null;}
  }
  function validateReview(doc,dataset,rows) {
    if (doc?.schema_version!=='food_review_v1'||doc.dataset_id!==dataset||!Array.isArray(doc.reviews)) throw Error('这份复查文件不属于当前数据，或格式不正确');
    const allowed=new Set(rows.map(key)), out=Object.create(null);
    for (const r of doc.reviews) {
      if (!r || !allowed.has(r.video_key)||!statuses.includes(r.status)||typeof r.note!=='string'||r.note.length>10000||Object.hasOwn(out,r.video_key)) throw Error('复查记录有重复、未知视频或无效标记');
      out[r.video_key]={status:r.status,note:r.note,updated_at:typeof r.updated_at==='string'?r.updated_at:null};
    }
    return out;
  }
  const api={labels,statuses,key,parse,identity,safeURL,validateReview};
  if (typeof module!=='undefined'&&module.exports) module.exports=api; else root.FoodViewer=api;
})(globalThis);
