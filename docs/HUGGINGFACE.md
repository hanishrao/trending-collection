# Hugging Face trending feeds

The scheduled workflow collects the top 20 public models and top 20 public datasets by Hugging Face's `trendingScore` once per day. The README displays the first 10 from each ranking. This is a daily snapshot of Hugging Face's ranking, not a ranking calculated from daily downloads.

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

Unavailable scalar values are `null`, not zero. Parameter metadata is incomplete for some models. Download counts are usage proxies, not unique users; model and dataset counting methods differ. This collector does not infer benchmark quality, daily download growth, dataset row counts, or historical metrics from current totals. Each successful run replaces the latest snapshot.

The README section uses its own `HUGGINGFACE_START` / `HUGGINGFACE_END` markers outside the GitHub-generated section so either collector can refresh its content independently.

Sources: [Hub API](https://huggingface.co/docs/hub/api), [model download counting](https://huggingface.co/docs/hub/models-download-stats), [dataset download counting](https://huggingface.co/docs/hub/datasets-download-stats), [Hub client field reference](https://huggingface.co/docs/huggingface_hub/package_reference/hf_api).
