# Standalone portability

Verified 2026-09-16. No fleet sibling is required. The ODS parser dependency is
declared locally.

```powershell
git clone https://github.com/lucasweber1202/collector_dft_uk.git
Set-Location collector_dft_uk
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python -m pytest -q
ruff check .
mypy .
python main.py --source-id dft_bus_fares
```

Python 3.11/3.12. Local collection requires `COLLECTOR_DB_URL`; Databricks is
optional. Network: HTTPS to `www.gov.uk` and official attachment hosts. Raw
artifacts write below `COLLECTOR_RAW_DIR`. TLS verification remains enabled.

Certification: standalone code PASS; sibling required NO; database and internet
required for collection; Databricks not required.
