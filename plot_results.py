"""Optional static figure: pip install -r requirements-plot.txt."""
import argparse
from datetime import date
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', nargs='?', default='example/results.json')
    parser.add_argument('--output', default='example/forecast-audit.png')
    args = parser.parse_args()
    report = json.loads(Path(args.results).read_text(encoding='utf-8'))
    selected = report['selected_model']
    rows = report['test_predictions'][selected]
    days = [date.fromisoformat(row['date']) for row in rows]
    fig = plt.figure(figsize=(12, 8.5), facecolor='#f8fafc', layout='constrained')
    grid = fig.add_gridspec(2, 2, height_ratios=[2, 1])
    ax = fig.add_subplot(grid[0, :])
    ax.fill_between(days, [row['lower'] for row in rows], [row['upper'] for row in rows], color='#bfdbfe', alpha=.65, label='Bande indicative (calibration)')
    ax.plot(days, [row['actual'] for row in rows], color='#0f172a', linewidth=1.8, label='Tickets observés (fictifs)')
    ax.plot(days, [row['prediction'] for row in rows], color='#2563eb', linewidth=1.8, label='Modèle choisi sur validation')
    ax.set_title('Prévisions à 7 jours, recalculées chaque semaine', loc='left', fontsize=14, pad=15)
    ax.set_ylabel('Tickets par jour')
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    ax.grid(axis='y', alpha=.2)
    ax.legend(loc='lower right', fontsize=9)
    bars = fig.add_subplot(grid[1,0])
    labels = list(report['test'])
    values = [report['test'][model]['mae'] for model in labels]
    bars.barh(labels, values, color=['#64748b', '#2563eb', '#0d9488'])
    bars.invert_yaxis()
    bars.set_xlim(0, max(values)*1.3)
    for i, value in enumerate(values):
        bars.text(value+.2, i, f'{value:.2f}', va='center')
    bars.set_title('Erreur absolue moyenne sur le test', loc='left', pad=15)
    bars.set_xlabel('Tickets — plus faible = meilleur')
    note = fig.add_subplot(grid[1,1])
    note.axis('off')
    note.text(.08, .88, f"{report['test_interval_coverage']:.1%}", va='top', fontsize=36, weight='bold', color='#9a3412')
    note.text(.08, .49, 'des observations dans la bande indicative\nQuantile de calibration : 90 %\nCouverture future non garantie', va='top', fontsize=11, linespacing=1.6)
    fig.suptitle('SUPPORT VOLUME  /  FORECAST AUDIT\nUn changement de régime met le modèle à l’épreuve', fontsize=18, weight='bold')
    fig.supxlabel('Données synthétiques · 56 jours de test · Modèle et rayon choisis avant le test', fontsize=10, color='#475569')
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=160)
    plt.close(fig)
    print(target)


if __name__ == '__main__':
    main()
