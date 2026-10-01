import copy
from datetime import date, timedelta
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from forecast import MODELS, audit, backtest, empirical_radius, metrics, predict, validate
from generate_demo import generate


class ForecastTests(unittest.TestCase):
    def test_seasonal_naive_repeats_last_week(self):
        history = list(range(56))
        self.assertEqual(predict(history, 'seasonal_naive'), list(range(49,56)))

    def test_weekday_average_hand_calculation(self):
        self.assertEqual(predict(list(range(56)), 'weekday_mean4'), [38.5+h for h in range(7)])

    def test_trend_recovers_exact_linear_weekly_signal(self):
        history = [100+3*(i//7)+i%7 for i in range(56)]
        self.assertEqual(predict(history, 'weekday_trend8'), [124+h for h in range(7)])

    def test_nonnegative_forecasts(self):
        history = [max(0, 20-3*(i//7)) for i in range(56)]
        self.assertTrue(all(value >= 0 for value in predict(history, 'weekday_trend8')))

    def test_metric_fixture_and_zero_denominator(self):
        result = metrics([{'actual':10, 'error':2}, {'actual':20, 'error':-4}])
        self.assertEqual(result['mae'], 3)
        self.assertEqual(result['bias'], -1)
        self.assertAlmostEqual(result['rmse'], math.sqrt(10))
        self.assertEqual(result['wape'], .2)
        self.assertIsNone(metrics([{'actual':0,'error':1}])['wape'])

    def test_empirical_quantile(self):
        self.assertEqual(empirical_radius([{'error': -i} for i in range(1,11)]), 9)

    def test_invalid_counts(self):
        for bad in [-1, True, 2.4, float('nan'), '12']:
            records = generate()
            records[10]['tickets'] = bad
            with self.assertRaises(ValueError):
                validate(records)

    def test_date_gaps_duplicates_and_order(self):
        records = generate()
        for altered in [records[:10]+records[11:], records[:10]+[records[9]]+records[11:], list(reversed(records))]:
            with self.assertRaises(ValueError):
                validate(altered)

    def test_insufficient_history(self):
        with self.assertRaises(ValueError):
            validate(generate()[:279])
        with self.assertRaises(ValueError):
            predict([1]*55, 'seasonal_naive')

    def test_week_targets_do_not_influence_own_forecasts(self):
        records = generate()
        dates, values = validate(records)
        changed = values[:]
        changed[308:315] = [9999]*7
        for model in MODELS:
            original = backtest(values, dates, 308,315,model)
            modified = backtest(changed, dates,308,315,model)
            self.assertEqual([row['prediction'] for row in original], [row['prediction'] for row in modified])

    def test_test_values_cannot_select_model_or_interval(self):
        records = generate()
        altered = copy.deepcopy(records)
        for row in altered[-56:]:
            row['tickets'] += 1000
        first, second = audit(records), audit(altered)
        self.assertEqual(first['selected_model'], second['selected_model'])
        self.assertEqual(first['calibration'], second['calibration'])
        self.assertEqual(first['validation'], second['validation'])

    def test_audit_date_boundaries_and_horizons(self):
        result = audit(generate())
        self.assertEqual([split['days'] for split in result['splits'].values()], [140,84,84,56])
        for rows in result['test_predictions'].values():
            self.assertEqual(len({row['date'] for row in rows}), 56)
            for row in rows:
                self.assertEqual((date.fromisoformat(row['date'])-date.fromisoformat(row['train_end'])).days, row['horizon'])
        self.assertEqual(len(result['next_week']),7)

    def test_constant_series(self):
        records = generate()
        for row in records:
            row['tickets'] = 0
        result = audit(records)
        self.assertEqual(result['selected_model'], 'seasonal_naive')
        self.assertEqual(result['test_interval_coverage'],1)
        self.assertEqual(result['calibration']['radius'],0)

    def test_cli_and_reproducibility(self):
        self.assertEqual(generate(), generate())
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, 'forecast.py', '--output', folder], capture_output=True, text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            output = json.loads((Path(folder)/'results.json').read_text())
            self.assertEqual(output,audit(generate()))
            self.assertTrue((Path(folder)/'forecast.csv').exists())
            self.assertTrue((Path(folder)/'report.md').exists())


if __name__ == '__main__':
    unittest.main()
