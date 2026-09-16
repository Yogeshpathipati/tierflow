"""
TierFlow — EventBridge Cron Trigger Setup
==========================================
Run this once to create a daily EventBridge rule that invokes
the TierFlow Lambda function automatically at 02:00 UTC every day.

Usage:
    python infrastructure/eventbridge_setup.py

Requirements:
    - AWS credentials configured (aws configure)
    - Lambda function 'TierFlow' already deployed
    - IAM permissions: events:PutRule, events:PutTargets, lambda:AddPermission
"""

import boto3
import json

REGION          = "ap-south-1"
RULE_NAME       = "TierFlow-DailyTrigger"
LAMBDA_NAME     = "TierFlow"
SCHEDULE        = "cron(0 2 * * ? *)"   # 02:00 UTC every day
RULE_DESCRIPTION = "Triggers TierFlow Lambda daily to evaluate and tier S3 prefixes"


def setup_eventbridge_trigger():
    events_client = boto3.client("events", region_name=REGION)
    lambda_client  = boto3.client("lambda",  region_name=REGION)

    # 1. Get Lambda ARN
    print(f"Fetching Lambda ARN for '{LAMBDA_NAME}'...")
    lambda_info = lambda_client.get_function(FunctionName=LAMBDA_NAME)
    lambda_arn  = lambda_info["Configuration"]["FunctionArn"]
    print(f"  Lambda ARN: {lambda_arn}")

    # 2. Create the EventBridge cron rule
    print(f"\nCreating EventBridge rule '{RULE_NAME}'...")
    rule_response = events_client.put_rule(
        Name=RULE_NAME,
        ScheduleExpression=SCHEDULE,
        State="ENABLED",
        Description=RULE_DESCRIPTION,
    )
    rule_arn = rule_response["RuleArn"]
    print(f"  Rule ARN: {rule_arn}")

    # 3. Add Lambda as the target of the rule
    print(f"\nAdding Lambda as target...")
    events_client.put_targets(
        Rule=RULE_NAME,
        Targets=[
            {
                "Id":  "TierFlowLambdaTarget",
                "Arn": lambda_arn,
                "Input": json.dumps({"source": "eventbridge-daily-trigger"}),
            }
        ],
    )
    print("  Target added successfully")

    # 4. Grant EventBridge permission to invoke Lambda
    print(f"\nGranting EventBridge permission to invoke Lambda...")
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_NAME,
            StatementId="EventBridgeTierFlowInvoke",
            Action="lambda:InvokeFunction",
            Principal="events.amazonaws.com",
            SourceArn=rule_arn,
        )
        print("  Permission granted")
    except lambda_client.exceptions.ResourceConflictException:
        print("  Permission already exists — skipping")

    print(f"\n[SUCCESS] EventBridge trigger configured.")
    print(f"  Schedule : {SCHEDULE} (daily at 02:00 UTC)")
    print(f"  Rule ARN : {rule_arn}")
    print(f"  Lambda   : {lambda_arn}")
    print(f"\nTo verify in AWS Console:")
    print(f"  EventBridge > Rules > {RULE_NAME}")


if __name__ == "__main__":
    setup_eventbridge_trigger()
