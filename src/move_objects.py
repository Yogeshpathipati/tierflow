import os
import boto3
from list_objects import list_objects_by_prefix

s3_client = boto3.client('s3')

# Read bucket name from environment variable — fallback to dev bucket
BUCKET_NAME = os.environ.get('TIERFLOW_BUCKET', 'tierflow-daivik-test')


def copy_object_to_tier(prefix, target_tier):
    print(f"Initiating move for {prefix} to {target_tier}...")

    # Use the paginated lister from list_objects.py — handles >1,000 objects correctly
    objects = list_objects_by_prefix(BUCKET_NAME, prefix)

    if not objects:
        print(f"No objects found under prefix: {prefix}")
        return

    for obj in objects:
        object_key = obj['key']
        try:
            # Copy the file over itself with the new storage tier
            s3_client.copy_object(
                Bucket=BUCKET_NAME,
                Key=object_key,
                CopySource={'Bucket': BUCKET_NAME, 'Key': object_key},
                StorageClass=target_tier
            )
            print(f"Successfully transitioned {object_key} to {target_tier}")
        except Exception as e:
            print(f"[ERROR] Failed to transition {object_key}: {e}")