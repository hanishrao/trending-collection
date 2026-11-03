# README refactor plan

Status: implemented locally. The first historical snapshot is saved; movement panels activate after a second successful daily observation. Seven-day summaries use expandable text tables.

## Reader goals

These are design hypotheses based on the current content, not findings from user interviews.

- A returning reader wants to spot what changed since the last visit.
- A developer wants to find a useful repository, model, or dataset quickly.
- An ML builder wants task, model size, license, and usage context before investigating a model.
- A researcher wants to distinguish sustained attention from a one-day appearance.
- An API consumer wants stable feed links and clear metric definitions.

## Proposed reading order

1. **Trending Collection** — subtitle: daily discovery across GitHub repositories and Hugging Face models and datasets. Specify GitHub history since 2015 separately from Hugging Face collection start.
2. **Navigation and freshness** — GitHub / Models / Datasets / Analytics / API & RSS. Show source-specific collection timestamps and coverage.
3. **Today at a glance** — three compact rows for GitHub, models and datasets, with a leading entry and a factual reason to inspect it. Add new-entry and mover highlights only when comparable snapshots exist.
4. **GitHub trending** — concise primary table, readable language names, bounded descriptions, links to full daily data. Keep six featured languages identifiable separately from broader API coverage. Put the longer language breakdown in a details block or linked report.
5. **Hugging Face models** — top five immediately visible; remaining entries in details or a linked daily report. Columns: model, task, parameters, downloads (30d), likes. Put license and richer metadata in the expanded view. Rank movement follows when historical snapshots are available.
6. **Hugging Face datasets** — top five immediately visible. Columns: dataset, category, downloads (30d), likes, license. Unknown categories remain unknown rather than being guessed from repository names.
7. **Changes and momentum** — separate GitHub and Hugging Face panels. Prioritize new entrants, rank movers, repeated appearances and seven-day histories. Do not combine platform scores.
8. **History and archives** — GitHub seven-day history, newcomers and Hall of Fame; Hugging Face equivalents as observation history accumulates. Collapse long historical tables.
9. **API & RSS** — one endpoint table covering GitHub, models and datasets, then links to schema documentation. Move the full JSON example out of the README.
10. **How to read the numbers** — short metric definitions, sample coverage and data limitations, with links to detailed methodology.

## Analytics and reader value

| Question | Proposed view | Available now? |
|---|---|---|
| What should I inspect today? | Separate top-ranked GitHub, model and dataset tables | Yes |
| Is this model relevant to my task? | Task, parameter count, license, library | Yes, with missing metadata |
| Which sampled projects have substantial usage? | 30-day downloads alongside current ranking | Yes; only within the collected sample |
| What is newly appearing? | First appearance in our tracked rankings | Needs dated Hugging Face snapshots |
| What moved up? | Rank difference between consecutive successful daily snapshots | Needs two comparable snapshots |
| What keeps appearing? | Days observed in the top 20 over the last seven days | Needs observation history |
| Which tasks dominate this sample? | Count of sampled models by task | Yes; label as sample composition |
| Is community attention increasing? | Change in total likes across observed dates | Needs history; report actual interval |

Keep raw trending scores in JSON and the expanded view. They determine ordering, but task, usage and movement offer more context in a compact README.

## Measurement rules

- A difference in rolling 30-day downloads is a change in the rolling total, not downloads during that day.
- New to the tracked top 20 does not mean newly released. Use creation timestamps for release age.
- A returning entry after a gap is a re-entry if it was previously observed.
- Rank movement is defined only when the entry appears in both comparable rankings. An absent entry is outside the sample, not rank 21.
- Missing collection days are gaps, not zero activity. Do not present multi-day differences as daily changes.
- Historical appearance counts describe our observed sample, not the whole platform.
- GitHub Hall of Fame should be labeled as archive appearances within tracked languages; archive coverage affects the totals.
- Model parameter count alone does not establish hardware compatibility. License tags are shortcuts to upstream terms, not commercial-use guarantees.
- Popularity is not benchmark quality. Never merge GitHub stars, Hugging Face likes and downloads into an unexplained universal score.
- Show source-specific freshness; an upstream failure must not make retained data appear newly collected.

## Implementation sequence

### 1. Fix presentation using existing data

- Give one README renderer responsibility for section ordering; collectors own source data.
- Place both Hugging Face sections directly after current GitHub discovery, before history and API documentation.
- Update the title, navigation, timestamps, language coverage labels and compact table formatting.
- Render existing task, size and license metadata with explicit unknown states.
- Consolidate API links and move long examples to docs.
- Repair the old-owner language registry URL that arrived with remote README updates during the previous rebase. The generator already uses the new owner.
- Keep current API paths and schemas compatible.

### 2. Persist history and derive analytics

- Save validated model and dataset snapshots under dated history paths as well as the existing latest-feed paths.
- Make one daily snapshot per UTC date; reruns replace that date rather than adding duplicate observations.
- Preserve collection timestamps and distinguish failed days from empty rankings.
- Calculate entrants, re-entries, comparable rank changes, like deltas and appearance counts from snapshots.
- Expose derived metrics in separate analytics JSON, with observation windows, coverage and definitions.
- Display a clear collecting-history state until sufficient observations exist. Do not invent historical values or fetch current values as backfilled history.

### 3. Add compact visual summaries

- After sufficient history exists, generate a small static seven-day chart or trend table that renders on GitHub.
- Include readable text equivalents and links to source snapshots.
- Start with rank trajectories and appearance counts; defer additional charts until they answer a distinct reader question.
- Consider broader per-task collection separately. Current top-20 snapshots cannot support whole-Hub market-share claims or comprehensive task leaderboards.

## Acceptance checks

- Readers see GitHub, models and datasets before API documentation or long archive tables.
- The first screen introduces both platforms and supplies direct navigation.
- Long descriptions and wide tables do not dominate the mobile reading experience.
- Generated updates preserve ordering, manual introduction text, and data from a source whose collection failed.
- Tests cover unknown metadata, Markdown escaping, duplicate-day runs, missing days, new entrants, re-entries, rank movement, and stale-source timestamps.
- Every displayed statistic has a source, scope, time window and defined missing-data behavior.
- Existing feed URLs continue to work.
