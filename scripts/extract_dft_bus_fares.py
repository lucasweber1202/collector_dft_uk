"""DfT BUS0415: quarterly local bus fares index by area status and country.

Official page:
https://www.gov.uk/government/statistical-data-sets/bus-statistics-data-tables

DfT publishes the local bus fares index as a single ODS workbook, `bus0415.ods`,
with two data sheets carrying the same eight geographies:

``BUS0415a``
    Fares index at current prices.
``BUS0415b``
    Fares index in real terms. DfT deflates this itself, so it is a published
    series rather than a transformation performed here.

Both are stored, distinguished by the ``CURRENT`` / ``REAL`` measure token.

Frequency
---------
Quarterly, not annual. The workbook carries ``Year`` and ``Month`` columns whose
month values are only Mar, Jun, Sep and Dec — verified against the live file,
which contradicts an earlier registry entry describing this table as annual.
The reference date is the first day of the quarter's final month, so the
quarter ending March 2026 is stored at 2026-03-01.

Base period
-----------
March 2005 = 100, verified against the live file: every column of the 2005-Mar
row is exactly 100. The base is part of every identifier (``..._B200503``), so a
DfT rebasing produces new series rather than silently redefining stored ones.

ONS comparators are not collected
---------------------------------
``BUS0415a`` also carries All-items RPI, CPI and CPIH columns. Those are ONS
target data, not DfT predictors, and collecting them here would duplicate
`collector_ons_cpi` inside a predictor repository. They are filtered out
explicitly — by name, and loudly — rather than silently skipped, so a new
comparator column appearing upstream is reported instead of being swept in.
"""

from __future__ import annotations

import html
import io
import logging
import re
from datetime import UTC, date, datetime
from itertools import pairwise
from typing import Any

import httpx
from odf import teletype
from odf.opendocument import load
from odf.table import CoveredTableCell, Table, TableCell, TableRow

from scripts.govuk import SourceData, download, fetch_page, find_attachment
from scripts.snapshots import build_snapshot
from scripts.time_series import Observation

logger = logging.getLogger(__name__)

SOURCE_ID = "dft_bus_fares"
PAGE_URL = "https://www.gov.uk/government/statistical-data-sets/bus-statistics-data-tables"

# The fares workbook specifically. The same page carries `bus04i.ods` and
# `bus04ii.ods`, which are different tables, so the pattern is anchored on the
# full table number.
ODS_PATTERN = r"/bus0415[^/]*\.ods"

# sheet name -> measure token. Verified against the live workbook on 2026-09-16.
SHEETS: dict[str, str] = {"BUS0415a": "CURRENT", "BUS0415b": "REAL"}

# The base period every published column is indexed to, verified from the data.
BASE_PERIOD = "200503"

# The eight published geographies, as the fleet identifier token -> the native
# label used in the catalog. Matching is done on the normalised token, so a
# cosmetic relabelling ("non metropolitan" -> "non-metropolitan") does not break
# collection, while a genuine new geography does.
REGIONS: dict[str, str] = {
    "LONDON": "London",
    "ENGLISHMETROPOLITANAREAS": "English metropolitan areas",
    "ENGLISHNONMETROPOLITANAREAS": "English non-metropolitan areas",
    "ENGLAND": "England",
    "SCOTLAND": "Scotland",
    "WALES": "Wales",
    "GREATBRITAIN": "Great Britain",
    "ENGLANDOUTSIDELONDON": "England outside London",
}

# Columns that are ONS target data rather than DfT predictors. Detected by
# keyword because the published labels carry note markers and punctuation.
COMPARATOR_PATTERNS = (
    re.compile(r"retail\s*prices\s*index", re.IGNORECASE),
    re.compile(r"consumer\s*prices\s*index", re.IGNORECASE),
    re.compile(r"\bcpih\b", re.IGNORECASE),
)

# Structural columns that carry no observation.
STRUCTURAL_HEADERS = frozenset({"year", "month", "notes"})

QUARTER_MONTHS = {"mar": 3, "jun": 6, "sep": 9, "dec": 12}

# Only a change-history entry that actually describes a fares release counts as
# a release for this data set. The page is a collection covering every BUS
# table, so attributing a fares quarter to (say) a concessionary-travel update
# would claim the figure was published before it was. Verified against the live
# history: the fares entries name BUS0415, "bus fares statistics" or "bus fares
# index", while the annual-bus, concessionary-travel, financial and BUS01-BUS08
# entries do not.
FARES_RELEASE_PATTERN = re.compile(r"bus\s*0415|bus\s+fares", re.IGNORECASE)
_CHANGE_ENTRY_PATTERN = re.compile(
    r'<time[^>]*class="[^"]*change-date[^"]*"[^>]*datetime="([^"]+)"', re.IGNORECASE
)

# Observed fares-release schedule, measured over the eleven fares entries the
# change history covers: the quarter ending in month M is published 86 to 121
# days after the first of M (for example the quarter ending March 2026 on
# 2026-06-18, and the quarter ending September 2025 on 2025-11-26).
MIN_LAG_DAYS = 70
MAX_LAG_DAYS = 140
INFERRED_LAG_DAYS = 110

EXPECTED_FIRST_OBSERVATION = date(2005, 3, 1)
MIN_EXPECTED_SERIES = 16
MIN_EXPECTED_DATES = 80
# Quarterly cadence: consecutive published quarters are about three months
# apart, never more than a third of a year.
MAX_GAP_DAYS = 100

# Plausibility envelope for an index on a March 2005 = 100 base. Wide on
# purpose: a guard against a rebasing or a decimal shift, not a forecast.
MIN_PLAUSIBLE_INDEX = 10.0
MAX_PLAUSIBLE_INDEX = 1000.0

MISSING_VALUES = frozenset({"", "[z]", "[x]", "[c]", "[w]", ":", "-", "..", "n/a", "na"})
MAX_COLUMNS = 40
_CELL_QNAMES = frozenset({TableCell().qname, CoveredTableCell().qname})
_NOTE_MARKER = re.compile(r"\[[^\]]*\]")


def _token(raw: str) -> str:
    """Normalize one native label into an uppercase identifier token."""
    token = re.sub(r"[^A-Z0-9]+", "", raw.strip().upper())
    if not token:
        raise ValueError(f"DfT label {raw!r} normalizes to an empty identifier token")
    return token


def make_series_id(measure: str, region_token: str, base_period: str = BASE_PERIOD) -> str:
    """Build ``DFT_BUS0415_{MEASURE}_{REGION}_B{BASE}`` from verified parts."""
    series_id = f"DFT_BUS0415_{measure}_{region_token}_B{base_period}"
    if len(series_id) > 200:
        raise ValueError(f"series_id exceeds 200 characters: {series_id}")
    return series_id


def describe_series_id(series_id: str) -> tuple[str, str, str, str, str]:
    """Decode ``DFT_BUS0415_{MEASURE}_{REGION}_B{BASE}`` into its five parts."""
    parts = series_id.split("_")
    if len(parts) != 5 or parts[0] != "DFT" or parts[1] != "BUS0415":
        raise ValueError(f"Invalid DfT bus fares series_id: {series_id}")
    source, dataset, measure, region, base = parts
    if measure not in set(SHEETS.values()):
        raise ValueError(f"Unknown measure in DfT bus fares series_id: {series_id}")
    if region not in REGIONS:
        raise ValueError(f"Unknown region in DfT bus fares series_id: {series_id}")
    if not re.fullmatch(r"B\d{6}", base):
        raise ValueError(f"DfT bus fares series_id carries no base period: {series_id}")
    return source, dataset, measure, region, base[1:]


def parse_series_id(series_id: str) -> tuple[str, ...]:
    """Split a canonical id into its raw underscore components.

    This is the fleet contract (GUIDELINES.md 4): uppercase, underscore
    separated, ordered coarse -> fine, and exactly reversible, so
    build_series_id(*parse_series_id(sid)) == sid. The decoded view -- which
    strips the base-period marker and types the numeric parts -- is
    describe_series_id, which validates the same grammar.
    """
    describe_series_id(series_id)
    return tuple(series_id.split("_"))


def _normalise_header(raw: str) -> str:
    """Strip DfT note markers and collapse whitespace in a header label."""
    return re.sub(r"\s+", " ", _NOTE_MARKER.sub("", raw)).strip()


def fares_release_timestamps(page_html: str) -> list[datetime]:
    """Return only the change-history entries that describe a fares release.

    The page is a collection covering every BUS table. Using its full change
    history would attribute a fares quarter to an unrelated update and claim
    the figure was knowable earlier than it was, which is a look-ahead. Only
    entries naming BUS0415 or bus fares are treated as releases for this data
    set; everything else is ignored, which can only push availability later.
    """
    stamps: set[datetime] = set()
    parts = _CHANGE_ENTRY_PATTERN.split(page_html)
    for index in range(1, len(parts), 2):
        raw_stamp, body = parts[index], parts[index + 1]
        text = html.unescape(re.sub(r"<[^>]+>", " ", body[:600]))
        if not FARES_RELEASE_PATTERN.search(text):
            continue
        try:
            parsed = datetime.fromisoformat(raw_stamp)
        except ValueError:
            logger.warning("Unparseable DfT change-history timestamp %r; skipping", raw_stamp)
            continue
        stamps.add(parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC))
    return sorted(stamps)


def _cell_values(row: TableRow) -> list[str]:
    """Expand one ODS row into a flat list of cell strings, honouring repeats."""
    expanded: list[str] = []
    for cell in row.childNodes:
        if cell.qname not in _CELL_QNAMES:
            continue
        repeat = int(cell.getAttribute("numbercolumnsrepeated") or 1)
        value = cell.getAttribute("value")
        text = value if value is not None else teletype.extractText(cell).strip()
        if repeat > MAX_COLUMNS:
            repeat = 1
        remaining = MAX_COLUMNS - len(expanded)
        if remaining <= 0:
            break
        expanded.extend([text] * min(repeat, remaining))
    return expanded


def _classify_columns(header: list[str], sheet: str) -> dict[int, str]:
    """Map each data column index to its region token, refusing the unexpected.

    Returns only the columns this collector stores. A comparator column is
    dropped by name; anything neither structural, comparator nor a known region
    stops collection, because a silently ignored column is how a published
    geography goes missing without anything failing.
    """
    collected: dict[int, str] = {}
    for index, raw in enumerate(header):
        label = _normalise_header(raw)
        if not label:
            continue
        if label.lower() in STRUCTURAL_HEADERS:
            continue
        if any(pattern.search(label) for pattern in COMPARATOR_PATTERNS):
            # ONS target data, deliberately out of scope for this repository.
            logger.info("%s: not collecting ONS comparator column %r", sheet, label)
            continue
        token = _token(label)
        if token not in REGIONS:
            raise ValueError(
                f"DfT sheet {sheet} publishes unrecognised column {label!r}; it is neither a "
                f"known geography {sorted(REGIONS)} nor a known ONS comparator. The published "
                "layout changed and must be re-verified against the official source."
            )
        if token in collected.values():
            raise ValueError(f"DfT sheet {sheet} publishes geography {label!r} twice")
        collected[index] = token
    missing = set(REGIONS) - set(collected.values())
    if missing:
        raise ValueError(
            f"DfT sheet {sheet} is missing published geographies {sorted(missing)}; a dimension "
            "disappeared and must be re-verified against the official source"
        )
    return collected


def _reference_date(year_cell: str, month_cell: str, sheet: str) -> date:
    """Turn the Year and Month columns into the quarter's final-month date."""
    month = QUARTER_MONTHS.get(month_cell.strip()[:3].lower())
    if month is None:
        raise ValueError(
            f"DfT sheet {sheet} publishes month {month_cell!r}, expected one of "
            f"{sorted(QUARTER_MONTHS)}; the published quarterly cadence changed"
        )
    return date(int(float(year_cell)), month, 1)


def parse_ods(
    body: bytes, url: str, snapshot_id: str
) -> tuple[list[Observation], dict[str, dict[str, str]]]:
    """Parse both published sheets into observations and their native labels."""
    document = load(io.BytesIO(body))
    tables = {str(table.getAttribute("name")): table for table in document.getElementsByType(Table)}
    missing_sheets = set(SHEETS) - set(tables)
    if missing_sheets:
        raise ValueError(
            f"DfT workbook {url} is missing sheet(s) {sorted(missing_sheets)}; found "
            f"{sorted(tables)}. The published layout changed and must be re-verified."
        )

    observations: list[Observation] = []
    natives: dict[str, dict[str, str]] = {}
    for sheet, measure in SHEETS.items():
        rows = [_cell_values(row) for row in tables[sheet].getElementsByType(TableRow)]
        header_index = next(
            (i for i, row in enumerate(rows) if row and row[0].strip().lower() == "year"), None
        )
        if header_index is None:
            raise ValueError(
                f"DfT workbook {url} sheet {sheet} has no 'Year' header row; the published "
                "layout changed"
            )
        columns = _classify_columns(rows[header_index], sheet)

        for row in rows[header_index + 1 :]:
            if len(row) < 2 or not row[0].strip()[:4].isdigit():
                # Footnote and blank rows trail the data block.
                continue
            reference_date = _reference_date(row[0], row[1], sheet)
            for index, region_token in columns.items():
                if index >= len(row):
                    continue
                raw = row[index].strip()
                if raw.lower() in MISSING_VALUES:
                    continue
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise ValueError(
                        f"DfT workbook {url} sheet {sheet} has unparseable value {raw!r} for "
                        f"{region_token} at {reference_date}"
                    ) from exc
                series_id = make_series_id(measure, region_token)
                natives.setdefault(
                    series_id, {"measure": measure, "region": region_token, "sheet": sheet}
                )
                observations.append(
                    Observation(
                        series_id=series_id,
                        reference_date=reference_date,
                        value=value,
                        snapshot_id=snapshot_id,
                    )
                )
    return observations, natives


def _build_catalog(
    natives: dict[str, dict[str, str]], last_publish_date: date | None
) -> dict[str, dict[str, Any]]:
    """Describe every collected series from its verified native labels."""
    catalog: dict[str, dict[str, Any]] = {}
    for series_id, fields in natives.items():
        region = REGIONS[fields["region"]]
        current = fields["measure"] == "CURRENT"
        basis = "at current prices" if current else "in real terms"
        catalog[series_id] = {
            "source_id": SOURCE_ID,
            "name": f"Local bus fares index {basis}, {region} (March 2005 = 100)",
            "description": (
                f"Quarterly local bus fares index for {region}, {basis}, on a March 2005 = 100 "
                "base, as published by the Department for Transport in table "
                f"{fields['sheet']}. Stored exactly as published at the final month of each "
                "quarter, with no derived transformation. "
                + (
                    "The real-terms deflation is the Department's own, not a calculation "
                    "performed here. "
                    if not current
                    else ""
                )
                + "The All-items RPI, CPI and CPIH columns published alongside this table are "
                "ONS target data and are deliberately not collected in this repository."
            ),
            "frequency": "quarterly",
            "unit": "index",
            "eco_group": "consumer_prices",
            "source_url": PAGE_URL,
            "last_publish_date": last_publish_date,
        }
    return catalog


def validate(observations: list[Observation], natives: dict[str, dict[str, str]]) -> None:
    """Gate the parsed panel before anything reaches the database."""
    if not observations:
        raise ValueError("DfT bus fares collection produced no observations")
    if len(natives) < MIN_EXPECTED_SERIES:
        raise ValueError(
            f"DfT bus fares returned only {len(natives)} series, below the "
            f"{MIN_EXPECTED_SERIES} floor; a sheet or a geography is missing"
        )

    # Both published measures must survive, or half the panel could vanish
    # without anything else failing.
    present = {fields["measure"] for fields in natives.values()}
    if present != set(SHEETS.values()):
        raise ValueError(
            f"DfT bus fares returned measures {sorted(present)}, expected "
            f"{sorted(set(SHEETS.values()))}"
        )

    keys = [(observation.series_id, observation.reference_date) for observation in observations]
    if len(keys) != len(set(keys)):
        counts: dict[tuple[str, date], int] = {}
        for key in keys:
            counts[key] = counts.get(key, 0) + 1
        duplicates = sorted(key for key, count in counts.items() if count > 1)[:5]
        raise ValueError(
            f"DfT bus fares published duplicate observations, for example {duplicates}"
        )

    dates = sorted({observation.reference_date for observation in observations})
    if dates[0] != EXPECTED_FIRST_OBSERVATION:
        raise ValueError(
            f"DfT bus fares history starts at {dates[0]}, expected "
            f"{EXPECTED_FIRST_OBSERVATION}; the published file changed — check for a rebasing — "
            "and must be re-verified"
        )
    if len(dates) < MIN_EXPECTED_DATES:
        raise ValueError(
            f"DfT bus fares returned only {len(dates)} reference quarters, below the "
            f"{MIN_EXPECTED_DATES} floor; the download was probably truncated"
        )
    if dates[-1] > datetime.now(UTC).date():
        raise ValueError(f"DfT bus fares published a future reference date {dates[-1]}")

    off_quarter = [day for day in dates if day.month not in set(QUARTER_MONTHS.values())]
    if off_quarter:
        raise ValueError(
            f"DfT bus fares published non-quarter reference dates {off_quarter[:5]}; the "
            "published cadence changed"
        )

    long_gaps = [
        (earlier, later)
        for earlier, later in pairwise(dates)
        if (later - earlier).days > MAX_GAP_DAYS
    ]
    if long_gaps:
        raise ValueError(
            f"DfT bus fares quarterly cadence broken by gaps longer than {MAX_GAP_DAYS} days at "
            f"{long_gaps[:5]}"
        )

    implausible = [
        (observation.series_id, observation.reference_date, observation.value)
        for observation in observations
        if not MIN_PLAUSIBLE_INDEX <= observation.value <= MAX_PLAUSIBLE_INDEX
    ]
    if implausible:
        raise ValueError(
            f"DfT bus fares published index values outside the plausible "
            f"[{MIN_PLAUSIBLE_INDEX}, {MAX_PLAUSIBLE_INDEX}] envelope, for example "
            f"{implausible[:5]}; check for an unannounced rebasing at source"
        )

    logger.info(
        "DfT bus fares validation passed: %d series, %d reference quarters, %s to %s",
        len(natives),
        len(dates),
        dates[0],
        dates[-1],
    )


def collect(client: httpx.Client) -> SourceData:
    """Download, parse and validate the full DfT bus fares index history."""
    page = fetch_page(client, PAGE_URL)
    releases = fares_release_timestamps(page)
    if not releases:
        raise ValueError(
            f"No bus fares release found in the change history of {PAGE_URL}; the page layout "
            "or its wording changed and release attribution must be re-verified"
        )
    last_publish_date = releases[-1].astimezone(UTC).date()
    logger.info(
        "DfT page carries %d fares release timestamps, %s to %s",
        len(releases),
        releases[0].astimezone(UTC).date(),
        last_publish_date,
    )

    ods_url = find_attachment(page, PAGE_URL, ODS_PATTERN)
    ods_body, ods_digest, ods_etag, ods_last_modified = download(client, ods_url)
    ods_snapshot = build_snapshot(
        source_id=SOURCE_ID,
        source_url=ods_url,
        filename=ods_url.rsplit("/", 1)[-1],
        body=ods_body,
        digest=ods_digest,
        etag=ods_etag,
        last_modified=ods_last_modified,
        fetched_at=datetime.now(UTC),
        source_published_date=last_publish_date,
    )
    observations, natives = parse_ods(ods_body, ods_url, ods_digest)
    validate(observations, natives)
    return SourceData(
        source_id=SOURCE_ID,
        source_url=PAGE_URL,
        catalog=_build_catalog(natives, last_publish_date),
        observations=observations,
        releases=releases,
        snapshots=[ods_snapshot],
        min_lag_days=MIN_LAG_DAYS,
        max_lag_days=MAX_LAG_DAYS,
        inferred_lag_days=INFERRED_LAG_DAYS,
        last_publish_date=last_publish_date,
    )
