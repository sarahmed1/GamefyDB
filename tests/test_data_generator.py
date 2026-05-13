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
