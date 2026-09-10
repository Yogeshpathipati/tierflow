"""
Local test for list_objects_by_prefix using moto (no real AWS calls).
Run: python -m pytest test_list_objects.py -v
"""

import boto3
import pytest
from moto import mock_aws

from list_objects import list_objects_by_prefix, list_prefixes

BUCKET = "tierflow-test-bucket"
REGION = "ap-south-1"


@pytest.fixture
def s3_setup():
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(
            Bucket=BUCKET,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )

        # raw-data/ - mixed storage classes
        s3.put_object(Bucket=BUCKET, Key="raw-data/file1.csv", Body=b"a" * 100)
        s3.put_object(
            Bucket=BUCKET, Key="raw-data/file2.csv", Body=b"b" * 200,
            StorageClass="STANDARD_IA",
        )

        # logs/ - untouched STANDARD objects
        s3.put_object(Bucket=BUCKET, Key="logs/2026-09-01.log", Body=b"c" * 50)
        s3.put_object(Bucket=BUCKET, Key="logs/2026-09-02.log", Body=b"d" * 75)

        yield s3


def test_list_objects_by_prefix_returns_correct_count(s3_setup):
    objs = list_objects_by_prefix(BUCKET, "raw-data/", region=REGION)
    assert len(objs) == 2


def test_list_objects_by_prefix_defaults_standard_class(s3_setup):
    objs = list_objects_by_prefix(BUCKET, "raw-data/", region=REGION)
    by_key = {o["key"]: o for o in objs}
    assert by_key["raw-data/file1.csv"]["storage_class"] == "STANDARD"
    assert by_key["raw-data/file2.csv"]["storage_class"] == "STANDARD_IA"


def test_list_objects_by_prefix_captures_size_and_key(s3_setup):
    objs = list_objects_by_prefix(BUCKET, "logs/", region=REGION)
    sizes = {o["key"]: o["size_bytes"] for o in objs}
    assert sizes["logs/2026-09-01.log"] == 50
    assert sizes["logs/2026-09-02.log"] == 75


def test_list_objects_by_prefix_empty_prefix_returns_empty(s3_setup):
    objs = list_objects_by_prefix(BUCKET, "nonexistent/", region=REGION)
    assert objs == []


def test_list_objects_by_prefix_missing_bucket_raises(s3_setup):
    with pytest.raises(RuntimeError):
        list_objects_by_prefix("no-such-bucket-at-all", "raw-data/", region=REGION)


def test_list_prefixes_discovers_top_level(s3_setup):
    prefixes = list_prefixes(BUCKET, region=REGION)
    assert set(prefixes) == {"raw-data/", "logs/"}
