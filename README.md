# TierFlow

An adaptive S3 storage tiering engine. TierFlow watches how S3 objects are
accessed and moves them between storage classes (`STANDARD`, `STANDARD_IA`,
`GLACIER`, `DEEP_ARCHIVE`) based on **prefix-level** access patterns, rather
than monitoring every object individually. That prefix-level reasoning is
what differentiates TierFlow from AWS S3 Intelligent-Tiering, and it works
*alongside* S3 lifecycle policies, not as a replacement for them.

This is a semester project for Advanced Cloud Computing.

## Team & roles

| Role | Responsibility |
|---|---|
| **Daivik** (this codebase) | Listing S3 objects by prefix, rule-based tiering decisions, executing `copy_object` moves |

## Repo layout

```
tierflow/
├── src/
│   ├── list_objects.py          # lists S3 objects under a prefix (paginated)
│   ├── decide_storage_class.py  # rule-based tiering decision logic
│   └── simulate_logs.py         # generates simulated access-pattern CSV data
├── tests/
│   ├── test_list_objects.py     # moto-based unit tests (no real AWS calls)
│   └── conftest.py
├── data/
│   ├── tierflow_simulated_logs.csv   # simulated per-prefix access log
│   └── sample-files/                 # tiny sample files used for manual S3 testing
├── scripts/
│   └── manual_smoke_test.py     # quick manual script against a real bucket (needs live AWS creds)
└── requirements.txt
```

## Status: what's done

- **`list_objects_by_prefix()`** (`src/list_objects.py`) — paginated
  `list_objects_v2` call, returns key/size/last-modified/storage class/etag
  per object. Covered by 6 passing moto-based unit tests. Also verified
  manually against a real bucket (`tierflow-daivik-test`, `ap-south-1`).
- **`decide_storage_class()`** (`src/decide_storage_class.py`) — 4-tier
  rule cascade (`DEEP_ARCHIVE` → `GLACIER` → `STANDARD_IA` → `STANDARD`)
  based on `last_accessed_days_ago` and `access_count_30d`. Run and
  verified against `data/tierflow_simulated_logs.csv`, including boundary
  cases sitting exactly on the rule thresholds.
- **`copy_object` tiering** — confirmed working against a real bucket:
  objects successfully moved to `STANDARD_IA` with the storage class
  change verified afterward (see `scripts/manual_smoke_test.py` for the
  pattern).
- **Simulated log generation** (`src/simulate_logs.py`) — produces
  realistic per-prefix access data (hot/warm/cool/cold/frozen/never, plus
  threshold edge cases) so tiering logic can be developed and tested
  without waiting on slow real S3 access log delivery.
- **AWS setup** — standalone AWS account (a prior org-managed account was
  blocked by a Service Control Policy that overrides IAM permissions), IAM
  user `daivik-tierflow`, CLI configured for `ap-south-1`, bucket
  `tierflow-daivik-test` live with `raw-data/` and `logs/` test prefixes.
- **Academic write-up** — Problem Identification, Motivation, Literature
  Survey, Objectives, Proposed Architecture, and SDG Mapping sections are
  complete (not in this repo yet — ping Person B if you need them).

## Status: what's left

- **Enable S3 Server Access Logging** on `tierflow-daivik-test`, delivering
  to a separate logs bucket (`tierflow-daivik-logs`).
- **Real-log parser** — a function to turn raw S3 access log lines into the
  same per-prefix schema `decide_storage_class()` already consumes
  (`prefix`, `last_accessed_days_ago`, `access_count_30d`), so we can swap
  simulated data for the real thing.
- **Lambda wrapper** — package `list_objects_by_prefix()` +
  `decide_storage_class()` + the `copy_object` mover into a Lambda function.
  This needs to be coordinated with Person A's architecture (trigger,
  schedule, IAM role for the function).
- **Implementation progress documentation** — write up what's built so far
  for the academic review, tying this code back to the design docs.

## Getting started (for teammates)

```bash
git clone <repo-url>
cd tierflow
pip install -r requirements.txt

# run the unit tests (safe - uses moto, makes no real AWS calls)
python -m pytest tests/ -v

# run the tiering decision logic against the simulated data
python -c "import sys; sys.path.insert(0, 'src'); import decide_storage_class as m; m.run_against_csv('data/tierflow_simulated_logs.csv')"

# regenerate the simulated log data if you want different scenarios
python src/simulate_logs.py
```

To run anything against the **real** AWS bucket
(`scripts/manual_smoke_test.py`, or `list_objects.py`'s `__main__` block),
you'll need your own AWS credentials configured (`aws configure`) with
access to the `tierflow-daivik-test` bucket in `ap-south-1`. **Never commit
AWS credentials to this repo** — `.gitignore` already blocks common
credential file patterns, but double-check before every push.

## Design notes

- Tiering decisions operate at the **prefix/group level**, not per
  individual object — this is intentional and is the key differentiator
  from S3 Intelligent-Tiering.
- Rule thresholds in `decide_storage_class()` (21/60/180 days,
  1/9 access counts) are a starting point tuned for the demo dataset —
  revisit these against the literature survey / assumptions section before
  the final writeup.
- `list_objects_by_prefix()` normalizes S3's quirky `StorageClass` field
  (S3 omits it entirely for `STANDARD` objects) so downstream code always
  has a value to compare against.
