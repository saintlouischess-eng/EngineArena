"""Non-destructive opponent-range views of already aggregated rating samples."""
import math


NOTE = ('Opponent range uses the absolute difference between all-opponent ratings in the same selected evidence scope. '
        'The baseline is fixed during each calculation; new results or evidence filters rebuild it. '
        'Only matchups with two finite baseline ratings qualify. Complete opening pairs stay intact. '
        'Eligible comparisons are jointly refitted with the same reference; disconnected entries are not rebased. '
        'Full rank refers to all configurations before version display or name search. '
        'Official games and W-D-L remain the full selected record; included games/opponents describe eligible rating samples. '
        'Filtered CI and LOS are conditional diagnostics and do not include uncertainty from selecting the range using those same results. '
        'This is not an independent confirmation or a guarantee of greater accuracy. No saved results are changed.')


def width(value):
    if value in (None, '', 'all'):return 0.
    try:result=float(value)
    except (TypeError,ValueError):raise ValueError('Opponent range must be a positive Elo number, or 0 for all opponents') from None
    if not math.isfinite(result) or result<0:
        raise ValueError('Opponent range must be a positive Elo number, or 0 for all opponents')
    return result


def restrict(values,limit,baseline):
    """O(observed matchups), not O(engines squared); never alter the full fit."""
    coverage={key:{'included_games':0,'included_pairs':0,'included_opponents':set()} for key in values['stats']}
    observations=[];pairs=unpaired=unknown=outside=0
    for a,b,bins in values['observations']:
        ak,bk=values['ordered'][a],values['ordered'][b]
        ar,br=baseline[ak]['rating'],baseline[bk]['rating'];n=sum(bins);paired=len(bins)==5
        games=n*(2 if paired else 1)
        if ar is None or br is None or not math.isfinite(ar) or not math.isfinite(br):unknown+=games;continue
        if abs(ar-br)>limit+1e-8:outside+=games;continue
        observations.append((a,b,bins))
        if paired:pairs+=n
        else:unpaired+=n
        for key,opponent in ((ak,bk),(bk,ak)):
            c=coverage[key];c['included_games']+=games;c['included_pairs']+=n if paired else 0
            c['included_opponents'].add(opponent)
    for c in coverage.values():c['included_opponents']=len(c['included_opponents'])
    return {k:v for k,v in values.items() if k not in ('fit','estimates')} | {
        'observations':observations,'pairs':pairs,'unpaired':unpaired,'baseline':baseline,'coverage':coverage,
        'opponent_range':{'elo':limit,'baseline_counted_games':2*values['pairs']+values['unpaired'],
                          'included_games':2*pairs+unpaired,'outside_range_games':outside,
                          'unrated_baseline_games':unknown,'excluded_games':outside+unknown}}
