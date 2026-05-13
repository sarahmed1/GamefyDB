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


class TestHolidayBoost:
    def test_keys_are_3_tuples(self):
        """All keys must be (year, month, day)."""
        for k in dg._HOLIDAY_BOOST.keys():
            assert isinstance(k, tuple) and len(k) == 3
            year, month, day = k
            assert 2022 <= year <= 2026
            assert 1 <= month <= 12
            assert 1 <= day <= 31

    def test_eid_al_fitr_2024_present(self):
        """Eid al-Fitr 2024 was Apr 10 — missing in the old dict."""
        assert dg._HOLIDAY_BOOST[(2024, 4, 10)] >= 2.5

    def test_eid_al_fitr_2025_present(self):
        """Eid al-Fitr 2025 is Mar 31 per Prophet's holiday calendar."""
        assert dg._HOLIDAY_BOOST[(2025, 3, 31)] >= 2.5

    def test_eid_al_fitr_2026_present(self):
        """Eid al-Fitr 2026 is Mar 21 — critical for test-set predictions."""
        assert dg._HOLIDAY_BOOST[(2026, 3, 21)] >= 2.5

    def test_eid_al_adha_dates_present(self):
        """Eid al-Adha dates for 2022..2026."""
        expected = [(2022, 7, 9), (2023, 6, 28), (2024, 6, 17),
                    (2025, 6, 7), (2026, 5, 27)]
        for key in expected:
            assert key in dg._HOLIDAY_BOOST, f'Missing Eid al-Adha {key}'

    def test_new_year_lifted(self):
        """New Year's Day was 2.8 in the old dict; spec lifts to 3.2."""
        assert dg._HOLIDAY_BOOST[(2024, 1, 1)] >= 3.0
        assert dg._HOLIDAY_BOOST[(2026, 1, 1)] >= 3.0

    def test_christmas_lifted(self):
        """Christmas was 2.0; spec lifts to 2.5."""
        assert dg._HOLIDAY_BOOST[(2025, 12, 25)] >= 2.4

    def test_civil_holiday_repeats_every_year(self):
        """Republic Day (Jul 25) is fixed-date — present every year."""
        for year in range(2022, 2027):
            assert (year, 7, 25) in dg._HOLIDAY_BOOST


class TestEidWeekPattern:
    def test_outside_eid_window_returns_one(self):
        assert dg._eid_week_pattern(pd.Timestamp('2025-07-15')) == 1.0
        assert dg._eid_week_pattern(pd.Timestamp('2025-12-31')) == 1.0

    def test_eid_day_itself_returns_one(self):
        """Eid day boost comes from _HOLIDAY_BOOST, not from this function."""
        assert dg._eid_week_pattern(pd.Timestamp('2025-03-31')) == 1.0  # Eid al-Fitr 2025
        assert dg._eid_week_pattern(pd.Timestamp('2026-03-21')) == 1.0  # Eid al-Fitr 2026

    def test_eid_plus_1_is_80_percent_of_eid_boost(self):
        """Day after Eid al-Fitr 2026: 1.0 + (3.0 - 1.0) * 0.8 = 2.6."""
        val = dg._eid_week_pattern(pd.Timestamp('2026-03-22'))
        assert abs(val - 2.6) < 0.01

    def test_eid_plus_2_is_60_percent_of_eid_boost(self):
        val = dg._eid_week_pattern(pd.Timestamp('2026-03-23'))
        assert abs(val - 2.2) < 0.01

    def test_eid_plus_3_is_40_percent_of_eid_boost(self):
        val = dg._eid_week_pattern(pd.Timestamp('2026-03-24'))
        assert abs(val - 1.8) < 0.01

    def test_eid_plus_4_returns_one(self):
        """Window is Eid+1..Eid+3 only."""
        assert dg._eid_week_pattern(pd.Timestamp('2026-03-25')) == 1.0

    def test_eid_al_adha_window_also_works(self):
        """Eid al-Adha 2025 is Jun 7; Jun 8 should be elevated."""
        val = dg._eid_week_pattern(pd.Timestamp('2025-06-08'))
        assert val > 1.0
