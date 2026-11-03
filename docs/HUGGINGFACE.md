# Hugging Face trending feeds

The scheduled workflow collects the top 20 public models and top 20 public datasets by Hugging Face's `trendingScore` once per day. The README displays the first five from each ranking, with all 20 available in expandable tables. This is a daily snapshot of Hugging Face's ranking, not a ranking calculated from daily downloads.

Run locally with the existing project dependencies:

```sh
python huggingface_collector.py
```

No access token is required. Only repository metadata is fetched; model weights and dataset files are never downloaded. Collection retries transient HTTP errors and uses a 30-second timeout per request. If either response fails validation or cannot be fetched, existing outputs are preserved. The workflow reports a warning and continues GitHub collection. Check `updated_at` to detect stale data.

## Endpoints

Paths are relative to `https://cdn.jsdelivr.net/gh/hanishrao/trending-collection@main/`:

| Path | Content |
|---|---|
| `api/huggingface/daily/models.json` | Model ranking and metrics |
| `api/huggingface/daily/datasets.json` | Dataset ranking and metrics |
| `api/huggingface/daily/models.xml` | Model RSS feed |
| `api/huggingface/daily/datasets.xml` | Dataset RSS feed |

These URLs become available after the files are pushed to `main`; CDN caches may delay updates. Existing GitHub endpoints retain their schema.

## JSON schema

The envelope contains `title`, `source`, `updated_at` (UTC ISO 8601), `ranking` (`huggingface_trending_score`), `download_window_days` (30), and `items`.

| Item field | Meaning |
|---|---|
| `rank`, `id`, `url` | Position in the fetched ranking, repository ID and public URL |
| `downloads_30d` | Hugging Face download count over the last 30 days |
| `downloads_all_time` | All-time download count when exposed by the API |
| `likes` | Current total likes |
| `trending_score` | Upstream trending score; not a benchmark or daily growth measure |
| `created_at`, `last_modified` | Upstream timestamps when available |
| `licenses`, `tags` | License tags and all repository tags; empty lists if absent |
| `task`, `library` | Models only: pipeline task and library |
| `parameters` | Models only: total from Safetensors metadata, when available |
| `task_categories` | Datasets only: categories extracted from tags |

Unavailable scalar values are `null`, not zero. Parameter metadata is incomplete for some models. Download counts are usage proxies, not unique users; model and dataset counting methods differ. This collector does not infer benchmark quality, daily download growth, dataset row counts, or historical metrics from current totals. Each successful run replaces the latest feed and saves one snapshot per UTC date. Reruns on the same date replace that day’s observation.

A shared README renderer controls section order inside `TRENDING_START` / `TRENDING_END`. Both collectors refresh it from saved source data; failed collection does not advance that source’s timestamps. Manual text outside the generated block is preserved. The old appended Hugging Face block is migrated automatically.

Sources: [Hub API](https://huggingface.co/docs/hub/api), [model download counting](https://huggingface.co/docs/hub/models-download-stats), [dataset download counting](https://huggingface.co/docs/hub/datasets-download-stats), [Hub client field reference](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api).


## Historical observations and analytics

- `api/huggingface/history/YYYY-MM-DD/models.json` and `datasets.json` retain daily UTC snapshots using the same feed schema.
- `api/huggingface/analytics/models.json` and `datasets.json` contain derived observations, independently for each ranking.
- Existing latest JSON and RSS paths remain unchanged.

Analytics include `snapshot_date`, `tracking_started`, `comparison_date`, `comparison_interval_days`, `window_start`, `window_days`, `observed_days_7d`, `sample_limit`, `daily_leaders`, and `items`. The `updated_at` timestamp comes from the source snapshot, not the rendering time.

Each analytical item includes `id`, `url`, `rank`, `status`, `first_seen`, `appearances_7d`, `rank_change`, and `likes_change`.

| Field / status | Definition |
|---|---|
| `baseline` | First successful observation; no new-entry or movement claim |
| `new` | First appearance in our saved observations after the baseline |
| `reentry` | Seen in earlier history, absent from the previous observation, present again |
| `continuing` | Present in both latest and previous observations |
| `rank_change` | Previous rank minus current rank; positive means rising; null if either rank is unavailable |
| `likes_change` | Change in total likes across the two observed dates, or null when unavailable |
| `appearances_7d` | Number of observed dates containing this entry in the seven-calendar-day window ending on the snapshot date |
| `daily_leaders` | First-ranked entry on each available date within that same window |

The comparison uses the latest earlier successful observation. A two-day gap is labeled as a two-day comparison, never daily growth. Missing days count toward the seven-day window but do not count as observations. Falling outside the top 20 is not treated as rank 21. Historical reruns exclude future observations from calculations.

New to tracking does not imply a newly released model or dataset. Current top-20 samples cannot establish whole-Hub market share. Task/category counts in the README describe only the current sample; datasets can have multiple categories. Rolling download differences are deliberately not reported as daily downloads.

On the first day, the README shows a collecting-history state. Subsequent days show new entries, re-entries and upward rank moves, with expandable appearance and daily-leader tables. These text tables are the initial seven-day visualization and need no external chart renderer.
