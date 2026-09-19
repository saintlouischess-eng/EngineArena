"""Spreadsheet-friendly statistics: one value per column, explicit interval method."""
import csv
import io


def standings_csv(rows, method='normal'):
    fields = ['rank','name','games','wins','draws','losses','points','score_pct','draw_pct',
              'elo','confidence','ci_method','ci_lower','ci_upper','los','pairs',
              'bye_points','seed','black_wins','buchholz','sonneborn_berger','model']
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        interval = row.get('ci_conservative' if method == 'conservative' else 'ci')
        writer.writerow(row | {'ci_method': 'Conservative Hoeffding' if method == 'conservative' else 'Normal approximation',
                               'ci_lower': interval[0] if interval else None,
                               'ci_upper': interval[1] if interval else None})
    return output.getvalue()
