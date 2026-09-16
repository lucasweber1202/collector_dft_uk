"""DfT BUS0415 parsing, comparator exclusion, release filtering and gates."""

from __future__ import annotations

import io
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

import pytest
from odf.opendocument import OpenDocumentSpreadsheet
from odf.table import Table, TableCell, TableRow
from odf.text import P

from scripts.extract_dft_bus_fares import (
    BASE_PERIOD,
    EXPECTED_FIRST_OBSERVATION,
    MIN_EXPECTED_DATES,
    REGIONS,
    SHEETS,
    _build_catalog,
    _classify_columns,
    fares_release_timestamps,
    make_series_id,
    parse_ods,
    parse_series_id,
    validate,
)
from scripts.metadata import validate_catalog
from scripts.time_series import Observation

# As published: comparator columns first, then the eight geographies, then Notes.
COMPARATORS = (
    "All items Retail Prices Index [note 2]",
    "All items Consumer Prices Index (CPI)",
    "CPIH (CPI incl owneroccupiers’ housing costs)",
)
GEOGRAPHIES = (
    "London",
    "English metropolitan areas",
    "English non metropolitan areas",
    "England",
    "Scotland",
    "Wales",
    "Great Britain",
    "England outside London",
)
HEADER_A = ("Year", "Month", *COMPARATORS, *GEOGRAPHIES, "Notes")
HEADER_B = ("Year", "Month", *GEOGRAPHIES, "Notes")
QUARTERS = ("Mar", "Jun", "Sep", "Dec")


def _cell(text: str) -> TableCell:
    cell = TableCell()
    cell.addElement(P(text=text))
    return cell


def _sheet(
    table: Table, header: tuple[str, ...], rows: Sequence[tuple[str, str, tuple[str, ...]]]
) -> None:
    title = TableRow()
    title.addElement(_cell("Local bus fares index"))
    table.addElement(title)
    base = TableRow()
    base.addElement(_cell("March 2005 = 100"))
    table.addElement(base)
    head = TableRow()
    for label in header:
        head.addElement(_cell(label))
    table.addElement(head)
    for year, month, values in rows:
        row = TableRow()
        row.addElement(_cell(year))
        row.addElement(_cell(month))
        for value in values:
            row.addElement(_cell(value))
        row.addElement(_cell("[z]"))
        table.addElement(row)


def _ods(
    rows: Sequence[tuple[str, str, tuple[str, ...]]] | None = None,
    *,
    header_a: tuple[str, ...] = HEADER_A,
    header_b: tuple[str, ...] = HEADER_B,
    sheet_names: tuple[str, str] = ("BUS0415a", "BUS0415b"),
) -> bytes:
    """Render a minimal workbook shaped like the published one."""
    rows = rows or [("2005", "Mar", ("100",) * 8)]
    document = OpenDocumentSpreadsheet()
    a = Table(name=sheet_names[0])
    _sheet(a, header_a, [(y, m, ("100", "100", "100", *v)) for y, m, v in rows])
    document.spreadsheet.addElement(a)
    b = Table(name=sheet_names[1])
    _sheet(b, header_b, rows)
    document.spreadsheet.addElement(b)
    buffer = io.BytesIO()
    document.write(buffer)
    return buffer.getvalue()


def _quarter(index: int) -> date:
    """Return the quarter-end month ``index`` quarters after the history start."""
    total = (EXPECTED_FIRST_OBSERVATION.month - 1) + 3 * index
    return date(EXPECTED_FIRST_OBSERVATION.year + total // 12, total % 12 + 1, 1)


def _panel(dates: int = MIN_EXPECTED_DATES) -> tuple[list[Observation], dict[str, dict[str, str]]]:
    """Build a synthetic panel that clears every validation floor."""
    observations: list[Observation] = []
    natives: dict[str, dict[str, str]] = {}
    for sheet, measure in SHEETS.items():
        for region in REGIONS:
            series_id = make_series_id(measure, region)
            natives[series_id] = {"measure": measure, "region": region, "sheet": sheet}
            for step in range(dates):
                observations.append(
                    Observation(
                        series_id=series_id,
                        reference_date=_quarter(step),
                        value=150.0,
                        snapshot_id="snapshot",
                    )
                )
    return observations, natives


def test_parses_both_sheets_into_sixteen_series() -> None:
    observations, natives = parse_ods(_ods(), "test://dft", "snap")
    assert len(natives) == len(SHEETS) * len(REGIONS) == 16
    assert len(observations) == 16
    assert {o.reference_date for o in observations} == {date(2005, 3, 1)}
    assert all(o.snapshot_id == "snap" for o in observations)


def test_the_ons_comparators_are_not_collected() -> None:
    """RPI, CPI and CPIH are ONS target data, not DfT predictors."""
    _observations, natives = parse_ods(_ods(), "test://dft", "snap")
    joined = " ".join(natives)
    for banned in ("RETAIL", "CONSUMER", "CPIH", "RPI"):
        assert banned not in joined


def test_comparator_columns_are_classified_out_not_treated_as_regions() -> None:
    collected = _classify_columns(list(HEADER_A), "BUS0415a")
    assert sorted(collected.values()) == sorted(REGIONS)


def test_an_unrecognised_column_is_reported_not_silently_dropped() -> None:
    header = (*HEADER_A[:-1], "Northern Ireland", "Notes")
    with pytest.raises(ValueError, match="unrecognised column"):
        _classify_columns(list(header), "BUS0415a")


def test_a_disappearing_geography_fails_loudly() -> None:
    header = tuple(label for label in HEADER_B if label != "Wales")
    with pytest.raises(ValueError, match="missing published geographies"):
        _classify_columns(list(header), "BUS0415b")


def test_a_missing_sheet_fails_loudly() -> None:
    with pytest.raises(ValueError, match="missing sheet"):
        parse_ods(_ods(sheet_names=("BUS0415a", "BUS0415z")), "test://dft", "snap")


def test_the_quarter_end_month_becomes_the_reference_date() -> None:
    rows = [("2026", month, ("100",) * 8) for month in QUARTERS]
    observations, _natives = parse_ods(_ods(rows), "test://dft", "snap")
    assert {o.reference_date for o in observations} == {
        date(2026, 3, 1),
        date(2026, 6, 1),
        date(2026, 9, 1),
        date(2026, 12, 1),
    }


def test_a_non_quarter_month_fails_loudly() -> None:
    with pytest.raises(ValueError, match="publishes month"):
        parse_ods(_ods([("2026", "Jan", ("100",) * 8)]), "test://dft", "snap")


def test_a_suppressed_cell_is_not_a_zero() -> None:
    observations, _natives = parse_ods(
        _ods([("2005", "Mar", ("100", "[z]", "100", "100", "100", "100", "100", "100"))]),
        "test://dft",
        "snap",
    )
    # 8 geographies minus the suppressed one, across both sheets.
    assert len(observations) == 14
    assert all(o.value == 100.0 for o in observations)


def test_an_unparseable_value_fails_loudly() -> None:
    with pytest.raises(ValueError, match="unparseable value"):
        parse_ods(
            _ods([("2005", "Mar", ("abc", "100", "100", "100", "100", "100", "100", "100"))]),
            "test://dft",
            "snap",
        )


# --- release attribution -------------------------------------------------

_HISTORY = """
<time class="app-c-published-dates__change-date" datetime="2026-06-18T08:30:03Z"></time>
<p>Quarterly bus fares statistics: January to March 2026 data tables published.</p>
<time class="app-c-published-dates__change-date" datetime="2026-03-24T09:30:04Z"></time>
<p>Tables BUS01 to BUS08 have been revised.</p>
<time class="app-c-published-dates__change-date" datetime="2025-06-19T08:30:00Z"></time>
<p>BUS0415 updated for January to March 2025.</p>
<time class="app-c-published-dates__change-date" datetime="2023-04-26T08:30:06Z"></time>
<p>Concessionary travel data tables for the latest financial year updated and added.</p>
"""


def test_only_fares_releases_count_as_a_release() -> None:
    """A concessionary-travel update never published a fares quarter."""
    stamps = [stamp.date() for stamp in fares_release_timestamps(_HISTORY)]
    assert stamps == [date(2025, 6, 19), date(2026, 6, 18)]


def test_an_unrelated_bus_table_update_is_not_a_fares_release() -> None:
    stamps = [stamp.date() for stamp in fares_release_timestamps(_HISTORY)]
    assert date(2026, 3, 24) not in stamps
    assert date(2023, 4, 26) not in stamps


def test_a_history_with_no_fares_entry_yields_nothing() -> None:
    history = (
        '<time class="change-date" datetime="2023-04-26T08:30:06Z"></time>'
        "<p>Concessionary travel data tables updated.</p>"
    )
    assert fares_release_timestamps(history) == []


# --- identifiers ---------------------------------------------------------


def test_series_ids_round_trip() -> None:
    for measure in SHEETS.values():
        for region in REGIONS:
            series_id = make_series_id(measure, region)
            _source, _dataset, parsed_measure, parsed_region, base = parse_series_id(series_id)
            assert make_series_id(parsed_measure, parsed_region) == series_id
            assert base == BASE_PERIOD


def test_the_base_period_is_part_of_the_identifier() -> None:
    """A DfT rebasing must create new series, never redefine stored ones."""
    assert make_series_id("CURRENT", "LONDON").endswith(f"_B{BASE_PERIOD}")
    assert make_series_id("CURRENT", "LONDON", "202001") != make_series_id("CURRENT", "LONDON")


def test_current_and_real_of_the_same_region_are_distinct_series() -> None:
    assert make_series_id("CURRENT", "LONDON") != make_series_id("REAL", "LONDON")


@pytest.mark.parametrize(
    "series_id",
    [
        "DFT_BUS0415_CURRENT_LONDON",
        "DFT_BUS0415_NOMINAL_LONDON_B200503",
        "DFT_BUS0415_CURRENT_NORTHERNIRELAND_B200503",
        "DFT_BUS04_CURRENT_LONDON_B200503",
    ],
)
def test_a_malformed_series_id_is_refused(series_id: str) -> None:
    with pytest.raises(ValueError):
        parse_series_id(series_id)


# --- validation gates ----------------------------------------------------


def test_validation_accepts_a_well_formed_panel() -> None:
    validate(*_panel())


def test_too_few_series_is_refused() -> None:
    observations, natives = _panel()
    kept = {sid for sid, f in natives.items() if f["region"] == "LONDON"}
    with pytest.raises(ValueError, match="below the .* floor"):
        validate(
            [o for o in observations if o.series_id in kept],
            {sid: f for sid, f in natives.items() if sid in kept},
        )


def test_losing_a_whole_measure_is_refused() -> None:
    observations, natives = _panel()
    kept = {sid for sid, f in natives.items() if f["measure"] == "CURRENT"}
    trimmed = {sid: f for sid, f in natives.items() if sid in kept}
    # Pad the survivors so the series floor is not what trips first.
    with pytest.raises(ValueError, match="returned measures|below the .* floor"):
        validate([o for o in observations if o.series_id in kept], trimmed)


def test_too_few_quarters_is_refused() -> None:
    observations, natives = _panel(dates=MIN_EXPECTED_DATES - 1)
    with pytest.raises(ValueError, match="reference quarters, below"):
        validate(observations, natives)


def test_a_shifted_first_observation_is_refused() -> None:
    observations, natives = _panel(dates=MIN_EXPECTED_DATES + 1)
    shifted = [o for o in observations if o.reference_date != EXPECTED_FIRST_OBSERVATION]
    with pytest.raises(ValueError, match="history starts at"):
        validate(shifted, natives)


def test_a_quarterly_cadence_gap_is_refused() -> None:
    observations, natives = _panel(dates=MIN_EXPECTED_DATES + 2)
    gapped = [o for o in observations if o.reference_date not in {_quarter(1), _quarter(2)}]
    with pytest.raises(ValueError, match="cadence broken by gaps"):
        validate(gapped, natives)


def test_a_duplicate_observation_is_refused() -> None:
    observations, natives = _panel()
    with pytest.raises(ValueError, match="duplicate observations"):
        validate([*observations, observations[0]], natives)


def test_a_future_reference_date_is_refused() -> None:
    observations, natives = _panel()
    future = Observation(
        series_id=observations[0].series_id,
        reference_date=datetime.now(UTC).date().replace(day=1) + timedelta(days=400),
        value=150.0,
        snapshot_id="snapshot",
    )
    with pytest.raises(ValueError, match="future reference date"):
        validate([*observations, future], natives)


@pytest.mark.parametrize("value", [0.0, 5.0, 5000.0])
def test_an_implausible_index_is_refused(value: float) -> None:
    observations, natives = _panel()
    broken = Observation(
        series_id=observations[0].series_id,
        reference_date=observations[0].reference_date,
        value=value,
        snapshot_id="snapshot",
    )
    with pytest.raises(ValueError, match="plausible"):
        validate([broken, *observations[1:]], natives)


def test_an_empty_panel_is_refused() -> None:
    with pytest.raises(ValueError, match="no observations"):
        validate([], {})


def test_the_catalog_satisfies_the_metadata_vocabularies() -> None:
    _observations, natives = parse_ods(_ods(), "test://dft", "snap")
    catalog = _build_catalog(natives, date(2026, 6, 18))
    validate_catalog(catalog)
    current = catalog[make_series_id("CURRENT", "GREATBRITAIN")]
    real = catalog[make_series_id("REAL", "GREATBRITAIN")]
    assert current["frequency"] == "quarterly"
    assert current["unit"] == "index"
    assert "March 2005 = 100" in current["name"]
    # The real-terms deflation is DfT's, and the catalog must say so.
    assert "Department's own" in real["description"]
    assert "Department's own" not in current["description"]
