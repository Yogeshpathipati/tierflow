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
| **Daivik**  | Listing S3 objects by prefix, rule-based tiering decisions, executing `copy_object` moves |
| **Irfan**  | S3 access logging, lambda function wrapping, athena access frequency logging |
| **P. Yogesh**  | Access-pattern data analysis, real bucket testing & validation, literature survey, SDG mapping |
| **Yamin** | Testing of files against real bucket, literature survey, lambda function design |

## Repo layout

```
tierflow/
├── src/
│   ├── list_objects.py          # lists S3 objects under a prefix (paginated)
│   ├── decide_storage_class.py  # rule-based tiering decision logic
│   ├── simulate_logs.py         # generates simulated access-pattern CSV data
│   ├── athena_parser.py         # queries real S3 access logs via AWS Athena
│   ├── move_objects.py          # executes in-place copy_object tier transitions
│   └── lambda_function.py       # AWS Lambda handler orchestrating the pipeline
├── tests/
│   ├── test_list_objects.py     # moto-based unit tests (no real AWS calls)
│   └── conftest.py
├── data/
│   ├── tierflow_simulated_logs.csv   # simulated per-prefix access log
│   ├── sample-files/                 # sample files used for manual S3 testing
│   └── real bucket testing results/  # query outputs from live Athena/S3 log testing
├── scripts/
│   └── manual_smoke_test.py     # quick manual script against a real bucket (needs live AWS creds)
└── requirements.txt
```

## Status: what's done

- **`list_objects_by_prefix()`** (`src/list_objects.py`) — paginated
  `list_objects_v2` call, returns key/size/last-modified/storage class/etag
  per object. Storage class is normalized for `STANDARD` objects. Covered
  by 6 passing moto-based unit tests. Also verified manually against a real
  bucket (`tierflow-daivik-test`, `ap-south-1`).
- **`decide_storage_class()`** (`src/decide_storage_class.py`) — 4-tier
  rule cascade (`DEEP_ARCHIVE` → `GLACIER` → `STANDARD_IA` → `STANDARD`)
  based on `last_accessed_days_ago` and `access_count_30d`. Run and
  verified against `data/tierflow_simulated_logs.csv`, including boundary
  cases sitting exactly on the rule thresholds.
- **S3 Server Access Logging & Athena Parser** (`src/athena_parser.py`) —
  S3 Server Access Logging enabled on `tierflow-daivik-test`, delivering logs to
  `tierflow-daivik-logs`. Athena SQL parser queries `s3_access_logs` and
  aggregates `last_accessed_days_ago` and `access_count_30d` for each prefix.
- **`copy_object` tiering & real bucket validation** — confirmed working
  against a real bucket: objects successfully moved to `STANDARD_IA` with the
  storage class change verified afterward (see `scripts/manual_smoke_test.py`
  and Athena log exports in `data/real bucket testing results/`).
- **Simulated log generation** (`src/simulate_logs.py`) — produces
  realistic per-prefix access data (hot/warm/cool/cold/frozen/never, plus
  threshold edge cases) so tiering logic can be developed and tested
  without waiting on slow real S3 access log delivery.
- **AWS setup** — standalone AWS account (a prior org-managed account was
  blocked by a Service Control Policy that overrides IAM permissions), IAM
  user `daivik-tierflow`, CLI configured for `ap-south-1`, bucket
  `tierflow-daivik-test` live with `raw-data/`, `logs/`, and `project-data/`
  test prefixes.
- **Serverless orchestration scaffold** (`src/lambda_function.py`, `src/move_objects.py`) —
  initial Lambda wrapper and object mover drafted.
- **Academic write-up** — Problem Identification, Motivation, Literature
  Survey, Objectives, Proposed Architecture, and SDG Mapping sections are
  complete.

## Status: what's left

- **Improve mover robustness** (`src/move_objects.py`) — reuse
  `list_objects_by_prefix()` for full pagination support beyond 1,000 keys,
  and parameterize the bucket name instead of hardcoding.
- **EventBridge trigger & IAM role** — configure an automated schedule
  (e.g., daily/weekly cron) and deploy the Lambda function with least-privilege
  execution policies.
- **Extended test coverage** — add unit tests for `decide_storage_class.py` and
  `athena_parser.py` to complement existing Moto tests.
- **Implementation progress documentation** — write up what's built so far
  for the academic review, tying live empirical benchmarks back to design goals.

## Getting started 

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
