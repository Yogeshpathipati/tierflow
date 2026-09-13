import boto3

s3_client = boto3.client('s3')
BUCKET_NAME = 'tierflow-daivik-test'

def copy_object_to_tier(prefix, target_tier):
    print(f"Initiating move for {prefix} to {target_tier}...")
    
    # 1. List all files inside the project-data/ folder
    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
    
    if 'Contents' in response:
        for obj in response['Contents']:
            object_key = obj['Key']
            
            # 2. Copy the file over itself with the new storage tier
            s3_client.copy_object(
                Bucket=BUCKET_NAME,
                Key=object_key,
                CopySource={'Bucket': BUCKET_NAME, 'Key': object_key},
                StorageClass=target_tier
            )
            print(f"Successfully transitioned {object_key} to {target_tier}")