import pandas as pd
import pytest

from gamefydb.weather import fetch_weather, weather_multiplier


def test_weather_multiplier_clear_day():
    assert weather_multiplier(25.0, 0.0) == 1.0


def test_weather_multiplier_rain_only():
    assert weather_multiplier(25.0, 5.0) == pytest.approx(0.90)


def test_weather_multiplier_hot_only():
    assert weather_multiplier(35.0, 0.0) == pytest.approx(1.08)


def test_weather_multiplier_hot_and_rain():
    assert weather_multiplier(35.0, 5.0) == pytest.approx(0.90 * 1.08)


def test_weather_multiplier_thresholds_exclusive():
    # Boundary: precip_mm == 2 should NOT trigger the rain dampener
    assert weather_multiplier(25.0, 2.0) == 1.0
    # Boundary: temp_max_c == 33 should NOT trigger the heat boost
    assert weather_multiplier(33.0, 0.0) == 1.0


def test_fetch_weather_returns_expected_columns_and_length():
    df = fetch_weather(pd.Timestamp('2024-09-01'), pd.Timestamp('2024-09-07'))
    assert set(df.columns) >= {'ds', 'temp_max_c', 'precip_mm'}
    assert len(df) == 7
    assert df['temp_max_c'].notna().all()
    assert df['precip_mm'].notna().all()
