"""
TierFlow — Person C: ML Predictive Tier Model
==============================================
Role: Data / Predictive Analytics Lead (P. Yogesh)
File: scripts/predict_tier_ml.py

Why ML instead of just rules?
    The rule-based decide_storage_class() uses manually chosen thresholds
    (21 days, 60 days, 180 days, 9 reads, 1 read). These were picked by
    intuition. A Decision Tree learns the optimal split points directly
    from the access pattern data — meaning the model can adapt if usage
    patterns change without anyone manually tuning the thresholds.

What this script does:
    1. Loads the 512-prefix simulated access log dataset.
    2. Labels each prefix using the existing rule-based engine (ground truth).
    3. Trains a Decision Tree Classifier on 80% of the data.
    4. Evaluates accuracy and per-class precision/recall on the held-out 20%.
    5. Extracts the learned decision thresholds and compares them to the
       original hardcoded values.
    6. Shows feature importances (which metric matters more: age or reads?).
    7. Predicts tier for 5 new unseen prefixes.
    8. Saves a text representation of the full decision tree.
"""

import os
import sys
import csv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from decide_storage_class import decide_storage_class

try:
    from sklearn.tree import DecisionTreeClassifier, export_text
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
    import numpy as np
except ImportError:
    print("[!] scikit-learn not installed.")
    print("    Run: pip install scikit-learn numpy")
    sys.exit(1)

DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "tierflow_simulated_logs.csv")
TIER_LABELS  = ["STANDARD", "STANDARD_IA", "GLACIER", "DEEP_ARCHIVE"]


# ==============================================================================
# Step 1: Load dataset and generate rule-based labels
# ==============================================================================
def load_and_label(csv_path: str):
    """Load the CSV and auto-label each row using the rule-based engine."""
    X, y = [], []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            days  = int(row["last_accessed_days_ago"])
            count = int(row["access_count_30d"])
            tier  = decide_storage_class(days, count)
            X.append([days, count])
            y.append(tier)
    return np.array(X), np.array(y)


def main():
    print("=" * 70)
    print("   TIERFLOW — DECISION TREE ML TIER PREDICTION MODEL")
    print("   Person C: P. Yogesh | Data & Predictive Analytics Lead")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Load data
    # ------------------------------------------------------------------
    print(f"\n[1] Loading dataset from: {DATASET_PATH}")
    X, y = load_and_label(DATASET_PATH)
    print(f"    Total samples : {len(X)}")
    for tier in TIER_LABELS:
        count = np.sum(y == tier)
        pct   = count / len(y) * 100
        print(f"    {tier:<15}: {count:>3} samples ({pct:.1f}%)")

    # ------------------------------------------------------------------
    # 2. Train / test split (80/20, stratified to preserve tier ratios)
    # ------------------------------------------------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"\n[2] Train/Test Split:")
    print(f"    Training samples : {len(X_train)}")
    print(f"    Test samples     : {len(X_test)}")

    # ------------------------------------------------------------------
    # 3. Train the Decision Tree
    # ------------------------------------------------------------------
    print("\n[3] Training Decision Tree Classifier...")
    model = DecisionTreeClassifier(
        criterion="gini",
        max_depth=6,          # Deep enough to capture all 4 tiers
        min_samples_leaf=3,   # Avoid overfitting single edge cases
        random_state=42
    )
    model.fit(X_train, y_train)
    print("    Training complete.")

    # ------------------------------------------------------------------
    # 4. Evaluate on held-out test set
    # ------------------------------------------------------------------
    y_pred    = model.predict(X_test)
    accuracy  = accuracy_score(y_test, y_pred)

    print(f"\n[4] Model Evaluation on Test Set ({len(X_test)} samples):")
    print("-" * 70)
    print(f"    Overall Accuracy: {accuracy * 100:.1f}%")
    print()
    print(classification_report(y_test, y_pred, target_names=TIER_LABELS, zero_division=0))

    print("    Confusion Matrix (rows=actual, cols=predicted):")
    cm = confusion_matrix(y_test, y_pred, labels=TIER_LABELS)
    header = f"    {'':>15} " + "  ".join(f"{t[:8]:>8}" for t in TIER_LABELS)
    print(header)
    for i, row in enumerate(cm):
        row_str = "  ".join(f"{v:>8}" for v in row)
        print(f"    {TIER_LABELS[i]:<15} {row_str}")

    # ------------------------------------------------------------------
    # 5. Feature Importances
    # ------------------------------------------------------------------
    features     = ["last_accessed_days_ago", "access_count_30d"]
    importances  = model.feature_importances_
    print(f"\n[5] Feature Importances (which metric drives the decision more?):")
    print("-" * 70)
    for feat, imp in zip(features, importances):
        bar = "#" * int(imp * 40)
        print(f"    {feat:<25}: {imp:.4f}  |{bar}|")
    dominant = features[int(np.argmax(importances))]
    print(f"\n    --> '{dominant}' is the dominant predictor of storage tier.")

    # ------------------------------------------------------------------
    # 6. Learned Thresholds vs Hardcoded Rules
    # ------------------------------------------------------------------
    print(f"\n[6] Learned Decision Thresholds vs Original Hardcoded Rules:")
    print("-" * 70)
    print(f"    {'Threshold':<30} {'Hardcoded Rule':<22} {'ML Learned'}")
    print(f"    {'-'*29} {'-'*21} {'-'*20}")

    # Extract unique split thresholds from the tree for each feature
    tree        = model.tree_
    feat_idx    = tree.feature
    thresholds  = tree.threshold

    days_splits  = sorted(set(
        round(thresholds[i], 1)
        for i in range(len(feat_idx))
        if feat_idx[i] == 0 and thresholds[i] > 0
    ))
    reads_splits = sorted(set(
        round(thresholds[i], 1)
        for i in range(len(feat_idx))
        if feat_idx[i] == 1 and thresholds[i] >= 0
    ))

    hardcoded_days  = [21, 60, 180]
    hardcoded_reads = [1, 9]

    for i, hd in enumerate(hardcoded_days):
        ml_val = days_splits[i] if i < len(days_splits) else "N/A"
        print(f"    {'Days threshold ' + str(i+1):<30} {str(hd) + ' days':<22} {str(ml_val) + ' days'}")

    for i, hr in enumerate(hardcoded_reads):
        ml_val = reads_splits[i] if i < len(reads_splits) else "N/A"
        print(f"    {'Read count threshold ' + str(i+1):<30} {str(hr) + ' reads':<22} {str(ml_val) + ' reads'}")

    print()
    print("    --> If ML thresholds differ from hardcoded ones, the ML model")
    print("        has found better boundaries based on the actual data distribution.")

    # ------------------------------------------------------------------
    # 7. Predict 5 new unseen prefixes
    # ------------------------------------------------------------------
    print(f"\n[7] Predicting Tier for 5 New Unseen Prefixes:")
    print("-" * 70)
    new_prefixes = [
        ("hr/reports/2026-Q1/",       2,   80),   # very hot
        ("finance/raw-data/2025-Q3/", 35,   6),   # aging, moderate reads
        ("ops/logs/2024-Q2/",         90,   1),   # old, rare reads
        ("sales/raw-data/2022-Q4/",  420,   0),   # very old, never accessed
        ("engineering/logs/2025-Q4/", 18,  12),   # recent but low reads
    ]
    print(f"    {'Prefix':<35} {'Days':>6} {'Reads':>6}  {'Rule-Based':<16} {'ML Predicted'}")
    print(f"    {'-'*34} {'-'*6} {'-'*6}  {'-'*15} {'-'*12}")
    for prefix, days, reads in new_prefixes:
        rule_tier = decide_storage_class(days, reads)
        ml_tier   = model.predict([[days, reads]])[0]
        match     = "==" if rule_tier == ml_tier else "!= <-- DIFFERS"
        print(f"    {prefix:<35} {days:>6} {reads:>6}  {rule_tier:<16} {ml_tier}  {match}")

    # ------------------------------------------------------------------
    # 8. Save full decision tree as text
    # ------------------------------------------------------------------
    tree_text_path = os.path.join(os.path.dirname(__file__), "..", "data", "decision_tree.txt")
    tree_text = export_text(model, feature_names=features)
    with open(tree_text_path, "w") as f:
        f.write("TierFlow — Learned Decision Tree\n")
        f.write("=" * 60 + "\n")
        f.write("Features: last_accessed_days_ago, access_count_30d\n")
        f.write("Classes : STANDARD, STANDARD_IA, GLACIER, DEEP_ARCHIVE\n")
        f.write("=" * 60 + "\n\n")
        f.write(tree_text)
    print(f"\n[8] Full decision tree saved to: {tree_text_path}")
    print("    Open this file to see every split the ML model learned.")

    print("\n" + "=" * 70)
    print("   [SUCCESS] ML model training and evaluation complete.")
    print(f"   Accuracy: {accuracy*100:.1f}% on held-out test data")
    print("=" * 70)


if __name__ == "__main__":
    main()
