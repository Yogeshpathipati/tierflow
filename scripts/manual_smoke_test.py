import boto3

s3 = boto3.client('s3')
bucket = 'tierflow-daivik-test'

# List all objects and their current storage class
response = s3.list_objects_v2(Bucket=bucket)
for obj in response['Contents']:
    print(obj['Key'], obj['StorageClass'])

# Move one object to a cheaper storage tier
s3.copy_object(
    Bucket=bucket,
    CopySource={'Bucket': bucket, 'Key': 'raw-data/file1.txt'},
    Key='raw-data/file1.txt',
    StorageClass='STANDARD_IA'
)

# Re-list to confirm the change
response = s3.list_objects_v2(Bucket=bucket)
for obj in response['Contents']:
    print(obj['Key'], obj['StorageClass'])