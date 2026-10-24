"""Spreadsheet-friendly statistics: one value per column, explicit interval method."""
import csv
import io
from .display import los_percent


def standings_csv(rows, method='normal'):
    fields = ['rank','name','games','wins','draws','losses','tf','tf_official','points','score_pct','draw_pct',
              'elo','confidence','ci_method','ci_lower','ci_upper','los','los_display','pairs',
              'bye_points','seed','black_wins','buchholz','sonneborn_berger','tiebreak_order','ranking_basis','model']
    if any('ko_status' in row for row in rows):fields[2:2]=['ko_finish','ko_status','match_wins','match_losses','eliminated_round','byes']
    if any('withdrawn' in row for row in rows):fields.insert(2,'withdrawn')
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        interval = row.get('ci_conservative' if method == 'conservative' else 'ci')
        writer.writerow(row | {'los_display':los_percent(row.get('los')),'ci_method': 'Conservative Hoeffding' if method == 'conservative' else 'Normal approximation',
                               'ci_lower': interval[0] if interval else None,
                               'ci_upper': interval[1] if interval else None})
    return output.getvalue()
