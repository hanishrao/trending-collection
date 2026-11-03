import json
from huggingface_analytics import summarize, snapshot_outputs


def feed(day, ids, likes=None):
    return {'updated_at': f'2026-11-{day:02d}T02:00:00+00:00', 'items': [
        {'id': name, 'rank': rank, 'likes': (likes or {}).get(name, 10), 'url': f'https://huggingface.co/{name}'}
        for rank, name in enumerate(ids, 1)]}


def test_baseline_does_not_claim_new_entries():
    result = summarize([feed(1, ['a/a'])])
    assert result['comparison_date'] is None
    assert result['items'][0]['status'] == 'baseline'
    assert result['items'][0]['rank_change'] is None


def test_movement_reentry_and_missing_days():
    result = summarize([feed(1, ['a/a', 'b/b']), feed(2, ['b/b']),
                        feed(4, ['a/a', 'b/b', 'c/c'], {'b/b': 15})])
    a, b, c = result['items']
    assert a['status'] == 'reentry'
    assert a['rank_change'] is None
    assert b['rank_change'] == -1
    assert b['likes_change'] == 5
    assert c['status'] == 'new'
    assert result['comparison_interval_days'] == 2
    assert result['observed_days_7d'] == 3
    assert b['appearances_7d'] == 3


def test_rerun_replaces_day_and_excludes_future(tmp_path):
    history = tmp_path / 'api/huggingface/history/2026-11-02'
    history.mkdir(parents=True)
    (history / 'models.json').write_text(json.dumps(feed(2, ['a/a'])))
    later = tmp_path / 'api/huggingface/history/2026-11-03'
    later.mkdir()
    (later / 'models.json').write_text(json.dumps(feed(3, ['b/b'])))
    outputs, analytics = snapshot_outputs(tmp_path, {'models': feed(2, ['c/c'])})
    assert analytics['models']['observed_days_7d'] == 1
    assert analytics['models']['items'][0]['id'] == 'c/c'
    assert history / 'models.json' in outputs


def test_window_and_unknown_likes():
    now = feed(10, ['a/a'], {'a/a': None})
    result = summarize([feed(1, ['a/a']), now])
    assert result['items'][0]['appearances_7d'] == 1
    assert result['items'][0]['likes_change'] is None
    assert len(result['daily_leaders']) == 1


def test_dashboard_renders_observed_movement_and_gap():
    from readme_dashboard import momentum
    data = summarize([feed(1, ['a/a', 'b/b', 'd/d']), feed(3, ['b/b', 'c/c'])])
    rendered = '\n'.join(momentum({'models': data}))
    assert '2-day interval' in rendered
    assert '↑ 1' in rendered
    assert '1 new to tracking' in rendered
    assert 'Daily ranking leaders' in rendered
    assert 'c/c' in rendered


def test_no_movers_and_unknown_likes():
    from readme_dashboard import momentum
    data = summarize([feed(1, ['a/a']), feed(2, ['a/a'], {'a/a': None})])
    assert 'No upward rank moves' in '\n'.join(momentum({'models': data}))
