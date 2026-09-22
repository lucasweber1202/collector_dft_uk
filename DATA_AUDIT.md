# Data audit — collector_dft_uk

- Audit seed: `20260918`
- Source version: live capture on 2026-09-18
- Test result: **55 passed**
- Execution: **PASS**
- Overall: **PARTIAL** — Valores, filtros e ponta validados; disponibilidade do arquivo atual é first_seen e versões anteriores exigem arquivo histórico.
- Output: 1,360 observations, 16 series, 2005-03-01 to 2026-03-01.
- Sample: 20; values matched: 20; failures: 0; not verifiable: 0.

## Observation evidence

| # | Series | Period | Collector | Official source | Unit/frequency evidence | Result |
|---:|---|---|---:|---:|---|---|
| 1 | `DFT_BUS0415_REAL_ENGLAND_B200503` | 2005-03-01 | 100.0 | 100.0 | index March 2005=100; quarterly; BUS0415b!row 10 col 6 | **PASS** |
| 2 | `DFT_BUS0415_CURRENT_GREATBRITAIN_B200503` | 2026-03-01 | 210.00187347799175 | 210.00187347799175 | index March 2005=100; quarterly; BUS0415a!row 94 col 12 | **PASS** |
| 3 | `DFT_BUS0415_REAL_GREATBRITAIN_B200503` | 2009-12-01 | 109.5 | 109.5 | index March 2005=100; quarterly; BUS0415b!row 29 col 9 | **PASS** |
| 4 | `DFT_BUS0415_REAL_ENGLAND_B200503` | 2005-06-01 | 100.5 | 100.5 | index March 2005=100; quarterly; BUS0415b!row 11 col 6 | **PASS** |
| 5 | `DFT_BUS0415_CURRENT_SCOTLAND_B200503` | 2009-12-01 | 129.1 | 129.1 | index March 2005=100; quarterly; BUS0415a!row 29 col 10 | **PASS** |
| 6 | `DFT_BUS0415_REAL_GREATBRITAIN_B200503` | 2008-06-01 | 105.2 | 105.2 | index March 2005=100; quarterly; BUS0415b!row 23 col 9 | **PASS** |
| 7 | `DFT_BUS0415_REAL_ENGLAND_B200503` | 2014-12-01 | 121.5 | 121.5 | index March 2005=100; quarterly; BUS0415b!row 49 col 6 | **PASS** |
| 8 | `DFT_BUS0415_REAL_ENGLAND_B200503` | 2018-09-01 | 123.7 | 123.7 | index March 2005=100; quarterly; BUS0415b!row 64 col 6 | **PASS** |
| 9 | `DFT_BUS0415_CURRENT_ENGLANDOUTSIDELONDON_B200503` | 2018-09-01 | 172.1 | 172.1 | index March 2005=100; quarterly; BUS0415a!row 64 col 13 | **PASS** |
| 10 | `DFT_BUS0415_CURRENT_SCOTLAND_B200503` | 2017-03-01 | 163.6 | 163.6 | index March 2005=100; quarterly; BUS0415a!row 58 col 10 | **PASS** |
| 11 | `DFT_BUS0415_REAL_ENGLISHMETROPOLITANAREAS_B200503` | 2025-12-01 | 125.5 | 125.5 | index March 2005=100; quarterly; BUS0415b!row 93 col 4 | **PASS** |
| 12 | `DFT_BUS0415_CURRENT_SCOTLAND_B200503` | 2026-03-01 | 234.6832699716523 | 234.6832699716523 | index March 2005=100; quarterly; BUS0415a!row 94 col 10 | **PASS** |
| 13 | `DFT_BUS0415_CURRENT_WALES_B200503` | 2025-12-01 | 200.9 | 200.9 | index March 2005=100; quarterly; BUS0415a!row 93 col 11 | **PASS** |
| 14 | `DFT_BUS0415_REAL_ENGLANDOUTSIDELONDON_B200503` | 2022-06-01 | 120.6 | 120.6 | index March 2005=100; quarterly; BUS0415b!row 79 col 10 | **PASS** |
| 15 | `DFT_BUS0415_REAL_WALES_B200503` | 2020-12-01 | 123.5 | 123.5 | index March 2005=100; quarterly; BUS0415b!row 73 col 8 | **PASS** |
| 16 | `DFT_BUS0415_REAL_LONDON_B200503` | 2021-03-01 | 122.7 | 122.7 | index March 2005=100; quarterly; BUS0415b!row 74 col 3 | **PASS** |
| 17 | `DFT_BUS0415_CURRENT_ENGLISHMETROPOLITANAREAS_B200503` | 2007-03-01 | 113.6 | 113.6 | index March 2005=100; quarterly; BUS0415a!row 18 col 7 | **PASS** |
| 18 | `DFT_BUS0415_CURRENT_LONDON_B200503` | 2022-12-01 | 183.3 | 183.3 | index March 2005=100; quarterly; BUS0415a!row 81 col 6 | **PASS** |
| 19 | `DFT_BUS0415_CURRENT_ENGLISHNONMETROPOLITANAREAS_B200503` | 2010-03-01 | 115.6 | 115.6 | index March 2005=100; quarterly; BUS0415a!row 30 col 8 | **PASS** |
| 20 | `DFT_BUS0415_REAL_SCOTLAND_B200503` | 2011-06-01 | 113.3 | 113.3 | index March 2005=100; quarterly; BUS0415b!row 35 col 7 | **PASS** |

## Filtering and metadata

- `{"sheet":"BUS0415a","columns":["Year","Month","All items Retail Prices Index [note 2]","All items Consumer Prices Index (CPI)","CPIH (CPI incl owner occupiers’ housing costs)","London","English metropolitan areas","English non metropolitan areas","England","Scotland","Wales","Great Britain","England outside London","Notes","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","",""],"selected":["LONDON","ENGLISHMETROPOLITANAREAS","ENGLISHNONMETROPOLITANAREAS","ENGLAND","SCOTLAND","WALES","GREATBRITAIN","ENGLANDOUTSIDELONDON"],"raw_rows":87}`
- `{"sheet":"BUS0415b","columns":["Year","Month","London","English metropolitan areas","English non metropolitan areas","England","Scotland","Wales","Great Britain","England outside London","Notes","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","","",""],"selected":["LONDON","ENGLISHMETROPOLITANAREAS","ENGLISHNONMETROPOLITANAREAS","ENGLAND","SCOTLAND","WALES","GREATBRITAIN","ENGLANDOUTSIDELONDON"],"raw_rows":86}`

The audit read the captured official artifact independently of the collector parser. It checked identifier linkage, published labels, units, frequency and first/latest boundaries. Source artifacts are identified by SHA-256 in the audit evidence.

## Point-in-time and revisions

Predictor as-of queries filter availability before ranking vintages. `inferred` and `unknown` remain excluded by default. Current mutable-file backfills are recorded at `first_seen`; later observed revisions create later vintages and do not inherit an original release timestamp. Actual pre-collection historical editions remain `NOT_VERIFIABLE` unless an archived source file exists.

## Corrections

- Mesma correção PIT para BUS0415; comparadores ONS continuam excluídos.

## Result

**PARTIAL** — Valores, filtros e ponta validados; disponibilidade do arquivo atual é first_seen e versões anteriores exigem arquivo histórico.
