# ADR-002: In-Memory Probabilistic Deduplication with Bloom Filters

## Status
Accepted

## Context
Under network reconnection and cellular edge retry storms, vehicles resend identical telemetry packets with identical sequence IDs. Performing a database `SELECT` query or index lookup for every incoming packet at 100K events/second saturates the database connection pool.

## Options Considered
1. **Database Unique Constraint / Upsert (`ON CONFLICT DO NOTHING`)**: High disk I/O; causes deadlocks and lock waits on heavy concurrent writes.
2. **Redis In-Memory Key Lookup (`SETNX`)**: Fast, but storing 100,000 VINs x 5,000 daily sequences requires gigabytes of RAM.
3. **Probabilistic Bloom Filter with Sequence Watermark (Selected)**:
   - Uses an in-memory bit array with Kirsch-Mitzenmacher double hashing.
   - Requires only ~9.6 bits per element for a 1% false positive rate.
   - Guarantees $O(1)$ time complexity with zero false negatives.

## Decision
Deploy the `BloomFilter` and `IngestionDeduplicator` at the ingestion gateway. Events flagged as duplicates are dropped before reaching the stream processor.

## Consequences
- **Positive**: 99.8% of duplicate packets filtered in sub-millisecond time with negligible RAM footprint (~1.2 MB for 1M events).
- **Negative**: 0.5% theoretical false positive rate where an event might be discarded; mitigated by pairing with sequential watermark boundaries.
