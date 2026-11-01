# Data Archaeology Report
*Run inv_20261101_154009 · 2026-11-01T15:40:44*
**Objective:** Investigate how these datasets are connected and find inconsistencies

## Datasets
- ds_001 customers.csv: 3 rows, 6 cols, quality 100.0
- ds_002 transactions.csv: 4 rows, 3 cols, quality 100.0
- ds_003 customers_v2.csv: 5 rows, 6 cols, quality 98.0

## Relationships (inferred)
- [supported, confidence 1.0] ds_001.customer_id references ds_003.customer_id (one_to_one)
- [supported, confidence 1.0] ds_002.client_ref references ds_003.customer_id (one_to_many)
- [partially_supported, confidence 0.86] ds_003.email references ds_001.email (one_to_many) | 1 child values have no parent, e.g. ['kiran@mail.com']
- [partially_supported, confidence 0.72] ds_003.customer_id references ds_001.customer_id (one_to_one) | 2 child values have no parent, e.g. ['104', '105']
- [partially_supported, confidence 0.825] ds_002.client_ref references ds_001.customer_id (one_to_many) | 1 child values have no parent, e.g. ['104']; Those values exist in ds_003.customer_id; possibly records added after the parent file was exported

## Lineage (inferred, not confirmed provenance)
- ds_001 -> ds_003 (inferred_derivation, relatedness 0.987, direction confidence 0.65): 2 keys only in ds_003, e.g. ['104', '105'] (additions if ds_003 is later); row count 3 -> 5; values differ on shared records: city=1; quality score 100.0 -> 98.0
- ds_002.client_ref aligns with ds_003.customer_id (1.0) more than ds_001.customer_id (0.75): child records appear to have been created against the better-matching parent version (inferred)
- Inferred from file contents and file names only. Direction is not proven: no ETL logs, SQL or reliable timestamps are available (observed lineage: none).

## Entities
- [same_entity, confidence 0.941] E-001: 3 records across ['ds_001', 'ds_003'] may be one entity
- [same_entity, confidence 1.0] E-002: 2 records across ['ds_001', 'ds_003'] may be one entity
- [same_entity, confidence 1.0] E-003: 2 records across ['ds_001', 'ds_003'] may be one entity

## Contradictions
- [unresolved] customers.csv and customers_v2.csv disagree on 'city' for 1 of 3 shared records | Differences may be updates: customers_v2.csv looks newer by filename (inferred, low confidence; file timestamps are not preserved on upload).; key 102: 'Surat' vs 'Vadodara' (other fields agreeing 4/4)

## Anomalies
- [high] invalid_date in ds_003.created_at: 1 (['2023-13-45'])
- [high] negative_amount in ds_003.total_spent: 1 (['-50.0'])
- [medium] broken_reference in ds_002.client_ref: 1 (['104'])

## Unresolved questions
- 1 values in ds_003.email have no parent anywhere: ['kiran@mail.com']
- Which file is the authoritative parent for ds_002.client_ref? Orphans ['104'] exist in ds_003.customer_id.
- Human review needed: customers.csv and customers_v2.csv disagree on 'city' for 1 of 3 shared records

## Recommended actions
- Confirm the authoritative parent for ds_003.email; unmatched values ['kiran@mail.com'].
- Confirm the authoritative parent for ds_002.client_ref; unmatched values ['104'].
- Decide the source of truth for: customers.csv and customers_v2.csv disagree on 'city' for 1 of 3 shared records.
- Fix or explain invalid_date in ds_003.created_at: ['2023-13-45'].
- Fix or explain negative_amount in ds_003.total_spent: ['-50.0'].
- Confirm ds_001 -> ds_003 with ETL logs or the data owner.

## Method
- 13 tool calls; every number comes from deterministic Python tools (evidence ids ev_001..ev_013).
- Planner: rules (no LLM key configured).
- All findings are inferred; none are human-verified.
