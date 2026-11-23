from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.policy import load_policy
"""Multi-metric shortlist behavior; no live collection or content verification."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from pipeline.priority import prioritize

POLICY = load_policy()


def record(i, platform='douyin', author=None):
    return {'record_id': platform+str(i), 'platform': platform, 'content_id': str(i),
            'title': '美食测试', 'url': 'https://example.com/video/'+str(i), 'author_id': author or str(i),
            'author_name': author or str(i), 'decision': 'keep', 'metrics_display': {},
            'metrics': {name: i+1 for name in ('views','likes','favorites','coins','shares','comments')}}


class PriorityTests(unittest.TestCase):
    def setUp(self):
        self.records = [record(i) for i in range(60)]

    def test_primary_top_twenty_percent_and_cap(self):
        result = prioritize(self.records, POLICY)
        self.assertEqual(len(result['selected']), 12)
        self.assertEqual({r['content_id'] for r in result['selected']}, {str(i) for i in range(48,60)})
        self.assertTrue(all(r['priority_tier']=='multi_metric' and r['primary_hit_count']==3 for r in result['selected']))
        self.assertEqual(result['summary']['platforms']['douyin']['not_highlighted'], 48)

    def test_comments_alone_do_not_qualify(self):
        self.records[0]['metrics']['comments'] = 100000000
        result = prioritize(self.records, POLICY)
        self.assertNotIn('0', {r['content_id'] for r in result['selected']+result['reserve']})

    def test_approximate_counts_participate_without_rewriting_exact_metrics(self):
        for i, r in enumerate(self.records):
            for name in ('likes','favorites','shares'):
                r['metrics'][name] = None
                r['metrics_display'][name] = str(i+1)+'万'
        result = prioritize(self.records, POLICY)
        self.assertEqual(len(result['selected']), 12)
        self.assertTrue(all(r['metrics']['likes'] is None for r in result['selected']))
        self.assertEqual(result['selected'][0]['metric_observations']['likes']['comparison_value'],600000)

    def test_lower_bound_is_manual_not_fabricated_rank(self):
        bound = record(100)
        for name in ('likes','favorites'):
            bound['metrics'][name]=None; bound['metrics_display'][name]='10万+'
        bound['metrics']['shares']=0
        result = prioritize(self.records+[bound], POLICY)
        row = next(r for r in result['needs_review'] if r['content_id']=='100')
        self.assertEqual(row['priority_tier'],'lower_bound_review')
        self.assertEqual(row['primary_hit_count'],0)
        self.assertTrue(all(e['coarse_sample_rank'] is None for e in row['metric_evidence'] if e['kind']=='lower_bound'))

    def test_cutoff_ties_are_shared_and_flagged(self):
        rows = [record(i) for i in range(10)]
        for r, value in zip(rows, [1,2,3,4,5,6,7,8,8,10]):
            for name in ('likes','favorites','shares'): r['metrics'][name]=value
        result=prioritize(rows,POLICY)
        self.assertEqual(len(result['selected']),3)
        tied=[r for r in result['selected'] if r['metrics']['likes']==8]
        self.assertEqual(len(tied),2)
        self.assertTrue(all(r['metric_evidence'][0]['coarse_sample_rank']==2 for r in tied))
        self.assertTrue(all(r['review_flags'] for r in tied))

    def test_author_cap_does_not_delete_other_candidates(self):
        rows = [record(i,author='same-author') for i in range(60)]
        result=prioritize(rows,POLICY)
        self.assertEqual(len(result['selected']),2)
        self.assertEqual(len(result['reserve']),10)
        self.assertTrue(all(r['not_selected_reason']=='author_limit' for r in result['reserve']))

    def test_platforms_are_independent_and_cap_is_per_platform(self):
        rows=[record(i,platform) for platform in ('douyin','xiaohongshu','bilibili') for i in range(60)]
        result=prioritize(rows,POLICY)
        self.assertEqual(len(result['selected']),36)
        self.assertEqual({p:v['selected'] for p,v in result['summary']['platforms'].items()},
                         {'douyin':12,'xiaohongshu':12,'bilibili':12})

    def test_unknown_relevance_kept_for_review(self):
        self.records[-1]['decision']='review'
        result=prioritize(self.records,POLICY)
        row=next(r for r in result['needs_review'] if r['content_id']=='59')
        self.assertIn('food_relevance_uncertain',row['review_flags'])
        self.assertIn(row['record_id'],{r['record_id'] for r in result['selected']+result['reserve']})

    def test_single_metric_backups_are_labeled(self):
        rows=[record(i) for i in range(10)]
        for i,r in enumerate(rows):
            r['metrics']['favorites']=10-i
            r['metrics']['shares']=0
        result=prioritize(rows,POLICY)
        self.assertTrue(result['selected'])
        self.assertTrue(all(r['priority_tier']=='single_metric_backup' for r in result['selected']))
        cfg=deepcopy(POLICY);cfg['ranking']['fill_with_single_metric_backups']=False
        result=prioritize(rows,cfg)
        self.assertFalse(result['selected'])
        self.assertTrue(result['reserve'])

    def test_tiny_zero_or_undifferentiated_cohorts_are_not_hits(self):
        self.assertFalse(prioritize(self.records[:9],POLICY)['selected'])
        for row in self.records:
            row['metrics']={name:1 for name in row['metrics']}
        self.assertFalse(prioritize(self.records,POLICY)['selected'])

    def test_replay_and_publication_age_do_not_change_selection(self):
        before=prioritize(self.records,POLICY)
        after=deepcopy(self.records)
        for i,row in enumerate(after): row['published_at']=None if i%2 else '2020-01-01T00:00:00+08:00'
        actual=prioritize(list(reversed(after)),POLICY)
        self.assertEqual([r['record_id'] for r in before['selected']],[r['record_id'] for r in actual['selected']])
        self.assertTrue(all('age-adjust' not in reason for r in actual['selected'] for reason in r['selection_reasons']))


if __name__=='__main__': unittest.main()
