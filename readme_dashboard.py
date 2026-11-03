"""GitHub-friendly discovery dashboard with one shared section order."""
import html
import datetime as dt

CDN = 'https://cdn.jsdelivr.net/gh/hanishrao/trending-collection@main'


def text(value, limit=100):
    value = '—' if value is None or value == '' else ' '.join(str(value).split())
    if len(value) > limit:
        value = value[:limit - 1].rstrip() + '…'
    return html.escape(value).replace('|', '&#124;').replace('[', '&#91;').replace(']', '&#93;')


def number(value):
    return '—' if value is None else f'{value:,}'


def size(value):
    if value is None:
        return '—'
    for divisor, suffix in [(1e12, 'T'), (1e9, 'B'), (1e6, 'M')]:
        if value >= divisor:
            return f'{value / divisor:.1f}'.rstrip('0').rstrip('.') + suffix
    return str(value)


def link(row):
    return f"[{text(row['id'], 58)}]({row['url']})"


def timestamp(value):
    if not value:
        return '—'
    parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    return parsed.astimezone(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')


def language_name(value):
    return {'javascript': 'JavaScript', 'typescript': 'TypeScript'}.get(value, value.title())


def table(headers, rows):
    return ['| ' + ' | '.join(headers) + ' |', '|' + '---|' * len(headers)] + [
        '| ' + ' | '.join(row) + ' |' for row in rows]


def details(label, content):
    return ['<details>', f'<summary>{label}</summary>', ''] + content + ['', '</details>', '']


def hf_section(kind, feed):
    lines = [f'<a id="{kind}"></a>', '', f'## 🤗 Hugging Face {kind}', '']
    if not feed:
        return lines + ['Awaiting the first successful collection.', '']
    lines += [f"Collected {timestamp(feed['updated_at'])} · Top {len(feed['items'])} by Hugging Face trending rank.", '']
    model = kind == 'models'
    headers = ['Model' if model else 'Dataset', 'Task' if model else 'Category']
    if model:
        headers += ['Parameters']
    headers += ['Downloads · 30d', 'Likes']
    if not model:
        headers += ['License']
    rows = []
    for item in feed['items']:
        category = item.get('task') if model else ', '.join(item.get('task_categories', []))
        row = [link(item), text(category, 35)]
        if model:
            row += [size(item.get('parameters'))]
        row += [number(item.get('downloads_30d')), number(item.get('likes'))]
        if not model:
            row += [text(', '.join(item.get('licenses', [])), 30)]
        rows.append(row)
    lines += table(headers, rows[:5]) + ['']
    if len(rows) > 5:
        lines += details(f'Explore all {len(rows)} {kind}', table(headers, rows))
    if model:
        metadata = [[link(item), text(', '.join(item.get('licenses', [])), 35),
                     text(item.get('library')), timestamp(item.get('last_modified'))]
                    for item in feed['items']]
        lines += details('Model licenses, libraries and update dates',
                         table(['Model', 'License', 'Library', 'Last updated'], metadata))
    tasks = {}
    for item in feed['items']:
        categories = [item.get('task') or 'Unknown'] if model else item.get('task_categories') or ['Unknown']
        for category in categories:
            tasks[category] = tasks.get(category, 0) + 1
    mix = sorted(tasks.items(), key=lambda pair: (-pair[1], pair[0]))[:4]
    lines += ['**In this sample:** ' + ' · '.join(f'{text(task)}: {count}' for task, count in mix) + '.',
              ('Each model has one task label.' if model else 'Datasets may have multiple categories.') +
              ' Counts describe this collected ranking, not the whole Hub.', '']
    return lines


def momentum(analytics):
    lines = ['<a id="analytics"></a>', '', '## 📊 Changes and momentum', '',
             'Hugging Face movement is measured within our tracked top 20, separately for models and datasets.', '']
    for kind in ('models', 'datasets'):
        data = analytics.get(kind)
        lines += [f'### {kind.title()}', '']
        if not data or not data.get('comparison_date'):
            lines += ['**Collecting history** — rank movement and new-entry signals need a second successful daily snapshot.', '']
            if data:
                lines += [f"Tracking since {data['tracking_started']}; {data['observed_days_7d']}/7 days observed. The initial ranking is a baseline.", '']
            continue
        items = data['items']
        lines += [f"Comparing {data['snapshot_date']} with {data['comparison_date']} "
                  f"({data['comparison_interval_days']}-day interval). "
                  f"Coverage: {data['observed_days_7d']}/7 days observed.", '',
                  f"**{sum(row['status'] == 'new' for row in items)} new to tracking** · "
                  f"**{sum(row['status'] == 'reentry' for row in items)} re-entries**", '']
        movers = sorted([row for row in items if (row['rank_change'] or 0) > 0],
                        key=lambda row: -row['rank_change'])[:5]
        if movers:
            lines += table(['Rising entry', 'Rank change', 'Likes change'], [
                [link(row), f"↑ {row['rank_change']}",
                 f"{row['likes_change']:+,}" if row['likes_change'] is not None else '—'] for row in movers]) + ['']
        else:
            lines += ['No upward rank moves among entries present in both snapshots.', '']
        signals = sorted(items, key=lambda row: (-row['appearances_7d'], row['rank']))[:5]
        lines += details('Repeat appearances in the last seven days', table(['Entry', 'Days observed', 'First observed'], [
            [link(row), str(row['appearances_7d']), row['first_seen']] for row in signals]))
        lines += details('Daily ranking leaders · last seven days', table(['Snapshot date', 'Leader'], [
            [row['date'], link(row)] for row in data['daily_leaders']]))
        entrants = [row for row in items if row['status'] in ('new', 'reentry')]
        if entrants:
            lines += details('New entries and returning entries', table(['Entry', 'Status', 'First observed'], [
                [link(row), row['status'], row['first_seen']] for row in entrants]))
    return lines


def render(today_entries, last7, hall, newcomers, total, years, date, feeds=None, analytics=None):
    feeds, analytics = feeds or {}, analytics or {}
    github_date = last7[0]['date'] if last7 else (date if today_entries else None)
    lines = ['# 📈 Trending Collection', '',
             'Discover GitHub repositories, Hugging Face models and datasets worth exploring.', '',
             '[GitHub](#github) · [Models](#models) · [Datasets](#datasets) · '
             '[Analytics](#analytics) · [Archives](#archives) · [API & RSS](#api)', '',
             f'**{total:,} GitHub days archived since 2015** · **6 featured languages** · **Daily collection**', '',
             'Hugging Face history begins with the first saved snapshot. Each source’s collection date appears below.', '',
             '## Today at a glance', '']
    overview = [['GitHub', f'Latest archive: {github_date}' if github_date else 'Awaiting data',
                 'Browse tools and libraries across six featured languages']]
    for kind in ('models', 'datasets'):
        feed = feeds.get(kind)
        overview.append([f'Hugging Face {kind}', timestamp(feed['updated_at']) if feed else 'Awaiting data',
                         link(feed['items'][0]) if feed and feed['items'] else '—'])
    lines += table(['Explore', 'Source freshness', 'Start here'], overview) + ['',
              '<a id="github"></a>', '', '## 🔥 Today\'s Trending · GitHub trending', '',
              f'Archive date: **{github_date or "unavailable"}**. One pick per featured language; expand for the top three.', '']
    by_language = {}
    for row in today_entries:
        by_language.setdefault(row['language'], []).append(row)
    def github_row(row):
        return [f"[{text(row['url'].removeprefix('https://github.com/'))}]({row['url']})",
                text(language_name(row['language'])), text(row['description'], 110)]
    lines += table(['Repository', 'Language', 'What it does'], [github_row(rows[0]) for rows in by_language.values()]) + ['']
    if not today_entries:
        lines += ['No archive for the requested date; browse the latest available dates below.', '']
    lines += details('Top three per featured language', table(['Repository', 'Language', 'What it does'],
                     [github_row(row) for rows in by_language.values() for row in rows[:3]]))
    if github_date:
        lines += [f'[Full GitHub day](./{github_date[:4]}/{github_date}.md)', '']
    for kind in ('models', 'datasets'):
        lines += hf_section(kind, feeds.get(kind))
    lines += momentum(analytics)
    lines += ['### 🆕 New This Month · GitHub', '',
              'First observed in our tracked GitHub archive during the last 30 days; these are not necessarily new projects.', '']
    lines += table(['Repository', 'Language', 'First observed'], [
        [github_row(row)[0], text(language_name(row['language'])), row['first_seen']] for row in newcomers[:5]]) + ['']
    lines += ['<a id="archives"></a>', '', '## 🗄 Archive and history', '']
    languages = ['python', 'rust', 'javascript', 'go', 'swift', 'typescript']
    lines += details('📅 Last 7 Days · GitHub leaders', table(['Date'] + [language_name(lang) for lang in languages], [
        [f"[{day['date']}](./{day['date'][:4]}/{day['date']}.md)"] + [
            f"[{text(day['top'][lang].split('/')[-1])}]({day['top'][lang]})" if lang in day['top'] else '—'
            for lang in languages] for day in last7]))
    lines += details('🏆 Hall of Fame · GitHub archive appearances',
                     ['Counts reflect our tracked languages and available archive days, not platform-wide popularity.', ''] +
                     table(['Repository', 'Days observed'], [[f"[{text(row['url'].removeprefix('https://github.com/'))}]({row['url']})",
                                                             number(row['days'])] for row in hall]))
    lines += [' · '.join(f'[{year}](./{year}/)' for year in sorted(years, reverse=True)), '',
              '[Hugging Face daily snapshots](api/huggingface/history/)', '',
              '<a id="api"></a>', '', '## 🚀 JSON API & RSS Feeds', '',
              'Use the feeds in your own tools, or subscribe with an RSS reader. GitHub feeds cover the supported language registry; the README features six languages.', '']
    rows = []
    for name, path in [('GitHub · all', 'api/daily/all'), ('GitHub · language', 'api/daily/{language}'),
                       ('Hugging Face · models', 'api/huggingface/daily/models'),
                       ('Hugging Face · datasets', 'api/huggingface/daily/datasets')]:
        rows.append([name, f'[JSON]({CDN}/{path}.json)', f'[RSS]({CDN}/{path}.xml)'])
    lines += table(['Collection', 'JSON', 'RSS'], rows) + ['',
              f'[Language registry]({CDN}/languages.json) · [Hugging Face schema](docs/HUGGINGFACE.md) · [GitHub API guide](docs/API.md)', '',
              f'Analytics: [Models]({CDN}/api/huggingface/analytics/models.json) · '
              f'[Datasets]({CDN}/api/huggingface/analytics/datasets.json)', '',
              '## Reading the numbers', '',
              '- **Downloads** cover the rolling last 30 days, not today or unique users.',
              '- **Rank movement** compares observed snapshots; positive changes mean rising. Missing days stay gaps.',
              '- **New** means first observed in our rankings, not newly released. Re-entries were observed before.',
              '- **Parameters** come from available Safetensors metadata; they do not guarantee hardware compatibility.',
              '- **Licenses** link back through each repository to its terms. Popularity does not measure model quality.',
              '- **—** means unavailable. Source timestamps remain unchanged when collection fails.', '']
    return '\n'.join(lines)
