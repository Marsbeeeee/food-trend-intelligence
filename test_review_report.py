"""Draft report contracts: triage stays triage; frozen observations remain intact."""
import copy,json,unittest
from datetime import date
from pipeline.review_report import ROOT,build,validate,snapshots,link

class DraftReportTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'platform':'douyin','content_id':'7616299354227698021','title':'配方教程','author_name':'甲','url':'https://www.douyin.com/video/7531793800897826063/search/test?modal_id=7616299354227698021','captured_at':'2026-11-23T10:00:00+08:00','metrics':{'likes':None},'metrics_display':{'likes':'10万+'},'priority_label':'数据模糊','selection_reasons':['下限待确认']}]
        self.review={'schema_version':'food_review_v1','dataset_id':json.dumps(list(snapshots(self.rows).values())),'reviews':[{'video_key':json.dumps(['douyin','7616299354227698021']),'status':'保留','note':'','updated_at':'2026-11-23T07:00:00Z'}]}
        self.template=(ROOT/'视频热点情报周报_母版.md').read_text(encoding='utf-8')
        self.editorial={'archive_batch':'2026/1122','source_sample_count':1,'cases':{},'focus':[]}
    def render(self):
        return build(self.rows,self.review,self.editorial,date(2026,11,15),date(2026,11,21),'2026-11-22',self.template)
    def test_deterministic_and_unmodified(self):
        before=copy.deepcopy((self.rows,self.review));self.assertEqual(self.render(),self.render());self.assertEqual(before,(self.rows,self.review))
    def test_not_verified_and_precision_preserved(self):
        text,payload=self.render();self.assertEqual(payload['status'],'review_backed_draft');self.assertIn('10万+',text);self.assertIn('形式待补',text);self.assertNotIn('经核验情报 1',text);self.assertEqual(text.count('## 0'),8)
        self.assertNotIn('|\n\n|',text);self.assertIn('https://www.douyin.com/video/7616299354227698021',text)
    def test_snapshot_mismatch_rejected(self):
        self.rows[0]['metrics_display']['likes']='11万+';self.assertRaises(ValueError,validate,self.rows,self.review)
    def test_duplicate_reviews_rejected(self):
        self.review['reviews']*=2;self.assertRaises(ValueError,validate,self.rows,self.review)
    def test_nonretained_not_admitted(self):
        self.review['reviews'][0]['status']='淘汰';self.assertEqual(self.render()[1]['selected_count'],0)
    def test_no_invented_video_observations(self):
        self.editorial['cases']={'douyin:7616299354227698021':{'basis':'watched_video'}};self.assertRaises(ValueError,self.render)
    def test_douyin_identity_mismatch(self):
        self.rows[0]['content_id']='1234567890123456789';self.assertRaises(ValueError,link,self.rows[0])

if __name__=='__main__':unittest.main()
