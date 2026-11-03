import os
import re
import datetime
import json
from pathlib import Path

REPO_RE = re.compile(r'^\* \[.+?\]\((https://github\.com/[^)]+)\):(.*)$')
LANG_RE = re.compile(r'^#### (\w+)$')

LANG_EMOJI = {
    'python': '🐍',
    'rust': '🦀',
    'javascript': '⚡',
    'go': '🐹',
    'swift': '🍎',
    'typescript': '🔷',
}
LANGUAGES = ['python', 'rust', 'javascript', 'go', 'swift', 'typescript']

MARKER_START = '<!-- TRENDING_START -->'
MARKER_END = '<!-- TRENDING_END -->'


def parse_day_file(filepath):
    """Return list of {url, description, language} from a daily .md file."""
    entries = []
    current_lang = None
    with open(filepath, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            lang_match = LANG_RE.match(line)
            if lang_match:
                current_lang = lang_match.group(1)
                continue
            repo_match = REPO_RE.match(line)
            if repo_match and current_lang:
                entries.append({
                    'url': repo_match.group(1),
                    'description': repo_match.group(2),
                    'language': current_lang,
                })
    return entries


def count_total_days(root='.'):
    count = 0
    for entry in os.listdir(root):
        year_path = os.path.join(root, entry)
        if os.path.isdir(year_path) and entry.isdigit():
            count += sum(1 for f in os.listdir(year_path) if f.endswith('.md'))
    return count


def compute_last_7_days(root='.', today=None):
    if today is None:
        today = datetime.date.today()
    result = []
    for i in range(7):
        d = today - datetime.timedelta(days=i)
        filepath = os.path.join(root, str(d.year), d.strftime('%Y-%m-%d') + '.md')
        if not os.path.exists(filepath):
            continue
        entries = parse_day_file(filepath)
        day_data = {'date': d.strftime('%Y-%m-%d'), 'top': {}}
        seen = set()
        for entry in entries:
            lang = entry['language']
            if lang not in seen:
                day_data['top'][lang] = entry['url']
                seen.add(lang)
        result.append(day_data)
    return result


def compute_hall_of_fame(root='.', top_n=10):
    counts = {}
    for year_entry in sorted(os.listdir(root)):
        year_path = os.path.join(root, year_entry)
        if not (os.path.isdir(year_path) and year_entry.isdigit()):
            continue
        for fname in sorted(os.listdir(year_path)):
            if not fname.endswith('.md'):
                continue
            filepath = os.path.join(year_path, fname)
            entries = parse_day_file(filepath)
            urls_today = {e['url'] for e in entries}
            for url in urls_today:
                counts[url] = counts.get(url, 0) + 1
    top = sorted(counts.items(), key=lambda x: -x[1])[:top_n]
    return [{'url': url, 'days': days} for url, days in top]


def compute_new_this_month(root='.', today=None, max_results=10):
    if today is None:
        today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=30)
    first_seen = {}  # url -> (date, description, language)
    for year_entry in sorted(os.listdir(root)):
        year_path = os.path.join(root, year_entry)
        if not (os.path.isdir(year_path) and year_entry.isdigit()):
            continue
        for fname in sorted(os.listdir(year_path)):
            if not fname.endswith('.md'):
                continue
            date_str = fname[:-3]
            try:
                file_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                continue
            filepath = os.path.join(year_path, fname)
            for entry in parse_day_file(filepath):
                url = entry['url']
                if url not in first_seen:
                    first_seen[url] = (file_date, entry['description'], entry['language'])
    new_repos = [
        {
            'url': url,
            'first_seen': d.strftime('%Y-%m-%d'),
            'description': desc,
            'language': lang,
        }
        for url, (d, desc, lang) in first_seen.items()
        if d > cutoff
    ]
    new_repos.sort(key=lambda x: x['first_seen'], reverse=True)
    return new_repos[:max_results]


def render_readme(today_entries, last7, hall_of_fame, new_this_month, total_days, year_list, today_str,
                  feeds=None, analytics=None):
    from readme_dashboard import render
    return render(today_entries, last7, hall_of_fame, new_this_month, total_days, year_list,
                  today_str, feeds, analytics)


def update_readme(root='.', today=None):
    if today is None:
        today = datetime.date.today()

    archive_dates = []
    for path in Path(root).glob('[0-9][0-9][0-9][0-9]/*.md'):
        try:
            date = datetime.date.fromisoformat(path.stem)
        except ValueError:
            continue
        if date <= today:
            archive_dates.append((date, path))
    source_date, source_path = max(archive_dates) if archive_dates else (today, None)
    today_entries = parse_day_file(source_path) if source_path else []

    last7 = compute_last_7_days(root=root, today=today)
    hall_of_fame = compute_hall_of_fame(root=root)
    new_this_month = compute_new_this_month(root=root, today=today)
    total_days = count_total_days(root=root)
    year_list = [
        d for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d)) and d.isdigit()
    ]

    # Source files retain their own timestamps when a collection fails.
    def load_feeds(folder):
        result = {}
        for kind in ('models', 'datasets'):
            path = Path(root) / 'api' / 'huggingface' / folder / f'{kind}.json'
            if path.exists():
                result[kind] = json.loads(path.read_text(encoding='utf-8'))
        return result

    content = render_readme(today_entries, last7, hall_of_fame, new_this_month, total_days, year_list,
                            source_date.isoformat(), load_feeds('daily'), load_feeds('analytics'))

    readme_path = os.path.join(root, 'README.md')
    with open(readme_path, 'r', encoding='utf-8') as f:
        readme = f.read()

    # Migrate the former appended block into the single generated dashboard.
    readme = re.sub(r'\n*<!-- HUGGINGFACE_START -->.*?<!-- HUGGINGFACE_END -->', '', readme, flags=re.S)
    start_idx = readme.find(MARKER_START)
    end_idx = readme.find(MARKER_END)

    if start_idx == -1 or end_idx == -1:
        new_readme = readme.rstrip() + f'\n\n{MARKER_START}\n{content}\n{MARKER_END}\n'
    else:
        before = readme[:start_idx]
        after = readme[end_idx + len(MARKER_END):]
        new_readme = before + MARKER_START + '\n' + content + '\n' + MARKER_END + after

    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(new_readme)
