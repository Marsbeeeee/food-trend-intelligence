"""Account-first stage boundaries, identity, missing metrics and frozen outputs."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pipeline.benchmarks import (initialize, read, validate_accounts, validate_reviews,
                                 validate_videos, compare, render_accounts)
from pipeline.paths import ROOT


def account(platform='instagram', handle='demo', creator='person1', **extra):
    prefix = '@' if platform in ('tiktok', 'youtube') else ''
    host = {'instagram': 'instagram.com', 'tiktok': 'tiktok.com', 'youtube': 'youtube.com'}[platform]
    return dict(creator_id=creator, platform=platform, display_name='Synthetic baker', handle=handle,
                profile_url=f'https://www.{host}/{prefix}{handle}/',
                source_url=f'https://www.{host}/', discovery_query='muscular baker',
                captured_at='2026-11-24T08:00:00+00:00', followers=None,
                followers_display=None, followers_missing_reason='Not visible',
                persona_evidence='Synthetic profile observation', bread_evidence='Synthetic recurring bread posts',
                fit='direct', verification='profile_observed', **extra)


def review(account_id='instagram:demo', decision='selected'):
    return dict(account_id=account_id, decision=decision, reason='Manual selection',
                reviewed_at='2026-11-24T09:00:00+00:00')


def video(i=1, account_id='instagram:demo', url=None, **extra):
    row = dict(account_id=account_id, url=url or f'https://www.instagram.com/reel/DEMO{i}/',
               title=f'Synthetic bread {i}', author_evidence='Original creator profile checked',
               captured_at='2026-11-24T10:00:00+00:00', published_at=None, format='short',
               views=100, baseline_sample=True, sample_reason='Consecutive sample',
               content_group='unassigned', content_evidence=None)
    row.update(extra)
    return row


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.collection = read(ROOT / 'config/collection.json')
        self.policy = read(ROOT / 'config/screening.json')['comparison']
        self.accounts = validate_accounts([account()], self.collection)
        self.reviews = validate_reviews([review()], self.accounts)

    def videos(self, source):
        return validate_videos(source, self.accounts, self.reviews)

    def test_missing_and_small_followers_never_exclude(self):
        self.assertEqual(self.accounts[0]['followers_observation']['kind'], 'missing')
        small = account()
        small.update(followers=2)
        self.assertEqual(len(validate_accounts([small], self.collection)), 1)
        large = account()
        large.update(followers=100000)
        self.assertEqual(len(validate_accounts([large], self.collection)), 1)

    def test_missing_reason_and_timezone_required(self):
        for update in ({'followers_missing_reason': ''}, {'captured_at': '2026-11-24T08:00:00'}):
            row = account()
            row.update(update)
            with self.assertRaises(ValueError):
                validate_accounts([row], self.collection)

    def test_account_identity_and_url_validation(self):
        a, b = account(), account()
        b['handle'] = '@DEMO'
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            validate_accounts([a, b], self.collection)
        for url in ('https://instagram.com.evil.test/demo/', 'https://instagram.com/reel/demo/', 'https://instagram.com/another/'):
            a = account()
            a['profile_url'] = url
            with self.assertRaises(ValueError):
                validate_accounts([a], self.collection)

    def test_cross_platform_merge_requires_evidence(self):
        source = [account(), account('youtube')]
        with self.assertRaisesRegex(ValueError, 'identity_evidence'):
            validate_accounts(source, self.collection)
        for row in source:
            row['identity_evidence'] = 'Synthetic profile cross-links'
        self.assertEqual(len(validate_accounts(source, self.collection)), 2)

    def test_unverified_cannot_be_selected_but_can_be_listed(self):
        source = [account()]
        source[0]['verification'] = 'search_only'
        accounts = validate_accounts(source, self.collection)
        with self.assertRaisesRegex(ValueError, 'Verify profile'):
            validate_reviews([review()], accounts)
        self.assertEqual(validate_reviews([review(decision='pending')], accounts)['instagram:demo']['decision'], 'pending')

    def test_video_stage_requires_selection(self):
        with self.assertRaisesRegex(ValueError, 'selected account'):
            validate_videos([video()], self.accounts, {})
        self.assertEqual(len(self.videos([video()])), 1)
        with self.assertRaisesRegex(ValueError, 'Duplicate video'):
            self.videos([video(), video()])
        with self.assertRaisesRegex(ValueError, 'original video'):
            self.videos([video(url='https://www.instagram.com/demo/')])

    def test_precision_and_baseline_with_historical_outlier(self):
        source = [video(i, views=i * 100) for i in range(1, 11)]
        source.append(video(11, views=100000, baseline_sample=False,
                            sample_reason='Historical popular video, separate from baseline',
                            content_group='high', group_reason='Historical high performer'))
        result = compare(self.videos(source), self.policy)[0]
        self.assertEqual(result['baseline_median'], 550)
        self.assertAlmostEqual(result['videos'][-1]['relative_views'], 100000 / 550)
        self.assertTrue(all(v['content_evidence'] is None for v in result['videos']))

    def test_approximate_and_lower_bound(self):
        source = [video(i, views=None, views_display='1.2K') for i in range(10)]
        source.append(video(11, views=None, views_display='10K+'))
        result = compare(self.videos(source), self.policy)[0]
        self.assertEqual(result['baseline_count'], 10)
        self.assertEqual(result['baseline_median'], 1200)
        self.assertIsNone(result['videos'][-1]['relative_views'])
        self.assertEqual(result['videos'][-1]['views_observation']['display'], '10K+')

    def test_missing_insufficient_and_zero_baseline(self):
        for source in ([video()], [video(i, views=0) for i in range(10)]):
            group = compare(self.videos(source), self.policy)[0]
            self.assertEqual(group['status'], 'insufficient_or_zero_baseline')
            self.assertIsNone(group['videos'][0]['relative_views'])
        with self.assertRaisesRegex(ValueError, 'views_missing_reason'):
            self.videos([video(views=None)])
        self.assertEqual(self.videos([video(views=None, views_missing_reason='Hidden')])[0]['views_observation']['kind'], 'missing')

    def test_same_creator_accounts_and_formats_are_separate(self):
        source = [account('youtube', 'one'), account('youtube', 'two'), account('instagram', 'three')]
        for row in source:
            row['identity_evidence'] = 'Verified links'
        accounts = validate_accounts(source, self.collection)
        reviews = validate_reviews([review(a['account_id']) for a in accounts], accounts)
        videos = [
            video(account_id='youtube:one', url='https://youtube.com/shorts/ONE'),
            video(account_id='youtube:one', url='https://youtube.com/watch?v=TWO', format='long'),
            video(account_id='youtube:two', url='https://youtube.com/shorts/THREE'),
            video(account_id='instagram:three')]
        self.assertEqual(len(compare(validate_videos(videos, accounts, reviews), self.policy)), 4)

    def test_content_evidence_not_inferred(self):
        row = video(content_evidence={'method': 'title', 'bread': 'sourdough'})
        with self.assertRaisesRegex(ValueError, 'Invalid content evidence'):
            self.videos([row])
        with self.assertRaisesRegex(ValueError, 'group_reason'):
            self.videos([video(content_group='high')])

    def test_resume_preserves_inputs_and_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = initialize(temp, '2026-11-24')
            (folder / 'accounts.jsonl').write_text('keep me', encoding='utf-8')
            snapshot = (folder / 'config_snapshot.json').read_bytes()
            self.assertEqual(initialize(temp, '2026-11-24'), folder)
            self.assertEqual((folder / 'accounts.jsonl').read_text(encoding='utf-8'), 'keep me')
            self.assertEqual((folder / 'config_snapshot.json').read_bytes(), snapshot)

    def test_cli_frozen_report_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = initialize(temp, '2026-11-24')
            (folder / 'accounts.jsonl').write_text(json.dumps(account()) + '\n', encoding='utf-8')
            output = Path(temp) / 'edition'
            command = [sys.executable, str(ROOT / 'run.py'), 'accounts', 'report',
                       '--folder', str(folder), '--output', str(output)]
            first = subprocess.run(command, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(read(output / 'manifest.json')['summary']['selected'], 0)
            self.assertEqual((output / 'accounts.jsonl').read_bytes(), (folder / 'accounts.jsonl').read_bytes())
            before = (output / 'report.md').read_bytes()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual((output / 'report.md').read_bytes(), before)
            (folder / 'reviews.jsonl').write_text(json.dumps(review()) + '\n', encoding='utf-8')
            (folder / 'videos.jsonl').write_text(json.dumps(video()) + '\n', encoding='utf-8')
            result = subprocess.run([sys.executable, str(ROOT / 'run.py'), 'videos', 'compare',
                                     '--folder', str(folder), '--output', str(Path(temp) / 'comparison')], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('待补', (Path(temp) / 'comparison/report.md').read_text(encoding='utf-8'))

    def test_retired_commands_fail_with_guidance(self):
        result = subprocess.run([sys.executable, str(ROOT / 'run.py'), 'collect'], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'retired', result.stderr)

    def test_markdown_table_cells_do_not_inject_rows(self):
        data = deepcopy(self.accounts)
        data[0]['display_name'] = 'name | injected\nline'
        report = render_accounts(data, {}, '{{account_table}}')
        self.assertIn(r'name \| injected line', report)
        self.assertEqual(len(report.splitlines()), 3)
