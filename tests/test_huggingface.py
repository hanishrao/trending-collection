import json
from unittest.mock import Mock
from xml.etree import ElementTree

import pytest

from huggingface_collector import collect, run


def session_for(payload):
    session = Mock()
    session.get.return_value.json.return_value = payload
    return session


def test_metrics_and_missing_values():
    session = session_for([{'id': 'org/model', 'downloads': 120, 'likes': 5,
                           'safetensors': {'total': 123}, 'tags': ['license:mit']}])
    item = collect(session, 'models')['items'][0]
    assert item['downloads_30d'] == 120
    assert item['parameters'] == 123
    assert item['licenses'] == ['mit']
    assert item['trending_score'] is None
    assert item['url'] == 'https://huggingface.co/org/model'
    assert session.get.call_args.kwargs['timeout'] == 30


@pytest.mark.parametrize('payload', [[], {}, [{'id': '../bad'}], [{'likes': 2}]])
def test_invalid_response(payload):
    with pytest.raises(ValueError):
        collect(session_for(payload), 'datasets')


def test_http_error():
    session = session_for([])
    session.get.return_value.raise_for_status.side_effect = RuntimeError('offline')
    with pytest.raises(RuntimeError, match='offline'):
        collect(session, 'models')


def test_outputs_and_readme_preservation(tmp_path):
    readme = tmp_path / 'README.md'
    readme.write_text('Existing GitHub content\n')
    session = session_for([{'id': 'org/item', 'likes': 7, 'downloads': 42,
                           'tags': ['task_categories:text|<test>']}])
    run(tmp_path, session)
    run(tmp_path, session)
    content = readme.read_text()
    assert content.startswith('Existing GitHub content\n')
    assert content.count('## 🤗 Hugging Face models') == 1
    assert '42' in content
    assert 'text&#124;&lt;test&gt;' in content
    for kind in ('models', 'datasets'):
        feed = json.loads((tmp_path / 'api/huggingface/daily' / f'{kind}.json').read_text())
        assert feed['items'][0]['likes'] == 7
        rss = ElementTree.parse(tmp_path / 'api/huggingface/daily' / f'{kind}.xml')
        assert rss.findtext('channel/item/link') == feed['items'][0]['url']


def test_failure_preserves_previous_outputs(tmp_path):
    (tmp_path / 'README.md').write_text('Original')
    session = session_for([{'id': 'org/model'}])
    session.get.return_value.json.side_effect = [[{'id': 'org/model'}], []]
    with pytest.raises(ValueError):
        run(tmp_path, session)
    assert (tmp_path / 'README.md').read_text() == 'Original'
    assert not (tmp_path / 'api').exists()


def test_github_refresh_preserves_huggingface_section(tmp_path):
    from readme_generator import update_readme

    (tmp_path / 'README.md').write_text('<!-- TRENDING_START -->\nOld\n<!-- TRENDING_END -->\n')
    run(tmp_path, session_for([{'id': 'org/item', 'downloads': 1}]))
    import json
    before = json.loads((tmp_path / 'api/huggingface/daily/models.json').read_text())
    update_readme(root=str(tmp_path))
    content = (tmp_path / 'README.md').read_text()
    from readme_dashboard import timestamp
    assert timestamp(before['updated_at']) in content
    assert 'org/item' in content
    assert content.count('## 🤗 Hugging Face models') == 1
    assert content.index('Hugging Face models') < content.index('JSON API & RSS')


def test_failed_refresh_retains_saved_feeds_and_timestamps(tmp_path):
    (tmp_path / 'README.md').write_text('Manual introduction\n')
    run(tmp_path, session_for([{'id': 'org/model'}]))
    before = {path: path.read_bytes() for path in tmp_path.rglob('*') if path.is_file()}
    session = session_for([])
    with pytest.raises(ValueError):
        run(tmp_path, session)
    assert all(path.read_bytes() == content for path, content in before.items())


def test_repeat_collection_has_one_observation_per_day(tmp_path):
    (tmp_path / 'README.md').write_text('Introduction\n')
    run(tmp_path, session_for([{'id': 'org/first'}]))
    run(tmp_path, session_for([{'id': 'org/second'}]))
    paths = list((tmp_path / 'api/huggingface/history').glob('*/models.json'))
    assert len(paths) == 1
    assert json.loads(paths[0].read_text())['items'][0]['id'] == 'org/second'
    analytics = json.loads((tmp_path / 'api/huggingface/analytics/models.json').read_text())
    assert analytics['observed_days_7d'] == 1
    assert analytics['comparison_date'] is None
