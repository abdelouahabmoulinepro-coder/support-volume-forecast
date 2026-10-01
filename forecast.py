"""Audit daily support-volume forecasts with strictly chronological evaluation."""
import argparse
import csv
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

MODELS = ('seasonal_naive', 'weekday_mean4', 'weekday_trend8')
HORIZON = 7


def validate(records):
    if not isinstance(records, list) or not 280 <= len(records) <= 10000:
        raise ValueError('Provide 280 to 10000 daily observations')
    dates, values = [], []
    for row in records:
        if not isinstance(row, dict) or not isinstance(row.get('date'), str):
            raise ValueError('Each observation needs an ISO date')
        day = date.fromisoformat(row['date'])
        if day.isoformat() != row['date']:
            raise ValueError('Dates must use YYYY-MM-DD')
        value = row.get('tickets')
        if type(value) is not int or not 0 <= value <= 10**7:
            raise ValueError('tickets must be a nonnegative integer <= 10000000')
        if dates and day != dates[-1] + timedelta(days=1):
            raise ValueError('Dates must be sorted, unique and contiguous; missing days are not zero')
        dates.append(day)
        values.append(value)
    return dates, values


def predict(history, model):
    if model not in MODELS or len(history) < 56:
        raise ValueError('Known model and at least 56 historical days required')
    if any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in history):
        raise ValueError('History must be finite and nonnegative')
    if model == 'seasonal_naive':
        return list(history[-7:])
    output = []
    for h in range(7):
        if model == 'weekday_mean4':
            value = mean(history[-28:][h::7])
        else:
            weekly = history[-56:][h::7]
            # Separate OLS line for each day-of-week slot: x = 0,...,7, forecast at 8.
            level = mean(weekly)
            slope = sum((i - 3.5) * (y - level) for i, y in enumerate(weekly)) / 42
            value = level + slope * (8 - 3.5)
        output.append(max(0.0, value))
    return output


def backtest(values, dates, start, end, model):
    if start < 56 or end > len(values) or start >= end or (end-start) % 7:
        raise ValueError('Backtest requires complete weeks after 56 historical days')
    rows = []
    for origin in range(start, end, 7):
        predictions = predict(values[:origin], model)
        for h, prediction in enumerate(predictions):
            rows.append({'train_end': dates[origin-1].isoformat(), 'date': dates[origin+h].isoformat(),
                         'horizon': h+1, 'actual': values[origin+h], 'prediction': prediction,
                         'error': prediction - values[origin+h]})
    return rows


def metrics(rows):
    if not rows:
        raise ValueError('Cannot score an empty evaluation')
    errors = [row['error'] for row in rows]
    denominator = sum(row['actual'] for row in rows)
    return {'n': len(rows), 'mae': mean(abs(error) for error in errors),
            'rmse': math.sqrt(mean(error**2 for error in errors)), 'bias': mean(errors),
            'wape': sum(abs(error) for error in errors) / denominator if denominator else None}


def empirical_radius(rows, quantile=.9):
    if not rows or not 0 < quantile <= 1:
        raise ValueError('Nonempty calibration errors and quantile in (0,1] required')
    return sorted(abs(row['error']) for row in rows)[math.ceil(quantile * len(rows)) - 1]


def audit(records):
    dates, values = validate(records)
    n = len(values)
    test_start, calibration_start, validation_start = n-56, n-140, n-224
    validation = {model: metrics(backtest(values, dates, validation_start, calibration_start, model)) for model in MODELS}
    # Stable ties follow the declared model order. Test and calibration are not used for selection.
    selected = min(MODELS, key=lambda model: validation[model]['mae'])
    calibration = backtest(values, dates, calibration_start, test_start, selected)
    radius = empirical_radius(calibration)
    test_rows = {model: backtest(values, dates, test_start, n, model) for model in MODELS}
    for row in test_rows[selected]:
        row['lower'] = max(0, row['prediction'] - radius)
        row['upper'] = row['prediction'] + radius
        row['covered'] = row['lower'] <= row['actual'] <= row['upper']
    future = [{'date': (dates[-1] + timedelta(days=h+1)).isoformat(), 'prediction': prediction,
               'lower': max(0, prediction-radius), 'upper': prediction+radius}
              for h, prediction in enumerate(predict(values, selected))]
    splits = {name: {'start': dates[start].isoformat(), 'end': dates[end-1].isoformat(), 'days': end-start}
              for name, start, end in [('initial_history', 0, validation_start), ('validation', validation_start, calibration_start),
                                       ('calibration', calibration_start, test_start), ('test', test_start, n)]}
    return {'data_sha256': hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest(),
            'selected_model': selected, 'splits': splits, 'validation': validation,
            'calibration': {'absolute_error_quantile': .9, 'n': len(calibration), 'radius': radius},
            'test': {model: metrics(rows) for model, rows in test_rows.items()},
            'test_interval_coverage': mean(row['covered'] for row in test_rows[selected]),
            'test_by_horizon': {str(h): metrics([row for row in test_rows[selected] if row['horizon'] == h]) for h in range(1,8)},
            'test_predictions': test_rows, 'next_week': future}


def report_markdown(result):
    lines = ['# Support Volume Forecast', '', '> Démonstration synthétique. Aucune performance de production ni garantie de couverture.', '',
             f"Modèle retenu sur validation : **{result['selected_model']}**.", '',
             '| Période | Début | Fin | Jours |', '|---|---|---|---:|']
    for name, split in result['splits'].items():
        lines.append(f"| {name} | {split['start']} | {split['end']} | {split['days']} |")
    lines += ['', '## Comparaison sur le test', '', '| Modèle | MAE | RMSE | Biais prévision − réel | WAPE |', '|---|---:|---:|---:|---:|']
    for model, metric in result['test'].items():
        wape = 'N/A' if metric['wape'] is None else f"{metric['wape']:.1%}"
        lines.append(f"| {model} | {metric['mae']:.2f} | {metric['rmse']:.2f} | {metric['bias']:.2f} | {wape} |")
    lines += ['', f"Bande indicative : prévision ± {result['calibration']['radius']:.2f} tickets, plancher zéro.",
              f"Couverture observée sur les 56 jours de test : **{result['test_interval_coverage']:.1%}**.", '',
              'Le rayon est le quantile empirique 90 % des erreurs absolues de calibration, mutualisées entre horizons. '
              'La dépendance temporelle et les changements de régime empêchent de garantir une couverture future de 90 %.', '',
              '## Sept jours suivants — scénario synthétique', '', '| Date | Prévision | Borne basse | Borne haute |', '|---|---:|---:|---:|']
    for row in result['next_week']:
        lines.append(f"| {row['date']} | {row['prediction']:.1f} | {row['lower']:.1f} | {row['upper']:.1f} |")
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', default='data/daily_tickets.json')
    parser.add_argument('--output', default='build')
    args = parser.parse_args()
    try:
        source, output = Path(args.input).resolve(), Path(args.output).resolve()
        if source in [output/name for name in ['results.json', 'report.md', 'forecast.csv']]:
            raise ValueError('Output would overwrite input')
        result = audit(json.loads(source.read_text(encoding='utf-8-sig')))
        output.mkdir(parents=True, exist_ok=True)
        (output/'results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        (output/'report.md').write_text(report_markdown(result), encoding='utf-8')
        with (output/'forecast.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=['date','prediction','lower','upper'], lineterminator='\n')
            writer.writeheader()
            writer.writerows(result['next_week'])
        print(json.dumps({key: result[key] for key in ['selected_model','test','test_interval_coverage']}, indent=2))
    except (ValueError, OSError, TypeError) as error:
        parser.exit(1, f'Data/evaluation error: {error}\n')


if __name__ == '__main__':
    main()
