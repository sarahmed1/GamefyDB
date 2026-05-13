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


class TestRamadanDailyMul:
    def test_outside_ramadan_returns_one(self):
        assert dg._ramadan_daily_mul(pd.Timestamp('2025-07-15')) == 1.0
        assert dg._ramadan_daily_mul(pd.Timestamp('2026-01-01')) == 1.0

    def test_start_of_ramadan_is_near_0_85(self):
        """Ramadan 2025 starts 2025-03-01."""
        val = dg._ramadan_daily_mul(pd.Timestamp('2025-03-01'))
        assert 0.84 <= val <= 0.86

    def test_end_of_ramadan_is_near_1_5(self):
        """Last day of Ramadan should hit the peak ramp value (1.5)."""
        val = dg._ramadan_daily_mul(pd.Timestamp('2025-03-29'))
        assert 1.45 <= val <= 1.5

    def test_mid_ramadan_is_intermediate(self):
        """Around the 50% mark should be between 0.85 and 1.5."""
        val = dg._ramadan_daily_mul(pd.Timestamp('2025-03-15'))
        assert 0.9 < val < 1.3

    def test_ramp_is_monotonic_in_2025(self):
        """Multiplier should be non-decreasing across Ramadan 2025."""
        dates = pd.date_range('2025-03-01', '2025-03-29')
        vals = [dg._ramadan_daily_mul(d) for d in dates]
        assert vals == sorted(vals)
