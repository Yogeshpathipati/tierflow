"""
TierFlow — Unit Tests for move_objects.copy_object_to_tier()
Uses moto to mock S3 — no real AWS calls made.
Run: python -m pytest tests/test_move_objects.py -v
"""
import sys
import os
import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import move_objects  # imported as module so we can patch BUCKET_NAME

BUCKET  = "tierflow-daivik-test"
REGION  = "ap-south-1"


@pytest.fixture(autouse=True)
def patch_bucket(monkeypatch):
    """Point move_objects at our test bucket name."""
    monkeypatch.setattr(move_objects, "BUCKET_NAME", BUCKET)


@pytest.fixture
def s3_with_objects():
    """Create a mock S3 bucket with 3 test objects in raw-data/ prefix."""
    with mock_aws():
        s3 = boto3.client("s3", region_name=REGION)
        s3.create_bucket(
            Bucket=BUCKET,
            CreateBucketConfiguration={"LocationConstraint": REGION},
        )
        for i in range(1, 4):
            s3.put_object(Bucket=BUCKET, Key=f"raw-data/file{i}.txt", Body=b"x" * 100)
        yield s3


def test_copy_object_to_tier_changes_storage_class(s3_with_objects):
    """After calling copy_object_to_tier, all objects should be in STANDARD_IA."""
    move_objects.s3_client = boto3.client("s3", region_name=REGION)
    move_objects.copy_object_to_tier("raw-data/", "STANDARD_IA")

    response = s3_with_objects.list_objects_v2(Bucket=BUCKET, Prefix="raw-data/")
    for obj in response["Contents"]:
        head = s3_with_objects.head_object(Bucket=BUCKET, Key=obj["Key"])
        assert head["StorageClass"] == "STANDARD_IA"


def test_copy_object_to_tier_processes_all_objects(s3_with_objects, capsys):
    """All 3 objects should be transitioned — no silent truncation."""
    move_objects.s3_client = boto3.client("s3", region_name=REGION)
    move_objects.copy_object_to_tier("raw-data/", "GLACIER")

    captured = capsys.readouterr()
    assert "file1.txt" in captured.out
    assert "file2.txt" in captured.out
    assert "file3.txt" in captured.out


def test_copy_object_to_tier_empty_prefix_does_nothing(s3_with_objects, capsys):
    """An empty prefix should print a warning and not crash."""
    move_objects.s3_client = boto3.client("s3", region_name=REGION)
    move_objects.copy_object_to_tier("nonexistent/", "GLACIER")

    captured = capsys.readouterr()
    assert "No objects found" in captured.out


def test_copy_object_to_tier_glacier(s3_with_objects):
    """Verify GLACIER tier is set correctly."""
    move_objects.s3_client = boto3.client("s3", region_name=REGION)
    move_objects.copy_object_to_tier("raw-data/", "GLACIER")

    response = s3_with_objects.list_objects_v2(Bucket=BUCKET, Prefix="raw-data/")
    for obj in response["Contents"]:
        head = s3_with_objects.head_object(Bucket=BUCKET, Key=obj["Key"])
        assert head["StorageClass"] == "GLACIER"
