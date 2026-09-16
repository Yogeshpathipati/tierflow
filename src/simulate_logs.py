"""
TierFlow — Simulated Access-Pattern Log Generator (Scaled to 500+ prefixes)

Generates a per-prefix dataset matching the schema TierFlow's
decide_storage_class() consumes, without waiting on real S3
Server Access Logs to be delivered.

Schema:
    prefix                  - S3 key prefix (group-level, not per-object)
    last_accessed_days_ago  - int, days since last read
    access_count_30d        - int, number of reads in the last 30 days

Generation strategy:
    Prefixes are generated across 6 departments, 3 data types, 7 years,
    and 4 quarters — producing 504 realistic prefixes. Access patterns
    are assigned by data age so the tier distribution reflects a real
    enterprise workload.
"""

import csv
import random
import os

random.seed(42)  # reproducible runs

# Always write to data/ folder relative to this file, not the cwd
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tierflow_simulated_logs.csv")

# -----------------------------------------------------------------------
# Workload dimensions
# -----------------------------------------------------------------------
DEPARTMENTS = ["engineering", "finance", "hr", "sales", "marketing", "ops"]
DATA_TYPES  = ["raw-data", "logs", "reports"]
YEARS       = [2020, 2021, 2022, 2023, 2024, 2025, 2026]
QUARTERS    = ["Q1", "Q2", "Q3", "Q4"]

# Access-pattern ranges per category
RANGES = {
    "hot":    {"days": (0,   3),   "count": (40, 120)},
    "warm":   {"days": (4,   20),  "count": (10, 39)},
    "cool":   {"days": (21,  59),  "count": (2,  9)},
    "cold":   {"days": (60,  150), "count": (0,  2)},
    "frozen": {"days": (200, 500), "count": (0,  0)},
    "never":  {"days": (365, 700), "count": (0,  0)},
}

def year_to_category(year: int) -> str:
    """Map data year to an access category based on typical retention patterns."""
    if year == 2026:
        return random.choice(["hot", "warm"])
    elif year == 2025:
        return random.choice(["warm", "cool"])
    elif year == 2024:
        return "cold"
    elif year == 2023:
        return random.choice(["cold", "frozen"])
    else:  # 2022 and older
        return random.choice(["frozen", "never"])

def generate_row(prefix: str, category: str) -> tuple:
    r = RANGES[category]
    days  = random.randint(*r["days"])
    count = random.randint(*r["count"])
    return prefix, days, count

def build_prefixes() -> list[tuple]:
    """Generate 500+ prefixes across departments, data types, years, quarters."""
    rows = []
    for dept in DEPARTMENTS:
        for dtype in DATA_TYPES:
            for year in YEARS:
                for quarter in QUARTERS:
                    prefix   = f"{dept}/{dtype}/{year}-{quarter}/"
                    category = year_to_category(year)
                    rows.append(generate_row(prefix, category))

    # Add extra edge-case prefixes to stress-test boundary conditions
    edge_cases = [
        ("shared/onboarding-assets/",   45,  0),   # edge: cool age, zero reads
        ("shared/deprecated-schema/",   180, 0),   # edge: exactly on DEEP_ARCHIVE threshold
        ("shared/compliance/2022/",     400, 0),   # edge: very old, never accessed
        ("shared/active-project/",      1,   95),  # edge: very hot
        ("shared/edge-60days/",         60,  1),   # edge: exactly on GLACIER threshold
        ("shared/edge-21days/",         21,  9),   # edge: exactly on STANDARD_IA threshold
        ("shared/edge-single-access/",  89,  1),   # edge: one read, near DEEP_ARCHIVE
        ("shared/edge-zero-access/",    45,  0),   # edge: cool age but zero reads
    ]
    for prefix, days, count in edge_cases:
        rows.append((prefix, days, count))

    return rows

def main():
    rows = build_prefixes()

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["prefix", "last_accessed_days_ago", "access_count_30d"])
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")
    print(f"Breakdown by year category:")

    # Quick summary
    cat_counts = {}
    for _, days, count in rows:
        if days <= 3:   cat = "hot"
        elif days <= 20: cat = "warm"
        elif days <= 59: cat = "cool"
        elif days <= 150: cat = "cold"
        else:           cat = "frozen/never"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    for cat, n in sorted(cat_counts.items()):
        print(f"  {cat:<15}: {n} prefixes")

if __name__ == "__main__":
    main()
