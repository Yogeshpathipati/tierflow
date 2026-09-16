import boto3
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from list_objects import list_objects_by_prefix, list_prefixes

s3 = boto3.client('s3')
bucket = 'tierflow-daivik-test'

# List all prefixes and their objects with full pagination (handles >1,000 objects)
print(f"Discovering prefixes in {bucket}...")
prefixes = list_prefixes(bucket)
print(f"Found prefixes: {prefixes}\n")

for prefix in prefixes:
    objs = list_objects_by_prefix(bucket, prefix)
    print(f"--- {prefix} ({len(objs)} objects) ---")
    for obj in objs:
        print(obj['key'], obj.get('storage_class', 'STANDARD'))

# Move one object to a cheaper storage tier
s3.copy_object(
    Bucket=bucket,
    CopySource={'Bucket': bucket, 'Key': 'raw-data/file1.txt'},
    Key='raw-data/file1.txt',
    StorageClass='STANDARD_IA'
)
print("\nMoved raw-data/file1.txt to STANDARD_IA")

# Re-list to confirm the change
print("\nRe-checking after move:")
objs = list_objects_by_prefix(bucket, 'raw-data/')
for obj in objs:
    print(obj['key'], obj.get('storage_class', 'STANDARD'))