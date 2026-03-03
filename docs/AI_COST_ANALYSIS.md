# LegacyLens — AI Cost Analysis

## Development Spend

### One-Time Ingestion Costs

| Operation | Model | Input | Est. Tokens | Cost |
|-----------|-------|-------|-------------|------|
| Embedding generation | text-embedding-3-small | ~670 Fortran files, ~100K LOC | ~2M tokens | ~$0.04 |
| **Total ingestion** | | | | **~$0.04** |

Ingestion is a one-time cost. Re-ingestion (if schema changes or new files are added) costs the same.

### Development & Testing

| Activity | Model | Est. Queries | Est. Tokens | Cost |
|----------|-------|-------------|-------------|------|
| Query testing (embeddings) | text-embedding-3-small | ~200 queries | ~50K tokens | ~$0.001 |
| Query testing (LLM answers) | Claude Haiku 4.5 | ~200 queries | ~400K input, ~200K output | ~$1.40 |
| Code understanding testing | Claude Haiku 4.5 | ~50 calls | ~150K input, ~75K output | ~$0.53 |
| Query expansion testing | Claude Haiku 4.5 | ~100 calls | ~30K input, ~20K output | ~$0.13 |
| **Total development** | | | | **~$2.10** |

### Total Development Cost: ~$2.14

---

## Per-Query Cost Breakdown

Each user query incurs costs across multiple API calls:

| Step | Model | Input Tokens | Output Tokens | Cost |
|------|-------|-------------|---------------|------|
| Query embedding | text-embedding-3-small | ~20 | — | $0.0000004 |
| Query expansion (optional) | Claude Haiku 4.5 | ~50 | ~60 | $0.00035 |
| Answer generation | Claude Haiku 4.5 | ~2,000 (context + query) | ~400 | $0.004 |
| **Per query (no expansion)** | | | | **~$0.004** |
| **Per query (with expansion)** | | | | **~$0.005** |

Code understanding features (explain, document) add ~$0.003–$0.006 per call. Dependency and similarity searches are database-only (no LLM cost).

---

## Production Cost Projections

Assuming 5 queries per user per day, with 30% using query expansion and 20% using a code understanding feature:

| Scale | Daily Queries | Monthly LLM Cost | Monthly DB Cost | Monthly Total |
|-------|--------------|-------------------|-----------------|---------------|
| 10 users | 50 | ~$6 | $0 (free tier) | **~$6** |
| 100 users | 500 | ~$60 | $0 (free tier) | **~$60** |
| 1,000 users | 5,000 | ~$600 | ~$25 | **~$625** |
| 10,000 users | 50,000 | ~$6,000 | ~$100 | **~$6,100** |

### Infrastructure Costs (not usage-based)

| Service | Free Tier Limit | Paid Tier |
|---------|----------------|-----------|
| Vercel (frontend) | 100GB bandwidth/mo | $20/mo |
| Fly.io (backend) | 3 shared VMs | $5–15/mo |
| Supabase (DB) | 500MB storage, 2GB transfer | $25/mo |

---

## Cost Optimization Opportunities

1. **Embedding caching** — Cache query embeddings (LRU) to avoid re-embedding repeated queries. Saves ~$0.0000004/cached query (minimal, but reduces latency).

2. **Response caching** — Cache LLM responses for identical queries with TTL. At 100 users, if 30% of queries repeat, saves ~$18/month.

3. **Smaller context windows** — Currently sending top-5 chunks (~2K tokens). Reducing to top-3 for simple queries would cut generation cost by ~40%.

4. **Model tiering** — Use Haiku for simple queries, Sonnet only for complex architectural questions. Could be routed by query complexity classifier.

5. **Batch embedding upgrades** — Switching to Voyage code-3 ($0.18/1M tokens) would cost ~$0.36 for re-ingestion but could improve retrieval precision enough to reduce the number of chunks needed in context.

---

## Summary

| Metric | Value |
|--------|-------|
| Total development spend | ~$2.14 |
| Cost per query | ~$0.004–0.005 |
| Break-even at 100 users (vs. manual code review) | < $60/month |
| Primary cost driver | LLM answer generation (~80% of per-query cost) |
