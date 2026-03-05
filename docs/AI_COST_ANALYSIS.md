# LegacyLens — AI Cost Analysis

## Development Spend

### One-Time Ingestion Costs

| Operation | Model | Input | Est. Tokens | Cost |
|-----------|-------|-------|-------------|------|
| Embedding generation | text-embedding-3-small | ~2,294 Fortran files, ~977K LOC, ~3,500–4,000 chunks | ~5M tokens | ~$0.10 |
| **Total ingestion** | | | | **~$0.10** |

Ingestion is a one-time cost. Re-ingestion (if schema changes or new files are added) costs the same.

### Development & Testing

| Activity | Model | Est. Queries | Est. Tokens | Cost |
|----------|-------|-------------|-------------|------|
| Query testing (embeddings) | text-embedding-3-small | ~200 queries | ~50K tokens | ~$0.001 |
| Query testing (LLM answers) | Claude Haiku 4.5 | ~200 queries | ~400K input, ~200K output | ~$1.40 |
| Code understanding testing | Claude Haiku 4.5 | ~100 calls (7 features) | ~250K input, ~150K output | ~$1.00 |
| Query expansion testing | Claude Haiku 4.5 | ~100 calls | ~30K input, ~20K output | ~$0.13 |
| LLM reranking testing | Claude Haiku 4.5 | ~200 calls | ~300K input, ~40K output | ~$0.50 |
| **Total development** | | | | **~$3.03** |

### Total Development Cost: ~$3.13

---

## Per-Query Cost Breakdown

Each user query incurs costs across multiple API calls. Reranking is enabled by default; query expansion is opt-in.

| Step | Model | Input Tokens | Output Tokens | Cost |
|------|-------|-------------|---------------|------|
| Query embedding | text-embedding-3-small | ~20 | — | $0.0000004 |
| Query expansion (opt-in) | Claude Haiku 4.5 | ~50 | ~60 | $0.00035 |
| LLM reranking (default on) | Claude Haiku 4.5 | ~1,500 | ~50 | $0.0018 |
| Answer generation | Claude Haiku 4.5 | ~2,000 (context + query) | ~400 | $0.004 |
| **Per query (rerank, no expansion)** | | | | **~$0.006** |
| **Per query (rerank + expansion)** | | | | **~$0.006** |
| **Per query (no rerank, no expansion)** | | | | **~$0.004** |

### Code Understanding Costs Per Call

| Feature | Max Tokens | Est. Input | Est. Output | Cost |
|---------|-----------|------------|-------------|------|
| Explain | 768 | ~1,500 | ~500 | ~$0.004 |
| ELI5 | 512 | ~1,500 | ~400 | ~$0.004 |
| Document | 1536 | ~1,500 | ~1,000 | ~$0.007 |
| Translate | 1536 | ~1,500 | ~1,000 | ~$0.007 |
| Use Cases | 512 | ~1,500 | ~400 | ~$0.004 |
| Dependencies | — | DB only | DB only | ~$0.00 |
| Similar | — | DB only | DB only | ~$0.00 |

Cached results (LRU, 512 entries) incur zero additional cost on repeat calls.

---

## Production Cost Projections

Assuming 5 queries per user per day (rerank enabled by default), with 30% using query expansion and 30% using a code understanding feature:

| Scale | Daily Queries | Monthly LLM Cost | Monthly DB Cost | Monthly Total |
|-------|--------------|-------------------|-----------------|---------------|
| 10 users | 50 | ~$10 | $0 (free tier) | **~$10** |
| 100 users | 500 | ~$100 | $0 (free tier) | **~$100** |
| 1,000 users | 5,000 | ~$1,000 | ~$25 | **~$1,025** |
| 10,000 users | 50,000 | ~$10,000 | ~$100 | **~$10,100** |

### Infrastructure Costs (not usage-based)

| Service | Free Tier Limit | Paid Tier |
|---------|----------------|-----------|
| Vercel (frontend) | 100GB bandwidth/mo | $20/mo |
| Fly.io (backend) | 3 shared VMs | $5–15/mo |
| Supabase (DB) | 500MB storage, 2GB transfer | $25/mo |

---

## Cost Optimization Opportunities

1. **Caching** — Three LRU caches are already in place (response: 512 entries, embedding: 256 entries, understanding: 512 entries). At 100 users, if 30% of queries repeat, saves ~$30/month.

2. **Selective reranking** — Disable reranking for simple routine lookups (exact name matches) where keyword search already returns the right result. Saves ~$0.002/query for those cases.

3. **Smaller context windows** — Currently sending top-5 chunks (~2K tokens). Reducing to top-3 for simple queries would cut generation cost by ~40%.

4. **Model tiering** — Use Haiku for simple queries, Sonnet only for complex architectural questions. Could be routed by query complexity classifier.

5. **Batch embedding upgrades** — Switching to Voyage code-3 ($0.18/1M tokens) would cost ~$0.90 for re-ingestion but could improve retrieval precision enough to reduce the number of chunks needed in context.

6. **Brief mode adoption** — Brief mode (256 max tokens vs. 512) reduces generation cost by ~50% for users who prefer concise answers.

---

## Summary

| Metric | Value |
|--------|-------|
| Total development spend | ~$3.13 |
| Cost per query (with rerank) | ~$0.006 |
| Cost per query (without rerank) | ~$0.004 |
| Break-even at 100 users (vs. manual code review) | < $100/month |
| Primary cost driver | LLM answer generation + reranking (~95% of per-query cost) |
