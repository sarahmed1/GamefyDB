import pandas as pd
import numpy as np
import pytest
from gamefydb.segmenter import segment_members


VALID_LABELS = {'Heavy Users', 'Casual Spenders', 'Regulars', 'Light Users'}


def make_members():
    return pd.DataFrame({
        'member_id':    [1,    2,    3,    4,    5,    6,    7,    8],
        'username':     ['a',  'b',  'c',  'd',  'e',  'f',  'g',  'h'],
        'firstname':    ['A',  'B',  'C',  'D',  'E',  'F',  'G',  'H'],
        'lastname':     ['',   '',   '',   '',   '',   '',   '',   ''],
        'total_tnd':    [1000, 800,  500,  300,  200,  100,  50,   20],
        'duration_min': [500,  400,  300,  200,  100,  80,   30,   10],
        'orders_tnd':   [200,  150,  100,  80,   50,   30,   10,   2],
        'usage_tnd':    [800,  650,  400,  220,  150,  70,   40,   18],
        'usb_tnd':      [0,    0,    0,    0,    0,    0,    0,    0],
    })


def test_returns_dataframe():
    result = segment_members(make_members())
    assert isinstance(result, pd.DataFrame)


def test_adds_cluster_id_column():
    result = segment_members(make_members())
    assert 'cluster_id' in result.columns


def test_adds_segment_label_column():
    result = segment_members(make_members())
    assert 'segment_label' in result.columns


def test_cluster_id_is_integer():
    result = segment_members(make_members())
    assert np.issubdtype(result['cluster_id'].dtype, np.integer)


def test_four_unique_labels():
    result = segment_members(make_members())
    assert result['segment_label'].nunique() == 4


def test_labels_are_valid():
    result = segment_members(make_members())
    assert set(result['segment_label'].unique()).issubset(VALID_LABELS)


def test_preserves_member_columns():
    result = segment_members(make_members())
    for col in ['member_id', 'username', 'firstname', 'lastname']:
        assert col in result.columns


def test_preserves_feature_columns():
    result = segment_members(make_members())
    for col in ['total_tnd', 'duration_min', 'orders_tnd']:
        assert col in result.columns


def test_output_row_count_matches_non_zero_input():
    df = make_members()
    result = segment_members(df)
    assert len(result) == len(df)


def test_drops_all_zero_members():
    df = make_members()
    df.loc[0, ['total_tnd', 'duration_min', 'orders_tnd']] = 0
    result = segment_members(df)
    assert 1 not in result['member_id'].values


def test_heavy_user_has_highest_spend():
    result = segment_members(make_members())
    heavy = result[result['segment_label'] == 'Heavy Users']['total_tnd'].mean()
    light = result[result['segment_label'] == 'Light Users']['total_tnd'].mean()
    assert heavy > light


def test_no_extra_columns():
    result = segment_members(make_members())
    expected = {'member_id', 'username', 'firstname', 'lastname',
                'total_tnd', 'duration_min', 'orders_tnd',
                'cluster_id', 'segment_label'}
    assert set(result.columns) == expected
