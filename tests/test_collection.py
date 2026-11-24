from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pipeline.policy import load_policy
"""Offline behavior checks for date archives, checkpoints and pipeline import."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pipeline.collection import Collection, archive_folder, discover_inputs, PLATFORMS

ROOT = Path(__file__).resolve().parents[1]
POLICY = load_policy()


def record(short='dy', content_id='123456789012345678901234', likes=100):
    platform, _, domain = PLATFORMS[short]
    if short == 'bili':
        content_id = 'BV1test000001'
    path = 'explore' if short == 'xhs' else 'video'
    return {'schema': 'browser_video_v1', 'content_id': content_id,
            'url': f'https://www.{domain}/{path}/{content_id}?required=keep',
            'source_url': f'https://www.{domain}/search?keyword=food', 'keyword': '美食',
            'title': '美食制作测试', 'author': '测试作者', 'content_type': 'video',
            'captured_at': '2026-11-22T20:00:00+08:00', 'detail_status': 'complete',
            'metrics': {name: likes if name == 'likes' else 0 for name in ('views', 'likes', 'coins', 'favorites', 'comments', 'shares')},
            'metrics_display': {}, 'search_conditions': {'type': 'video', 'sort': '综合'}}


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.job = Collection(self.root, '2026-11-22', deepcopy(POLICY))
        self.job.init()

    def tearDown(self):
        self.temp.cleanup()

    def attempt(self, short='dy', key='first'):
        return self.job.attempt(short, key, '美食')

    def test_same_day_replay_and_restart_preserve_first_snapshot(self):
        self.attempt()
        source = record()
        self.job.append('dy', [source])
        original = self.job.path('dy').read_bytes()
        resumed = Collection(self.root, '2026-11-22', deepcopy(POLICY))
        resumed.init()
        self.assertEqual(resumed.append('dy', [record(likes=999)])['duplicates'], 1)
        self.assertEqual(original, resumed.path('dy').read_bytes())
        self.assertFalse(resumed.attempt('dy', 'first', '美食')['open_detail'])
        self.assertEqual(resumed.status(True)['platforms']['dy']['attempts'], 1)

    def test_different_dates_and_platforms_preserve_identity(self):
        self.attempt(); self.job.append('dy', [record()])
        self.attempt('xhs'); self.job.append('xhs', [record('xhs')])
        later = Collection(self.root, '2026-12-05', deepcopy(POLICY)); later.init()
        later.attempt('dy', 'first', '美食'); later.append('dy', [record(likes=200)])
        self.assertEqual(later.path('dy'), self.root/'2026/1205/douyin_original.jsonl')
        self.assertEqual(json.loads(self.job.path('dy').read_text(encoding='utf-8'))['metrics']['likes'], 100)
        self.assertEqual(json.loads(later.path('dy').read_text(encoding='utf-8'))['metrics']['likes'], 200)
        self.assertEqual(self.job.status()['platforms']['xhs']['complete_records'], 1)

    def test_invalid_core_field_is_discarded_without_payload(self):
        self.attempt()
        broken = record(); broken['metrics']['comments'] = None
        result = self.job.append('dy', [broken])
        self.assertEqual(result['discarded'], 1)
        self.assertEqual(self.job.path('dy').read_bytes(), b'')
        self.assertIn('invalid_metric_comments', self.job.status()['platforms']['dy']['failure_reasons'])

    def test_approximation_not_pseudo_integer_and_modal_id_preserved(self):
        self.attempt()
        source = record(); source['metrics']['likes'] = None; source['metrics_display']['likes'] = '1.2万'
        source['url'] = 'https://www.douyin.com/video/111/search/food?modal_id='+source['content_id']+'&required=keep'
        self.assertEqual(self.job.append('dy', [source])['added'], 1)
        saved = json.loads(self.job.path('dy').read_text(encoding='utf-8'))
        self.assertEqual(saved['url'], source['url']); self.assertIsNone(saved['metrics']['likes'])
        self.attempt(key='bad-rounded')
        fake = record(content_id='222'); fake['metrics_display']['likes'] = '1.2万'
        self.assertEqual(self.job.append('dy', [fake])['discarded'], 1)

    def test_attempt_limit_and_target_stop_before_browsing(self):
        policy = deepcopy(POLICY); policy['collection']['max_detail_attempts_per_platform'] = 2
        limited = Collection(self.root, '2026-12-06', policy); limited.init(target=1)
        limited.attempt('dy', 'a', '美食'); limited.reject('dy', 'detail_timeout')
        limited.attempt('dy', 'b', '美食'); limited.reject('dy', 'missing_comments')
        with self.assertRaisesRegex(ValueError, 'limit'):
            limited.attempt('dy', 'c', '美食')
        self.job.init(target=1); self.attempt(); self.job.append('dy', [record()])
        with self.assertRaisesRegex(ValueError, 'target'):
            self.job.attempt('dy', 'another', '美食')
        self.job.init(target=3)
        self.assertTrue(self.job.attempt('dy', 'another', '美食')['open_detail'])

    def test_unregistered_attempt_wrong_platform_and_same_platform_lock(self):
        with self.assertRaisesRegex(ValueError, 'Register'):
            self.job.append('dy', [record()])
        self.attempt()
        self.assertEqual(self.job.append('dy', [record('xhs')])['discarded'], 1)
        with self.job.locked('dy'):
            with self.assertRaisesRegex(ValueError, 'already being written'):
                self.job.attempt('dy', 'busy', '美食')
            self.assertTrue(self.job.attempt('xhs', 'independent', '美食')['open_detail'])

    def test_partial_old_archive_cannot_reset_attempt_budget(self):
        old = Collection(self.root, '2026-12-07', deepcopy(POLICY))
        old.folder.mkdir(parents=True)
        old.path('dy').write_text(json.dumps(record())+'\n', encoding='utf-8')
        old.init()
        self.assertIsNone(old.status()['platforms']['dy']['attempts'])
        with self.assertRaisesRegex(ValueError, 'no attempt history'):
            old.attempt('dy', 'more', '美食')

    def test_new_layout_pipeline_import_and_legacy_ambiguity(self):
        for short in PLATFORMS:
            self.attempt(short); self.job.append(short, [record(short)])
        config = json.loads((ROOT/'config/legacy/report.json').read_text(encoding='utf-8'))
        config.update(observation_cutoff='2026-11-22T20:00:00+08:00')
        cfg = self.root/'config.json'; cfg.write_text(json.dumps(config), encoding='utf-8')
        command = [sys.executable, '-c', 'from pipeline.workflow import main; main()', 'discovery', '--run-id', 'archive-import',
                   '--run-root', str(self.root/'runs'), '--config', str(cfg), '--input-root', str(self.job.folder)]
        subprocess.run(command, check=True, capture_output=True)
        summary = json.loads((self.root/'runs/archive-import/discovery.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['accepted_by_platform'], {'douyin': 1, 'xiaohongshu': 1, 'bilibili': 1})
        legacy = self.job.folder/'dy'; legacy.mkdir(); (legacy/'records.jsonl').write_text('', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            discover_inputs(self.job.folder, ['dy'])

    def test_date_validation_and_non_destructive_malformed_file(self):
        for bad in ('../2026', '2026-02-30', '20261205', '2026-12-05/extra'):
            with self.assertRaises(ValueError): archive_folder(self.root, bad)
        self.job.path('dy').write_text('broken\n', encoding='utf-8')
        before = self.job.path('dy').read_bytes()
        with self.assertRaises(ValueError): self.job.status()
        self.assertEqual(self.job.path('dy').read_bytes(), before)

    def test_cli_status_and_batch_limit(self):
        result = subprocess.run([sys.executable, '-c', 'from pipeline.collection import main; main()', 'status', '--date', self.job.date,
                                 '--data-root', str(self.root)], check=True, capture_output=True)
        self.assertEqual(json.loads(result.stdout)['archive_date'], '2026-11-22')
        with self.assertRaisesRegex(ValueError, 'batch_size'):
            self.job.append('dy', [record()]*6)

    def test_malformed_metrics_display_rejected_and_archive_not_corrupted(self):
        self.attempt()
        malformed = record(); malformed['metrics_display'] = None
        result = self.job.append('dy', [malformed])
        self.assertEqual(result['discard_reasons'], {'invalid_metrics_display': 1})
        self.assertEqual(self.job.path('dy').read_bytes(), b'')

    def test_ranking_updates_do_not_reset_or_block_collection_resume(self):
        self.attempt()
        changed = deepcopy(POLICY)
        changed['version'] = 'test-new-ranking'
        changed['ranking']['max_candidates_per_platform'] = 3
        resumed = Collection(self.root, self.job.date, changed)
        resumed.init()
        self.assertEqual(resumed.status()['platforms']['dy']['attempts'], 1)
        self.assertEqual(resumed.load_state('dy')['policy'], POLICY)
        changed['collection']['keywords'] = ['different']
        with self.assertRaisesRegex(ValueError, 'frozen collection policy'):
            Collection(self.root, self.job.date, changed).init()


if __name__ == '__main__':
    unittest.main()

