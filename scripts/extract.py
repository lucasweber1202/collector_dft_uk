"""DfT extractor entrypoint: orchestrates this repository's datasets.

This module stays deliberately small. It owns no parsing and no HTTP beyond the
one shared client: each DfT data set is a self-contained ``extract_dft_*``
module returning its own ``SourceData``, and adding a data set means adding a
module and one entry to ``DATASETS``.

Datasets are collected one at a time so that a layout change at one DfT page
fails that data set alone. ``main.py`` persists each one in its own transaction
and reports the failures at the end of the run.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

import httpx

from scripts.extract_dft_bus_fares import collect as _collect_bus_fares
from scripts.govuk import SourceData, build_client

# source_id -> collector.
DATASETS: dict[str, Callable[[httpx.Client], SourceData]] = {
    "dft_bus_fares": _collect_bus_fares,
}


def resolve(source_ids: list[str] | None) -> list[str]:
    """Return the data sets to run, rejecting an unknown name loudly."""
    selected = list(DATASETS) if source_ids is None else list(source_ids)
    unknown = [source_id for source_id in selected if source_id not in DATASETS]
    if unknown:
        raise ValueError(f"Unknown DfT data set(s) {unknown}; known: {sorted(DATASETS)}")
    return selected


@contextmanager
def open_client() -> Iterator[httpx.Client]:
    """Yield the single managed HTTP client shared by one run."""
    with build_client() as client:
        yield client


def collect_one(client: httpx.Client, source_id: str) -> SourceData:
    """Collect exactly one data set with an already-open client."""
    return DATASETS[resolve([source_id])[0]](client)


def collect(source_ids: list[str] | None = None) -> list[SourceData]:
    """Collect the named data sets, or all of them, failing on the first error."""
    with open_client() as client:
        return [collect_one(client, source_id) for source_id in resolve(source_ids)]
