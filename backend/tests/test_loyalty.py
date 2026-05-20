import pandas as pd
import pytest
from backend.packages.analytics.segmenter import score_member_loyalty


def _members(total_tnd, duration_min):
    n = len(total_tnd)
    return pd.DataFrame({
        'member_id':    range(1, n + 1),
        'username':     [f'u{i}' for i in range(1, n + 1)],
        'firstname':    ['A'] * n,
        'lastname':     ['B'] * n,
        'total_tnd':    total_tnd,
        'duration_min': duration_min,
    })


# 8 members with evenly spread values — Q1=[10,20] Q2=[30,40] Q3=[50,60] Q4=[70,80]
_SPREAD = [10, 20, 30, 40, 50, 60, 70, 80]


def test_output_columns():
    result = score_member_loyalty(_members(_SPREAD, _SPREAD))
    assert list(result.columns) == [
        'member_id', 'username', 'firstname', 'lastname',
        'total_tnd', 'duration_min', 'm_score', 'f_score', 'fm_score', 'loyalty_tier',
    ]


def test_sorted_descending_by_fm_score():
    result = score_member_loyalty(_members(_SPREAD, _SPREAD))
    assert result['fm_score'].is_monotonic_decreasing


def test_fm_score_equals_sum_of_m_and_f():
    result = score_member_loyalty(_members(_SPREAD, _SPREAD))
    assert (result['fm_score'] == result['m_score'] + result['f_score']).all()


def test_platinum_member():
    result = score_member_loyalty(_members(_SPREAD, _SPREAD))
    top = result[result['member_id'] == 8].iloc[0]
    assert top['loyalty_tier'] == 'Platinum'
    assert top['fm_score'] == 8


def test_bronze_member():
    result = score_member_loyalty(_members(_SPREAD, _SPREAD))
    bottom = result[result['member_id'] == 1].iloc[0]
    assert bottom['loyalty_tier'] == 'Bronze'
    assert bottom['fm_score'] == 2


def test_tier_mapping():
    result = score_member_loyalty(_members(_SPREAD, _SPREAD))
    tiers = result.set_index('fm_score')['loyalty_tier'].to_dict()
    assert tiers[8] == 'Platinum'
    for score, expected in [(6, 'Gold'), (7, 'Gold'), (4, 'Silver'), (5, 'Silver'),
                             (2, 'Bronze'), (3, 'Bronze')]:
        if score in tiers:
            assert tiers[score] == expected


def test_all_zero_members_excluded():
    df = _members([0, 0, 50, 80], [0, 0, 300, 600])
    result = score_member_loyalty(df)
    assert set(result['member_id']) == {3, 4}


def test_empty_input_returns_correct_columns():
    result = score_member_loyalty(_members([], []))
    assert result.empty
    assert 'loyalty_tier' in result.columns
    assert 'fm_score' in result.columns


def test_all_same_values_no_error():
    df = _members([100, 100, 100, 100, 100], [200, 200, 200, 200, 200])
    result = score_member_loyalty(df)
    assert len(result) == 5
    assert result['loyalty_tier'].notna().all()




