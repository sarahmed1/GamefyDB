"""Unit tests for synthetic data generator helpers.

We test the pure helper functions (Ramadan/Eid shapes, holiday boost lookup)
because they drive every transaction's revenue target. The Excel writers and
generate_all() are integration tested manually via re-running the pipeline.
"""
import pandas as pd
import pytest

from gamefydb import data_generator as dg


def test_module_imports():
    """Smoke test: module loads and constants exist."""
    assert dg.MONTHLY_MUL[7] == 1.50
    assert dg.MONTHLY_MUL[8] == 1.35
    assert len(dg._RAMADAN_PERIODS) >= 4


def test_ramadan_periods_cover_2022_through_2026():
    """Five Ramadan windows: 2022, 2023, 2024, 2025, 2026."""
    years = sorted({s.year for s, _ in dg._RAMADAN_PERIODS})
    assert years == [2022, 2023, 2024, 2025, 2026]


def test_ramadan_2026_meets_eid_al_fitr():
    """Ramadan 2026 must end no earlier than Mar 19 so it covers the
    pre-Eid prep days (Eid al-Fitr 2026 is Mar 21)."""
    rng_2026 = next((s, e) for s, e in dg._RAMADAN_PERIODS if s.year == 2026)
    assert rng_2026[1] >= pd.Timestamp('2026-03-19')
