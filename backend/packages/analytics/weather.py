"""Daily weather for Tunis from Open-Meteo. Cached locally so repeated runs hit the API zero times."""

from pathlib import Path
import pandas as pd
import requests

TUNIS_LAT = 36.8065
TUNIS_LON = 10.1815
ARCHIVE_URL = 'https://archive-api.open-meteo.com/v1/archive'
CACHE_PATH = Path('data') / 'excel' / 'weather_tunis.parquet'


def _load_cache() -> pd.DataFrame:
    if CACHE_PATH.exists():
        df = pd.read_parquet(CACHE_PATH)
        df['ds'] = pd.to_datetime(df['ds'])
        return df.sort_values('ds').reset_index(drop=True)
    return pd.DataFrame(columns=['ds', 'temp_max_c', 'precip_mm'])


def _save_cache(df: pd.DataFrame) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.sort_values('ds').reset_index(drop=True).to_parquet(CACHE_PATH, index=False)


def _fetch_range(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    params = {
        'latitude': TUNIS_LAT, 'longitude': TUNIS_LON,
        'start_date': start.strftime('%Y-%m-%d'),
        'end_date':   end.strftime('%Y-%m-%d'),
        'daily': 'temperature_2m_max,precipitation_sum',
        'timezone': 'Africa/Tunis',
    }
    r = requests.get(ARCHIVE_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()['daily']
    return pd.DataFrame({
        'ds':         pd.to_datetime(data['time']),
        'temp_max_c': data['temperature_2m_max'],
        'precip_mm':  data['precipitation_sum'],
    })


def _climatology(cache: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.DataFrame:
    """Return mean temp/precip by (month, day) for dates beyond available data."""
    out = pd.DataFrame({'ds': dates})
    if cache.empty:
        out['temp_max_c'] = 20.0
        out['precip_mm']  = 0.0
        return out[['ds', 'temp_max_c', 'precip_mm']]
    src = cache.copy()
    src['_mo'] = src['ds'].dt.month
    src['_dy'] = src['ds'].dt.day
    clim = src.groupby(['_mo', '_dy'])[['temp_max_c', 'precip_mm']].mean().reset_index()
    out['_mo'] = out['ds'].dt.month
    out['_dy'] = out['ds'].dt.day
    out = out.merge(clim, on=['_mo', '_dy'], how='left')
    out['temp_max_c'] = out['temp_max_c'].fillna(20.0)
    out['precip_mm']  = out['precip_mm'].fillna(0.0)
    return out[['ds', 'temp_max_c', 'precip_mm']]


def fetch_weather(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Return daily Tunis weather for [start, end] inclusive.

    Strategy:
      1. Load cache.
      2. For dates <= today not in cache, fetch from the Archive API.
      3. For dates > today, fall back to climatological average from cache history.
    """
    start = pd.Timestamp(start).normalize()
    end   = pd.Timestamp(end).normalize()
    today = pd.Timestamp.today().normalize()

    cache = _load_cache()
    cached_dates = set(cache['ds'].dt.normalize()) if not cache.empty else set()

    hist_end = min(end, today)
    if start <= hist_end:
        all_hist = pd.date_range(start, hist_end, freq='D')
        missing  = [d for d in all_hist if d not in cached_dates]
        if missing:
            fetch_start = pd.Timestamp(min(missing))
            fetch_end   = pd.Timestamp(max(missing))
            new_rows = _fetch_range(fetch_start, fetch_end)
            cache = pd.concat([cache, new_rows], ignore_index=True).drop_duplicates('ds')
            _save_cache(cache)

    requested = pd.date_range(start, end, freq='D')
    result = cache[cache['ds'].isin(requested)].copy()

    future_dates = requested[requested > today]
    if len(future_dates) > 0:
        clim = _climatology(cache, future_dates)
        result = pd.concat([result, clim], ignore_index=True)

    return result.sort_values('ds').reset_index(drop=True)


def weather_multiplier(temp_max_c: float, precip_mm: float) -> float:
    """Revenue/sessions multiplier for synthetic data injection.

    precip > 2mm dampens traffic by 10%; temp_max > 33C drives indoor escape +8%.
    """
    mult = 1.0
    if precip_mm > 2.0:    mult *= 0.90
    if temp_max_c > 33.0:  mult *= 1.08
    return mult
