# Predictor collector methodology

This repository belongs to the UK inflation predictor fleet. It collects raw explanatory variables (X) only. Official forecast targets (Y), CPI weights and bottom-up reconciliation remain owned by `collector_ons_cpi` / `collector_ons_ex_cpi`.

## Collector contract

Each repository owns one publisher/source family and writes five tables in a schema whose name equals the repository name:

1. `metadata`
2. `time_series`
3. `availability`
4. `source_snapshots`
5. `logs`

Only raw published levels are stored. MoM, YoY, MTD, rolling averages, monthly aggregation, diffusion and model features are downstream research transformations.

## Source isolation

Source-specific download, parsing and validation live in `scripts/extract.py` or source-forced helper modules. There are no imports from other collector repositories, no shared Python package, no `BaseCollector`, ORM layer or migration framework. Template code is copied into each repository so every collector remains independently deployable and auditable.

## Validation

Before persistence the source module should validate at least source schema, duplicate keys, units, frequency/cadence, plausible values, expected history boundaries where defensible and non-empty output. Source changes that undermine an invariant fail loudly.

## Idempotency and revisions

An unchanged rerun writes no `time_series`, `availability`, `source_snapshots` or `metadata` rows. A later-day historical change creates a new vintage and keeps the old vintage. Point-in-time revision handling follows `POINT_IN_TIME.md`.

## Raw snapshots

Every parsed artifact is hashed with SHA-256. A changed upstream file becomes a new `source_snapshots` row rather than replacing the previous snapshot. Raw bytes stay outside Git in a gitignored location.

## DfT BUS0415 local bus fares index

One ODS workbook, `bus0415.ods`, discovered from the GOV.UK page rather than
pinned: the attachment URL carries a content hash that changes on every
republication. The pattern is anchored on the full table number because the
same page also serves `bus04i.ods` and `bus04ii.ods`, which are different
tables.

Both published sheets are collected. `BUS0415b` is a real-terms index, which
DfT deflates itself; that makes it a published series rather than a
transformation performed here, and its catalog description says so explicitly
so a research user does not deflate it twice.

Columns are classified by normalised header name, not position, so a cosmetic
relabelling ("non metropolitan" to "non-metropolitan") does not break
collection while a genuine change does. Three outcomes are possible and all
three are explicit: a known geography is collected, a known ONS comparator is
dropped with a log line, and anything else stops collection. A geography
disappearing from the header also stops collection, because a silently missing
dimension is how a published series vanishes without anything failing.

The quarterly `Year` + `Month` pair is converted to the first day of the
quarter's final month. A month outside Mar/Jun/Sep/Dec stops collection, as
does a reference date outside those months reaching validation.

Nothing is aggregated, deflated, chained or rebased here.
