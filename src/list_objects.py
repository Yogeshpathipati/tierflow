"""
TierFlow - Person B (Backend/Core Logic)
Lists S3 objects under a given prefix, with the metadata needed
downstream by decide_storage_class() and the copy_object mover.

Design notes:
- Uses list_objects_v2 with a paginator, since a bucket can hold
  more than 1000 keys under a prefix and a single call truncates
  silently unless you follow ContinuationToken.
- StorageClass is only present in the response for objects NOT in
  STANDARD (boto3/S3 quirk) - we normalize that to "STANDARD" so
  downstream code always has a value to compare against.
- Returns plain dicts (not boto3's raw response) so decide_storage_class()
  and the rest of the pipeline don't need to know anything about the API
  shape - this is the boundary between "AWS-facing" and "logic-facing" code.
"""

import boto3
from botocore.exceptions import ClientError
import os

# Read region from environment — defaults to ap-south-1 (Mumbai)
REGION = os.environ.get('AWS_REGION', 'ap-south-1')


def list_objects_by_prefix(bucket: str, prefix: str, region: str = REGION) -> list[dict]:
    """
    List all objects under a given prefix in an S3 bucket.

    Args:
        bucket: bucket name, e.g. "tierflow-daivik-test"
        prefix: prefix to filter under, e.g. "raw-data/" or "logs/"
        region: AWS region (defaults to ap-south-1)

    Returns:
        List of dicts, one per object:
        {
            "key": str,
            "size_bytes": int,
            "last_modified": datetime,
            "storage_class": str,   # e.g. "STANDARD", "STANDARD_IA", "GLACIER"
            "etag": str,
        }
    """
    s3 = boto3.client("s3", region_name=region)
    objects = []

    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                objects.append({
                    "key": obj["Key"],
                    "size_bytes": obj["Size"],
                    "last_modified": obj["LastModified"],
                    # S3 omits StorageClass for STANDARD objects - default it in.
                    "storage_class": obj.get("StorageClass", "STANDARD"),
                    "etag": obj["ETag"].strip('"'),
                })
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "NoSuchBucket":
            raise RuntimeError(f"Bucket '{bucket}' does not exist") from e
        raise

    return objects


def list_prefixes(bucket: str, delimiter: str = "/", region: str = REGION) -> list[str]:
    """
    Discover top-level prefixes ("folders") in the bucket, e.g. ["raw-data/", "logs/"].
    Useful for iterating over all prefixes without hardcoding them.
    """
    s3 = boto3.client("s3", region_name=region)
    prefixes = []

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Delimiter=delimiter):
        for cp in page.get("CommonPrefixes", []):
            prefixes.append(cp["Prefix"])

    return prefixes


if __name__ == "__main__":
    BUCKET = "tierflow-daivik-test"

    print(f"Discovering prefixes in {BUCKET}...")
    prefixes = list_prefixes(BUCKET)
    print(f"Found prefixes: {prefixes}\n")

    for prefix in prefixes:
        objs = list_objects_by_prefix(BUCKET, prefix)
        print(f"--- {prefix} ({len(objs)} objects) ---")
        for o in objs:
            print(f"  {o['key']:<40} {o['size_bytes']:>10} bytes  "
                  f"{o['storage_class']:<12} last_mod={o['last_modified']}")
        print()
