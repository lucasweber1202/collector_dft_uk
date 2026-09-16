# collector_dft_uk

Standalone collector for Department for Transport datasets relevant to UK
inflation.

The repository owns DfT extraction and raw point-in-time persistence. It does
not map predictors to CPI targets or calculate modelling features; those tasks
belong to [`uk_inflation_predictors`](https://github.com/lucasweber1202/uk_inflation_predictors).

Schema: `collector_dft_uk`.

## Current coverage

| `source_id` | Dataset | Frequency | History | Series | Artifact |
| --- | --- | --- | --- | --- | --- |
| `dft_bus_fares` | [Bus statistics data tables, BUS0415](https://www.gov.uk/government/statistical-data-sets/bus-statistics-data-tables) | quarterly | 2005-03 → | 16 | ODS |

Verified on 2026-09-16: 16 series and 1,360 observations from one raw artifact.

### BUS0415 — local bus fares index

`bus0415.ods` carries two data sheets over the same eight geographies:

| Sheet | Measure token | Meaning |
| --- | --- | --- |
| `BUS0415a` | `CURRENT` | fares index at current prices |
| `BUS0415b` | `REAL` | fares index in real terms (DfT's own deflation) |

Geographies: London, English metropolitan areas, English non-metropolitan
areas, England, Scotland, Wales, Great Britain, England outside London.
Two measures × eight geographies = 16 series.

Series identifier: `DFT_BUS0415_{MEASURE}_{REGION}_B{BASE}`, for example
`DFT_BUS0415_CURRENT_GREATBRITAIN_B200503`.

**Frequency is quarterly, not annual.** The workbook's `Month` column takes only
Mar, Jun, Sep and Dec — verified against the live file, contradicting an earlier
registry entry. The reference date is the first day of the quarter's final
month, so the quarter ending March 2026 is stored at `2026-03-01`.

**Base is March 2005 = 100**, verified from the data itself: every column of the
2005-Mar row is exactly 100. The base is part of every identifier, so a DfT
rebasing creates new series rather than redefining stored history.

**The ONS comparators are not collected.** `BUS0415a` also publishes All-items
RPI, CPI and CPIH columns. Those are ONS target data, not DfT predictors, and
collecting them here would duplicate `collector_ons_cpi` inside a predictor
repository. They are filtered out by name and logged, and an unrecognised
column stops collection rather than being swept in.

## Limitations

Point-in-time coverage before 2023 is weak. See `POINT_IN_TIME.md`: the GOV.UK
change history for this page begins 2023-01-31, so quarters before that carry
`availability_basis = inferred` and are excluded from `get_series_as_of()` by
default. On the verified build that is 1,184 of 1,360 observations.

## Run

```bash
python -m pip install -r requirements.txt
cp .env.example .env
python main.py                          # every data set
python main.py --source-id dft_bus_fares
```

The default local database URL is documented in `.env.example`. Raw snapshots
are written below the gitignored snapshot directory configured there.
