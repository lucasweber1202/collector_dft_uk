# Point-in-time contract

This collector stores predictor data for forecasting. A historical backtest must never see information that was unavailable at the simulated forecast instant.

## Stored dates

- `reference_date`: period the observation describes.
- `vintage_date`: UTC date on which this collector stored that version.
- `release_date`: source publication date when explicitly supported.
- `available_at`: earliest defensible instant at which this stored vintage could have been known.
- `collected_at`: timestamp of this pipeline run.

`availability_basis` is one of `official_timestamp`, `official_date`, `archived_release`, `first_seen`, `inferred`, `unknown`.

By default `get_series_as_of()` accepts only `official_timestamp`, `official_date`, `archived_release`, and `first_seen`. `inferred` and `unknown` require explicit opt-in.

## Historical revisions

A revised value for an already stored `(series_id, reference_date)` must not reuse the original publication timestamp. Unless the source exposes explicit evidence for the revision release, the revised vintage is stamped:

- `available_at = collected_at`
- `availability_basis = first_seen`
- `release_date = NULL`

This prevents a 2026 revision of a 2024 observation from appearing in a 2024 backtest.

## Same-day revisions

The fleet schema uses `vintage_date DATE`. Two different intraday revisions therefore cannot be represented without overwriting one information set. Predictor collectors fail closed when an already stored vintage changes again on the same UTC date. Retry after the UTC date changes rather than rewriting history.

## As-of guarantee

`get_series_as_of(series_id, as_of)` filters on `available_at <= as_of` before ranking vintages. A later revision therefore cannot mask the vintage that was actually current at the historical instant.

## DfT BUS0415 release attribution

### Only a fares release counts as a release

The GOV.UK page is a *collection* covering every BUS table — annual bus
statistics, concessionary travel, vehicle distance, BUS01 to BUS08 and the
fares index. Its change history therefore mixes releases that had nothing to do
with BUS0415.

Attributing a fares quarter to, say, a concessionary-travel update would claim
the figure was knowable before it was actually published. That is a look-ahead,
so this collector filters the change history: only entries naming `BUS0415` or
"bus fares" are treated as releases for this data set. Verified against the
live history on 2026-09-16, that keeps 11 of 17 entries and discards the
annual-bus, concessionary-travel, financial-data and BUS01-BUS08 updates.
Discarding an entry can only push availability later, never earlier, so the
filter is conservative in the safe direction.

### Measured schedule

| Reference quarter ends | Published | Lag |
| --- | --- | --- |
| March 2026 | 2026-06-18 | 109 days |
| September 2025 | 2025-11-26 | 86 days |
| June 2025 | 2025-09-30 | 121 days |
| March 2025 | 2025-06-19 | 110 days |
| September 2024 | 2024-12-18 | 108 days |
| March 2024 | 2024-06-12 | 103 days |

Attribution window 70–140 days after the first of the quarter's final month;
inferred fallback 110 days.

### Coverage is weak before 2023

The change history for this page begins 2023-01-31 ("First published"), while
the data reaches back to 2005-03. Everything before the first fares release is
therefore `availability_basis = inferred`: a reconstruction from the observed
release rule, not evidence, and excluded from `get_series_as_of()` by default.

On the verified 2026-09-16 build: **176 observations carry
`official_timestamp`, 1,184 carry `inferred`, none `unknown`.** A backtest
restricted to point-in-time evidence therefore effectively starts in 2023 for
this data set. That is a real limitation of the source, not of the collector,
and it must not be papered over by back-dating availability from the reference
date.
