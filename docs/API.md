# GitHub JSON API and RSS

Base URL: `https://cdn.jsdelivr.net/gh/hanishrao/trending-collection@main/`

| Path | Contents |
|---|---|
| `api/daily/all.json` | Current daily GitHub trending ranking |
| `api/daily/{language}.json` | Daily ranking for a language |
| `api/weekly/{language}.json` | Weekly ranking for a language |
| `api/monthly/{language}.json` | Monthly ranking for a language |
| `languages.json` | Supported language registry |

Replace `.json` with `.xml` for RSS. The `all` slug also works for weekly and monthly feeds. Use a language alias from the registry, such as `python` or `c++`; hyphenate spaces. Files are refreshed by the scheduled workflow; CDN caches may delay updates. Check the feed's `pubDate`.

Example (illustrative values):

```json
{
  "title": "GitHub Python Languages Daily Trending",
  "description": "Daily Trending of Python Languages in GitHub",
  "link": "https://github.com/trending",
  "pubDate": "Tue, 03 Nov 2026 02:00:00 GMT",
  "items": [
    {
      "title": "owner/repository",
      "url": "https://github.com/owner/repository",
      "description": "Repository description",
      "language": "Python"
    }
  ]
}
```

The README features six languages. Its archive appearance counts reflect observed repositories in those tracked archive sections, not a platform-wide popularity ranking. See [Hugging Face feeds and analytics](HUGGINGFACE.md) for model and dataset endpoints.
