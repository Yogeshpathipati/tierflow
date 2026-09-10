"""
TierFlow — decide_storage_class()

This is the core rule-based decision function for Person B's part of the
project. Given how recently and how often a prefix's objects have been
accessed, it decides which S3 storage class that prefix should be tiered to.

How to read the rules below: they're checked TOP TO BOTTOM, and the first
one that matches wins. So order matters — most specific/extreme cases go
first (DEEP_ARCHIVE), most common case goes last (STANDARD).

Thresholds used here are a reasonable starting point — you and your team
should tune these based on your literature survey / assumptions section.
"""

import csv


def decide_storage_class(last_accessed_days_ago: int, access_count_30d: int) -> str:
    """
    Decide the target S3 storage class for a prefix based on its access pattern.

    Args:
        last_accessed_days_ago: days since the prefix was last read
        access_count_30d: number of reads in the last 30 days

    Returns:
        One of "STANDARD", "STANDARD_IA", "GLACIER", "DEEP_ARCHIVE"
    """

    # Rule 1: Very old AND essentially untouched -> cheapest, slowest tier
    if last_accessed_days_ago >= 180 and access_count_30d == 0:
        return "DEEP_ARCHIVE"

    # Rule 2: Old and rarely touched -> cold storage, but still retrievable
    if last_accessed_days_ago >= 60 and access_count_30d <= 1:
        return "GLACIER"

    # Rule 3: Aging and infrequently accessed -> cheaper "warm" tier
    if last_accessed_days_ago >= 21 and access_count_30d <= 9:
        return "STANDARD_IA"

    # Rule 4 (default): Recently and/or frequently accessed -> keep it fast
    return "STANDARD"


def run_against_csv(csv_path: str) -> None:
    """
    Reads the simulated (or later, real) log CSV and prints the
    storage class decision for every prefix.
    """
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)

        print(f"{'prefix':35} {'days_ago':>9} {'count_30d':>10}   -> decision")
        print("-" * 75)

        for row in reader:
            prefix = row["prefix"]
            days_ago = int(row["last_accessed_days_ago"])
            count_30d = int(row["access_count_30d"])

            decision = decide_storage_class(days_ago, count_30d)

            print(f"{prefix:35} {days_ago:>9} {count_30d:>10}   -> {decision}")


if __name__ == "__main__":
    run_against_csv("tierflow_simulated_logs.csv")
