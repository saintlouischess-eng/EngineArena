import json
import statistics
from pathlib import Path
r=json.loads(Path('test-output/sustained-report.json').read_text());rows=r['samples'];unique={s['ui']['time']:s['ui']|{'active':s['active']} for s in rows if s.get('ui') and s['ui']['visible'] and s['active']>=28}
groups={}
for count in (2,32):
    selected=[s for s in unique.values() if s['visible_boards']==count]
    if selected:groups[count]={'distinct_browser_reports':len(selected),'median_frame_p95_ms':statistics.median(s['frame_p95_ms'] for s in selected),'worst_window_frame_p95_ms':max(s['frame_p95_ms'] for s in selected),'largest_frame_gap_ms':max(s['frame_max_ms'] for s in selected),'event_p95_ms_latest':selected[-1]['event_p95_ms'],'event_samples_latest':selected[-1]['event_samples'],'long_tasks_latest':selected[-1]['long_tasks']}
print(json.dumps({'browser_groups':groups,'cpu_median_busy':statistics.median(s['cpu_percent'] for s in rows if s['active']>=28),'memory_peak_gb':max(s['memory_used_gb'] for s in rows)},indent=2))
