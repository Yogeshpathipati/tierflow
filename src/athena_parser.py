import boto3
import time

def parse_real_s3_logs(database_name='tierflow_db', output_location='s3://tierflow-daivik-logs/athena-results/'):
    """
    Queries Athena for real S3 access logs and formats them to match
    the schema expected by decide_storage_class().
    """
    athena_client = boto3.client('athena', region_name='ap-south-1')
    
    # The SQL query that extracts the exact metrics Daivik's logic requires
    query = """
        SELECT
            regexp_extract(key, '^([^/]+/[^/]+)/', 1) || '/' AS prefix,
            date_diff('day', max(parse_datetime(requestdatetime, 'dd/MMM/yyyy:HH:mm:ss Z')), current_timestamp) AS last_accessed_days_ago,
            COUNT(CASE WHEN date_diff('day', parse_datetime(requestdatetime, 'dd/MMM/yyyy:HH:mm:ss Z'), current_timestamp) <= 30 THEN 1 END) AS access_count_30d
        FROM s3_access_logs
        WHERE operation = 'REST.GET.OBJECT'
          AND key IS NOT NULL
          AND key LIKE '%/%'
        GROUP BY regexp_extract(key, '^([^/]+/[^/]+)/')
    """
    
    print("Initiating Athena query...")
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': database_name},
        ResultConfiguration={'OutputLocation': output_location}
    )
    
    execution_id = response['QueryExecutionId']
    
    # Wait for the serverless query to complete (timeout after 60 seconds)
    state = 'RUNNING'
    start_time = time.time()
    TIMEOUT_SECONDS = 60
    while state in ['RUNNING', 'QUEUED']:
        if time.time() - start_time > TIMEOUT_SECONDS:
            raise Exception(f"Athena query timed out after {TIMEOUT_SECONDS} seconds")
        time.sleep(2)
        status = athena_client.get_query_execution(QueryExecutionId=execution_id)
        state = status['QueryExecution']['Status']['State']
        
    if state != 'SUCCEEDED':
        raise Exception(f"Athena query failed with state: {state}")
        
    # Fetch and parse the results
    results_paginator = athena_client.get_paginator('get_query_results')
    parsed_data = []
    
    for results_page in results_paginator.paginate(QueryExecutionId=execution_id):
        for row in results_page['ResultSet']['Rows'][1:]: # Skip the header row
            data = row['Data']
            
            # Map Athena string outputs to the correct Python types
            prefix = data[0]['VarCharValue']
            last_accessed = int(data[1]['VarCharValue'])
            count_30d = int(data[2]['VarCharValue'])
            
            parsed_data.append({
                'prefix': prefix,
                'last_accessed_days_ago': last_accessed,
                'access_count_30d': count_30d
            })
            
    print(f"Successfully parsed {len(parsed_data)} prefixes from real logs.")
    return parsed_data

if __name__ == "__main__":
    # Test execution (will return an empty list until S3 drops the first log file!)
    real_data = parse_real_s3_logs()
    print(real_data)