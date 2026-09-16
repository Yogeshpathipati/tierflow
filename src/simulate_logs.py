"""
TierFlow — Simulated Access-Pattern Log Generator

Generates a per-prefix dataset matching the schema TierFlow's
decide_storage_class() consumes, without waiting on real S3
Server Access Logs to be delivered.

Schema:
    prefix                  - S3 key prefix (group-level, not per-object)
    last_accessed_days_ago  - int, days since last read
    access_count_30d        - int, number of reads in the last 30 days

Scenarios covered (so decide_storage_class() has real cases to branch on):
    - hot:        frequent, recent access        -> should stay STANDARD
    - warm:       moderate, semi-recent access    -> STANDARD or STANDARD_IA
    - cool:       infrequent, aging access        -> STANDARD_IA
    - cold:       old, rare access                -> GLACIER
    - frozen:     very old, effectively unused     -> DEEP_ARCHIVE
    - never:      access_count_30d == 0, no recent read at all
    - edge cases: values sitting exactly on likely thresholds (30/60/90 days,
                  0/1 access counts) to stress-test boundary conditions
"""

import csv
import random
import os

random.seed(42)  # reproducible runs

# Always write to data/ folder relative to this file, not the cwd
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tierflow_simulated_logs.csv")

# (prefix, category) — prefixes live under your real bucket's raw-data/ and logs/ trees
PREFIXES = [
    ("raw-data/2026-q1/", "hot"),
    ("raw-data/2026-q2/", "hot"),
    ("raw-data/2026-current/", "hot"),
    ("raw-data/2025-q4/", "warm"),
    ("raw-data/2025-q3/", "warm"),
    ("raw-data/2025-q2/", "cool"),
    ("raw-data/2025-q1/", "cool"),
    ("raw-data/2024-archive/", "cold"),
    ("raw-data/2023-archive/", "frozen"),
    ("raw-data/2022-archive/", "frozen"),
    ("raw-data/onboarding-assets/", "never"),
    ("raw-data/deprecated-schema/", "never"),
    ("logs/app-server/2026/", "hot"),
    ("logs/app-server/2025-q4/", "warm"),
    ("logs/batch-jobs/2026/", "warm"),
    ("logs/batch-jobs/2025/", "cool"),
    ("logs/debug/2025/", "cold"),
    ("logs/debug/2024/", "frozen"),
    ("logs/audit/2025/", "cold"),
    ("logs/audit/2022/", "frozen"),
    # edge cases sitting on likely rule thresholds
    ("raw-data/edge-30days/", "edge_30"),
    ("raw-data/edge-60days/", "edge_60"),
    ("raw-data/edge-90days/", "edge_90"),
    ("raw-data/edge-zero-access/", "edge_zero"),
    ("raw-data/edge-single-access/", "edge_single"),
]

RANGES = {
    "hot":    {"days": (0, 3),    "count": (40, 120)},
    "warm":   {"days": (4, 20),   "count": (10, 39)},
    "cool":   {"days": (21, 59),  "count": (2, 9)},
    "cold":   {"days": (60, 150), "count": (0, 2)},
    "frozen": {"days": (200, 500),"count": (0, 0)},
    "never":  {"days": (365, 700),"count": (0, 0)},
}

EDGE_VALUES = {
    "edge_30":       {"days": 30, "count": 5},
    "edge_60":       {"days": 60, "count": 1},
    "edge_90":       {"days": 90, "count": 0},
    "edge_zero":     {"days": 45, "count": 0},
    "edge_single":   {"days": 89, "count": 1},
}


def generate_row(prefix, category):
    if category in EDGE_VALUES:
        vals = EDGE_VALUES[category]
        return prefix, vals["days"], vals["count"]

    r = RANGES[category]
    days = random.randint(*r["days"])
    count = random.randint(*r["count"])
    return prefix, days, count


def main():
    rows = [generate_row(prefix, category) for prefix, category in PREFIXES]

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["prefix", "last_accessed_days_ago", "access_count_30d"])
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
