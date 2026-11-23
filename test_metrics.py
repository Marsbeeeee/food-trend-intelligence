"""Precision preservation and display parsing, without platform access."""
import unittest
from pipeline.metrics import observe_metric, observe_metrics


class MetricTests(unittest.TestCase):
    def test_exact_zero_and_grouped_display(self):
        self.assertEqual(observe_metric(0, '0')['comparison_value'], 0)
        self.assertEqual(observe_metric(1234, '1,234')['exact_value'], 1234)

    def test_approximation_is_not_exact(self):
        for text, value in [('1.2万', 12000), ('2亿', 200000000), ('1.5k', 1500), ('2M', 2000000), ('3w', 30000)]:
            obs = observe_metric(None, text)
            self.assertEqual(obs['kind'], 'approximate')
            self.assertEqual(obs['comparison_value'], value)
            self.assertIsNone(obs['exact_value'])

    def test_lower_bound_has_no_point_comparison_value(self):
        obs = observe_metric(None, '10万+')
        self.assertEqual(obs['lower_bound'], 100000)
        self.assertIsNone(obs['comparison_value'])
        self.assertIsNone(obs['exact_value'])

    def test_missing_labels_negative_and_invalid_are_not_zero(self):
        for text in (None, '', '评论', '收藏', '-1', 'NaN', 'Infinity', '1,23', '1.2'):
            obs = observe_metric(None, text)
            self.assertEqual(obs['kind'], 'missing')
            self.assertIsNone(obs['comparison_value'])

    def test_conflicts_and_invalid_exact_values_rejected(self):
        for value, display in [(12000, '1.2万'), (1, '2'), (0, '评论'), (True, None), (-1, None)]:
            with self.assertRaises(ValueError): observe_metric(value, display)

    def test_input_not_rewritten(self):
        exact, display = {'likes': None}, {'likes': '1.2万'}
        observe_metrics(exact, display)
        self.assertEqual(exact, {'likes': None})
        self.assertEqual(display, {'likes': '1.2万'})


if __name__ == '__main__': unittest.main()
