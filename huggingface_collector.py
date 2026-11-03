"""Collect public Hugging Face trending metadata; no model files or token needed."""

import datetime
import html
import json
import os
from pathlib import Path
import re
import tempfile
from xml.etree import ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

START = '<!-- HUGGINGFACE_START -->'
END = '<!-- HUGGINGFACE_END -->'
CDN = 'https://cdn.jsdelivr.net/gh/hanishrao/trending-collection@main/api/huggingface/daily'
FIELDS = ['downloads', 'downloadsAllTime', 'likes', 'trendingScore', 'tags',
          'createdAt', 'lastModified']


def collect(session, kind):
    """Fetch one bounded ranking, retaining unknown metrics as null."""
    if kind not in ('models', 'datasets'):
        raise ValueError('Unsupported Hugging Face repository type')
    fields = FIELDS + (['pipeline_tag', 'library_name', 'safetensors'] if kind == 'models' else [])
    response = session.get(
        f'https://huggingface.co/api/{kind}',
        params={'sort': 'trendingScore', 'direction': -1, 'limit': 20, 'expand[]': fields},
        timeout=30,
    )
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list) or not rows:
        raise ValueError(f'Empty or invalid Hugging Face {kind} response')
    items = []
    for rank, row in enumerate(rows, 1):
        repo_id = row.get('id') if isinstance(row, dict) else None
        if not isinstance(repo_id, str) or not re.fullmatch(r'[\w-]+/[\w.-]+', repo_id):
            raise ValueError('Invalid Hugging Face repository ID')
        tags = row.get('tags') or []
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError('Invalid Hugging Face tags')
        prefix = 'datasets/' if kind == 'datasets' else ''
        item = {
            'rank': rank, 'id': repo_id, 'url': f'https://huggingface.co/{prefix}{repo_id}',
            'downloads_30d': row.get('downloads'),
            'downloads_all_time': row.get('downloadsAllTime'),
            'likes': row.get('likes'), 'trending_score': row.get('trendingScore'),
            'created_at': row.get('createdAt'), 'last_modified': row.get('lastModified'),
            'licenses': [t.removeprefix('license:') for t in tags if t.startswith('license:')],
            'tags': tags,
        }
        if kind == 'models':
            item.update(task=row.get('pipeline_tag'), library=row.get('library_name'),
                        parameters=(row.get('safetensors') or {}).get('total'))
        else:
            item['task_categories'] = [t.removeprefix('task_categories:') for t in tags
                                       if t.startswith('task_categories:')]
        items.append(item)
    return {'title': f'Hugging Face Trending {kind.title()}',
            'source': f'https://huggingface.co/{kind}?sort=trending',
            'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'ranking': 'huggingface_trending_score', 'download_window_days': 30,
            'items': items}


def rss(feed):
    root = ET.Element('rss', version='2.0')
    channel = ET.SubElement(root, 'channel')
    for key, value in [('title', feed['title']), ('link', feed['source']),
                       ('description', 'Trending metadata; downloads cover the last 30 days.')]:
        ET.SubElement(channel, key).text = value
    for row in feed['items']:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = row['id']
        ET.SubElement(item, 'link').text = row['url']
        ET.SubElement(item, 'guid', isPermaLink='true').text = row['url']
        ET.SubElement(item, 'description').text = (
            f"Downloads (30d): {display(row['downloads_30d'])}; Likes: {display(row['likes'])}; "
            f"Trending score: {display(row['trending_score'])}")
    return ET.tostring(root, encoding='unicode', xml_declaration=True) + '\n'


def display(value):
    if value is None:
        return '—'
    return format(value, ',') if isinstance(value, (int, float)) else str(value)


def cell(value):
    return html.escape(display(value)).replace('|', '&#124;').replace('\n', ' ')


def render_section(feeds):
    lines = [START, '## 🤗 Hugging Face Trending', '',
             'Top models and datasets by Hugging Face trending score, refreshed daily. '
             'Downloads cover the **last 30 days**, not the collection day. '
             'Missing metrics are shown as — (JSON: `null`).', '']
    for kind, feed in feeds.items():
        lines += [f'### Trending {kind.title()}', '', f"Updated: {feed['updated_at']}", '',
                  '| Repository | Downloads (30d) | Likes | Trending score | Task / category |',
                  '|---|---:|---:|---:|---|']
        for row in feed['items'][:10]:
            task = row.get('task') or ', '.join(row.get('task_categories', [])) or None
            lines.append(f"| [{row['id']}]({row['url']}) | {cell(row['downloads_30d'])} | "
                         f"{cell(row['likes'])} | {cell(row['trending_score'])} | {cell(task)} |")
        lines += ['', f'[JSON API]({CDN}/{kind}.json) · [RSS feed]({CDN}/{kind}.xml)', '']
    lines += ['The JSON feeds include up to 20 entries each, with available all-time downloads, '
              'licenses, tags, creation/update dates, model task, library and Safetensors parameter count. '
              'Parameter counts are unavailable for some models. Popularity metrics are not quality benchmarks.', '',
              '[API schema and collection details](docs/HUGGINGFACE.md)', END]
    return '\n'.join(lines)


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def run(root='.', session=None):
    """Fetch and render both feeds before replacing any previous outputs."""
    root = Path(root)
    if session is None:
        with requests.Session() as session:
            retry = Retry(total=4, backoff_factor=2, status_forcelist=(429, 500, 502, 503, 504),
                          allowed_methods=frozenset(['GET']))
            session.mount('https://', HTTPAdapter(max_retries=retry))
            return run(root, session)
    feeds = {kind: collect(session, kind) for kind in ('models', 'datasets')}
    readme_path = root / 'README.md'
    readme = readme_path.read_text(encoding='utf-8')
    section = render_section(feeds)
    if START in readme and END in readme:
        before, rest = readme.split(START, 1)
        _, after = rest.split(END, 1)
        readme = before + section + after
    else:
        readme = readme.rstrip() + '\n\n' + section + '\n'
    outputs = {}
    for kind, feed in feeds.items():
        base = root / 'api' / 'huggingface' / 'daily'
        outputs[base / f'{kind}.json'] = json.dumps(feed, indent=2, ensure_ascii=False) + '\n'
        outputs[base / f'{kind}.xml'] = rss(feed)
    outputs[readme_path] = readme
    for path, content in outputs.items():
        atomic_write(path, content)


if __name__ == '__main__':
    run()
