import logging
import os
from athena_parser import parse_real_s3_logs
from decide_storage_class import decide_storage_class
from move_objects import copy_object_to_tier

# Structured CloudWatch logging — replaces all print() statements
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("TierFlow Lambda started", extra={"event": str(event)})

    # 1. Fetch real access metrics using the Athena parser
    logger.info("Fetching S3 access metrics via Athena...")
    real_metrics = parse_real_s3_logs()
    logger.info(f"Athena returned {len(real_metrics)} prefixes to evaluate")

    moved = 0
    skipped = 0

    # 2. Process tiering decisions
    for metric in real_metrics:
        prefix    = metric['prefix']
        days_ago  = metric['last_accessed_days_ago']
        count_30d = metric['access_count_30d']

        target_tier = decide_storage_class(days_ago, count_30d)
        logger.info(f"Decision | prefix={prefix} | days_ago={days_ago} | "
                    f"count_30d={count_30d} | target_tier={target_tier}")

        # 3. Execute the S3 move
        try:
            copy_object_to_tier(prefix, target_tier)
            logger.info(f"Move OK  | prefix={prefix} -> {target_tier}")
            moved += 1
        except Exception as e:
            logger.error(f"Move FAIL | prefix={prefix} | error={e}")
            skipped += 1

    logger.info(f"TierFlow complete | moved={moved} | failed={skipped} | "
                f"total={len(real_metrics)}")

    return {
        'statusCode': 200,
        'body': {
            'message': 'TierFlow execution complete',
            'prefixes_evaluated': len(real_metrics),
            'moved': moved,
            'failed': skipped
        }
    }