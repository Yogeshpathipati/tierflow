"""
TierFlow — Unit Tests for decide_storage_class()
Tests all 4 rule branches, all boundary conditions, and edge cases.
Run: python -m pytest tests/test_decide_storage_class.py -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from decide_storage_class import decide_storage_class


# -----------------------------------------------------------------------
# STANDARD (Rule 4: recently / frequently accessed)
# -----------------------------------------------------------------------
def test_standard_very_recent_high_access():
    assert decide_storage_class(0, 100) == "STANDARD"

def test_standard_recent_moderate_access():
    assert decide_storage_class(5, 20) == "STANDARD"

def test_standard_20_days_10_reads():
    # Just inside STANDARD: 20 days, 10 reads (not >= 21 so Rule 3 doesn't fire)
    assert decide_storage_class(20, 10) == "STANDARD"

def test_standard_zero_days():
    assert decide_storage_class(0, 0) == "STANDARD"


# -----------------------------------------------------------------------
# STANDARD_IA (Rule 3: >= 21 days AND <= 9 reads)
# -----------------------------------------------------------------------
def test_standard_ia_exactly_21_days_9_reads():
    # Exactly on threshold — should match Rule 3
    assert decide_storage_class(21, 9) == "STANDARD_IA"

def test_standard_ia_30_days_5_reads():
    assert decide_storage_class(30, 5) == "STANDARD_IA"

def test_standard_ia_59_days_9_reads():
    # Just below GLACIER threshold
    assert decide_storage_class(59, 9) == "STANDARD_IA"

def test_standard_ia_21_days_zero_reads():
    # 21 days but no reads — GLACIER needs >=60 days, so this is STANDARD_IA
    assert decide_storage_class(21, 0) == "STANDARD_IA"


# -----------------------------------------------------------------------
# GLACIER (Rule 2: >= 60 days AND <= 1 read)
# -----------------------------------------------------------------------
def test_glacier_exactly_60_days_1_read():
    # Exactly on threshold
    assert decide_storage_class(60, 1) == "GLACIER"

def test_glacier_60_days_zero_reads():
    # Zero reads but only 60 days — not old enough for DEEP_ARCHIVE (needs 180)
    assert decide_storage_class(60, 0) == "GLACIER"

def test_glacier_90_days_zero_reads():
    # Old but not 180 days — stays in GLACIER
    assert decide_storage_class(90, 0) == "GLACIER"

def test_glacier_150_days_1_read():
    assert decide_storage_class(150, 1) == "GLACIER"

def test_glacier_179_days_zero_reads():
    # One day short of DEEP_ARCHIVE threshold
    assert decide_storage_class(179, 0) == "GLACIER"


# -----------------------------------------------------------------------
# DEEP_ARCHIVE (Rule 1: >= 180 days AND 0 reads)
# -----------------------------------------------------------------------
def test_deep_archive_exactly_180_days_zero_reads():
    # Exactly on threshold
    assert decide_storage_class(180, 0) == "DEEP_ARCHIVE"

def test_deep_archive_365_days_zero_reads():
    assert decide_storage_class(365, 0) == "DEEP_ARCHIVE"

def test_deep_archive_700_days_zero_reads():
    assert decide_storage_class(700, 0) == "DEEP_ARCHIVE"


# -----------------------------------------------------------------------
# BOUNDARY / EDGE cases — ensures rules fire in correct order
# -----------------------------------------------------------------------
def test_180_days_with_1_read_is_glacier_not_deep_archive():
    # Rule 1 requires 0 reads — 1 read disqualifies DEEP_ARCHIVE, falls to GLACIER
    assert decide_storage_class(180, 1) == "GLACIER"

def test_60_days_with_2_reads_is_standard_ia_not_glacier():
    # Rule 2 requires <= 1 read — 2 reads disqualifies GLACIER, falls to STANDARD_IA
    assert decide_storage_class(60, 2) == "STANDARD_IA"

def test_21_days_with_10_reads_is_standard_not_ia():
    # Rule 3 requires <= 9 reads — 10 reads disqualifies STANDARD_IA
    assert decide_storage_class(21, 10) == "STANDARD"

def test_return_type_is_always_string():
    for days in [0, 21, 60, 180, 400]:
        for count in [0, 1, 9, 10, 50]:
            result = decide_storage_class(days, count)
            assert isinstance(result, str)
            assert result in {"STANDARD", "STANDARD_IA", "GLACIER", "DEEP_ARCHIVE"}
