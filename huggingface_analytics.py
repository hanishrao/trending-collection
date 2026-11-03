"""Analytics over observed daily rankings, never inferred download activity."""
import datetime as dt
import json
from pathlib import Path


def snapshot_date(feed):
    return dt.datetime.fromisoformat(feed['updated_at']).astimezone(dt.timezone.utc).date()


def summarize(snapshots):
    by_date = {snapshot_date(feed): feed for feed in snapshots}
    dates = sorted(by_date)
    current_date = dates[-1]
    current = by_date[current_date]
    previous_date = dates[-2] if len(dates) > 1 else None
    previous = {row['id']: row for row in by_date[previous_date]['items']} if previous_date else {}
    first_seen = {}
    for date in dates:
        for row in by_date[date]['items']:
            first_seen.setdefault(row['id'], date.isoformat())
    recent = [date for date in dates if (current_date - date).days < 7]
    counts = {}
    for date in recent:
        for repo_id in {row['id'] for row in by_date[date]['items']}:
            counts[repo_id] = counts.get(repo_id, 0) + 1
    items = []
    for row in current['items']:
        prior = previous.get(row['id'])
        status = 'baseline' if previous_date is None else (
            'continuing' if prior else ('new' if first_seen[row['id']] == current_date.isoformat() else 'reentry'))
        likes_change = None
        if prior and row.get('likes') is not None and prior.get('likes') is not None:
            likes_change = row['likes'] - prior['likes']
        items.append({'id': row['id'], 'url': row['url'], 'rank': row['rank'], 'status': status,
                      'first_seen': first_seen[row['id']], 'appearances_7d': counts[row['id']],
                      'rank_change': prior['rank'] - row['rank'] if prior else None,
                      'likes_change': likes_change})
    return {'updated_at': current['updated_at'], 'snapshot_date': current_date.isoformat(),
            'tracking_started': dates[0].isoformat(),
            'comparison_date': previous_date.isoformat() if previous_date else None,
            'comparison_interval_days': (current_date - previous_date).days if previous_date else None,
            'window_start': (current_date - dt.timedelta(days=6)).isoformat(),
            'observed_days_7d': len(recent), 'window_days': 7, 'sample_limit': 20,
            'scope': 'Observed Hugging Face top-20 rankings; positive rank_change means rising.',
            'daily_leaders': [{'date': date.isoformat(), 'id': by_date[date]['items'][0]['id'],
                               'url': by_date[date]['items'][0]['url']} for date in reversed(recent)],
            'items': items}


def snapshot_outputs(root, feeds):
    """Prepare dated snapshots and analytics; reruns replace the same UTC date."""
    root = Path(root)
    outputs, analytics = {}, {}
    for kind, feed in feeds.items():
        date = snapshot_date(feed)
        history = root / 'api/huggingface/history'
        prior = []
        for path in sorted(history.glob(f'*/{kind}.json')):
            # Exclude today's superseded snapshot and any future snapshots on historical reruns.
            if path.parent.name < date.isoformat():
                prior.append(json.loads(path.read_text(encoding='utf-8')))
        analytics[kind] = summarize(prior + [feed])
        outputs[history / date.isoformat() / f'{kind}.json'] = json.dumps(feed, indent=2, ensure_ascii=False) + '\n'
        outputs[root / 'api/huggingface/analytics' / f'{kind}.json'] = json.dumps(analytics[kind], indent=2, ensure_ascii=False) + '\n'
    return outputs, analytics
