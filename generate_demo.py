"""Produce fictional daily support counts with weekly seasonality and a late level shift."""
from datetime import date, timedelta
import json
from pathlib import Path
import random


def generate():
    rng = random.Random(20261001)
    start = date(2025, 10, 1)
    weekday_effect = [28, 18, 12, 8, 0, -55, -65]
    records = []
    for i in range(364):
        day = start + timedelta(days=i)
        value = 130 + .22*i + weekday_effect[day.weekday()] + rng.gauss(0, 12)
        if i >= 308:
            value += 30  # Deliberate stress: unseen level shift at the test boundary.
        records.append({'date': day.isoformat(), 'tickets': max(0, round(value))})
    return records


if __name__ == '__main__':
    path = Path('data/daily_tickets.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(generate(), indent=2) + '\n', encoding='utf-8')
    print('Created 364 synthetic daily observations')
