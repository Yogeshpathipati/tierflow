"""
TierFlow — Person C: Data & Cost Analysis Model
=================================================
Role: Data / Predictive Analytics Lead ( P. Yogesh)
File: scripts/cost_analysis.py

What this script does:
1. Ingests prefix access telemetry (simulated or real S3 logs).
2. Classifies each prefix into its optimal S3 tier via TierFlow's decision engine.
3. Computes rigorous AWS cost models comparing three paradigms:
   - Baseline (Always S3 STANDARD @ $0.023/GB)
   - AWS S3 Intelligent-Tiering (Tier rates + $0.0025/10k objects monitoring fee)
   - TierFlow (Prefix-level tiering + Athena serverless query overhead, $0 monitoring fee)
4. Evaluates workload scalability across data sizes (1 TB to 50 TB) and object counts.
5. Generates high-resolution visualization charts for project slides:
   - 'tierflow_cost_comparison.png'
   - 'tierflow_tier_distribution.png'
6. Prints a comprehensive financial executive summary to terminal.
"""

import os
import sys
import csv

# Add src to path so we can import the decision logic
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
try:
    from decide_storage_class import decide_storage_class
except ImportError:
    # Inline fallback if run outside repo structure
    def decide_storage_class(days_ago: int, count_30d: int) -> str:
        if days_ago >= 180 and count_30d == 0:
            return "DEEP_ARCHIVE"
        if days_ago >= 60 and count_30d <= 1:
            return "GLACIER"
        if days_ago >= 21 and count_30d <= 9:
            return "STANDARD_IA"
        return "STANDARD"

# ==============================================================================
# AWS PRICING CONSTANTS (ap-south-1 / Mumbai Region, USD per GB-month)
# ==============================================================================
PRICING = {
    "STANDARD": 0.0230,       # $0.023 per GB
    "STANDARD_IA": 0.0125,    # $0.0125 per GB (~45% cheaper than Standard)
    "GLACIER": 0.0036,        # $0.0036 per GB (~84% cheaper than Standard)
    "DEEP_ARCHIVE": 0.00099,  # $0.00099 per GB (~95% cheaper than Standard)
}

# AWS Intelligent-Tiering per-object monthly monitoring fee: $0.0025 per 10,000 objects
INT_TIERING_MONITORING_PER_OBJ = 0.0025 / 10000.0

# Athena query cost: $5.00 per TB scanned (approx 10 MB per monthly access log query = $0.00005)
ATHENA_MONTHLY_QUERY_OVERHEAD = 0.05  # Generous upper bound for frequent daily queries


def load_dataset(csv_path: str) -> list[dict]:
    """Loads prefix access logs from CSV."""
    if not os.path.exists(csv_path):
        print(f"[!] Warning: {csv_path} not found. Using default simulated distribution.")
        return []

    records = []
    with open(csv_path, mode="r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                "prefix": row["prefix"],
                "last_accessed_days_ago": int(row["last_accessed_days_ago"]),
                "access_count_30d": int(row["access_count_30d"]),
            })
    return records


def evaluate_workload(records: list[dict]):
    """Classifies each prefix and counts tier distribution."""
    tier_counts = {"STANDARD": 0, "STANDARD_IA": 0, "GLACIER": 0, "DEEP_ARCHIVE": 0}
    decisions = []

    for r in records:
        tier = decide_storage_class(r["last_accessed_days_ago"], r["access_count_30d"])
        tier_counts[tier] += 1
        decisions.append({**r, "tier": tier})

    total = len(records)
    tier_proportions = {k: v / total for k, v in tier_counts.items()} if total > 0 else {}
    return decisions, tier_counts, tier_proportions


def calculate_costs(total_storage_gb: float, num_objects: int, tier_proportions: dict):
    """
    Computes monthly storage and operational costs across 3 approaches:
    1. S3 Standard Baseline
    2. S3 Intelligent-Tiering
    3. TierFlow
    """
    # 1. Baseline: 100% of data sits in STANDARD
    cost_baseline = total_storage_gb * PRICING["STANDARD"]

    # 2. TierFlow: Proportional allocation across tiers + Athena query cost
    cost_tierflow_storage = sum(
        total_storage_gb * prop * PRICING[tier]
        for tier, prop in tier_proportions.items()
    )
    cost_tierflow_total = cost_tierflow_storage + ATHENA_MONTHLY_QUERY_OVERHEAD

    # 3. AWS Intelligent-Tiering: Similar storage distribution + per-object monitoring fee
    cost_int_tiering_storage = cost_tierflow_storage  # Same storage savings
    cost_int_tiering_monitoring = num_objects * INT_TIERING_MONITORING_PER_OBJ
    cost_int_tiering_total = cost_int_tiering_storage + cost_int_tiering_monitoring

    savings_vs_baseline = cost_baseline - cost_tierflow_total
    savings_pct = (savings_vs_baseline / cost_baseline) * 100.0

    return {
        "cost_baseline": cost_baseline,
        "cost_int_tiering": cost_int_tiering_total,
        "int_tiering_fee": cost_int_tiering_monitoring,
        "cost_tierflow": cost_tierflow_total,
        "tierflow_overhead": ATHENA_MONTHLY_QUERY_OVERHEAD,
        "monthly_savings_usd": savings_vs_baseline,
        "savings_percentage": savings_pct,
    }


def generate_charts(tier_counts: dict, output_dir: str):
    """Generates visual figures for Person D's presentation slides using matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # Non-interactive headless backend
        import matplotlib.pyplot as plt
    except ImportError:
        print("[*] matplotlib not installed. Skipping chart PNG generation.")
        print("    Install matplotlib (`pip install matplotlib`) to produce slide graphs.")
        return

    os.makedirs(output_dir, exist_ok=True)

    # --------------------------------------------------------------------------
    # Chart 1: Tier Distribution (Donut Chart)
    # --------------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(6, 5))
    tiers = list(tier_counts.keys())
    counts = [tier_counts[t] for t in tiers]
    colors = ["#2563eb", "#38bdf8", "#0284c7", "#1e3a8a"]

    wedges, texts, autotexts = ax.pie(
        counts,
        labels=tiers,
        autopct="%1.1f%%",
        startangle=140,
        colors=colors,
        textprops=dict(color="black", weight="bold"),
        wedgeprops=dict(width=0.4, edgecolor="white")
    )
    ax.set_title("TierFlow: Workload Prefix Tier Distribution", fontsize=13, weight="bold", pad=15)
    plt.tight_layout()
    donut_path = os.path.join(output_dir, "tierflow_tier_distribution.png")
    plt.savefig(donut_path, dpi=300)
    plt.close()
    print(f"[+] Saved Chart 1: {donut_path}")

    # --------------------------------------------------------------------------
    # Chart 2: Cost Comparison across Data Scales (1 TB, 5 TB, 10 TB, 25 TB, 50 TB)
    # --------------------------------------------------------------------------
    scales_tb = [1, 5, 10, 25, 50]
    total = sum(tier_counts.values())
    tier_props = {k: v / total for k, v in tier_counts.items()}

    baseline_costs = []
    int_tiering_costs = []
    tierflow_costs = []

    for tb in scales_tb:
        gb = tb * 1024
        # Assume average object size = 500 KB (common web/logging dataset)
        num_objs = int((gb * 1024 * 1024) / 500)
        c = calculate_costs(gb, num_objs, tier_props)
        baseline_costs.append(c["cost_baseline"])
        int_tiering_costs.append(c["cost_int_tiering"])
        tierflow_costs.append(c["cost_tierflow"])

    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(scales_tb))
    width = 0.25

    ax.bar([i - width for i in x], baseline_costs, width, label="S3 Standard (Baseline)", color="#ef4444")
    ax.bar(x, int_tiering_costs, width, label="AWS Intelligent-Tiering", color="#f59e0b")
    ax.bar([i + width for i in x], tierflow_costs, width, label="TierFlow (Adaptive Prefix)", color="#10b981")

    ax.set_xlabel("Dataset Size (Terabytes)", fontsize=11, weight="bold")
    ax.set_ylabel("Monthly Cost (USD $)", fontsize=11, weight="bold")
    ax.set_title("Monthly Cloud Storage Cost Comparison by Workload Scale", fontsize=13, weight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{tb} TB" for tb in scales_tb])
    ax.legend(frameon=True)
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    bar_path = os.path.join(output_dir, "tierflow_cost_comparison.png")
    plt.savefig(bar_path, dpi=300)
    plt.close()
    print(f"[+] Saved Chart 2: {bar_path}")


def main():
    print("=" * 75)
    print("   TIERFLOW: COST MODEL & PREDICTIVE SAVINGS ANALYSIS")
    print("=" * 75)

    dataset_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "tierflow_simulated_logs.csv")
    records = load_dataset(dataset_path)

    if not records:
        print("[!] No records to process. Exiting.")
        return

    decisions, counts, proportions = evaluate_workload(records)

    print(f"\n[1] Evaluated {len(records)} Dataset Prefixes:")
    for tier, count in counts.items():
        pct = proportions.get(tier, 0) * 100
        print(f"    * {tier:<15}: {count:>2} prefixes ({pct:>5.1f}%)")

    # --------------------------------------------------------------------------
    # Benchmark Evaluation: 10 TB Workload with 2,000,000 Small Objects
    # --------------------------------------------------------------------------
    BENCHMARK_STORAGE_TB = 10.0
    BENCHMARK_STORAGE_GB = BENCHMARK_STORAGE_TB * 1024
    BENCHMARK_OBJECTS = 2_000_000

    results = calculate_costs(BENCHMARK_STORAGE_GB, BENCHMARK_OBJECTS, proportions)

    print("\n[2] Financial Benchmark Simulation (10 TB Workload, 2 Million Objects):")
    print("-" * 75)
    print(f"  * S3 Standard Baseline Monthly Cost : ${results['cost_baseline']:>9.2f} / month")
    print(f"  * AWS Intelligent-Tiering Total     : ${results['cost_int_tiering']:>9.2f} / month")
    print(f"      |-- Includes Object Monitoring Fee: ${results['int_tiering_fee']:>9.2f} ($0.0025/10k objects)")
    print(f"  * TierFlow Adaptive Prefix Total    : ${results['cost_tierflow']:>9.2f} / month")
    print(f"      |-- Includes Athena Query Overhead: ${results['tierflow_overhead']:>9.2f} ($5.00/TB scanned)")
    print("-" * 75)
    print(f"  >>> NET MONTHLY SAVINGS WITH TIERFLOW: ${results['monthly_savings_usd']:>9.2f} ({results['savings_percentage']:.1f}% reduction)")
    print(f"  >>> ANNUALIZED SAVINGS ESTIMATE      : ${results['monthly_savings_usd'] * 12:>9.2f} / year")
    print("=" * 75)

    # --------------------------------------------------------------------------
    # Generate Charts for Slides
    # --------------------------------------------------------------------------
    output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "charts")
    generate_charts(counts, output_dir)
    print("\n[SUCCESS] Analysis complete.")


if __name__ == "__main__":
    main()
