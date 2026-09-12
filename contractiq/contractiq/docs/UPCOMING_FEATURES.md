# ContractIQ — Upcoming Features

## Pending

- [ ] **Adaptive-RAG complexity routing** — simple vs multi-hop retrieval depth
- [ ] **Live web-search recovery** — when action is `WEB_SEARCH`
- [ ] **RAG efficiency upgrades** — embedding cache, ANN index, fewer NLI calls (pipeline works but is not efficient yet)
- [ ] **Multi-benchmark evaluation** — EM/F1, faithfulness on public QA sets
- [ ] **Latency & cost study** — corrective loop vs vanilla RAG

## Implemented (do not re-list as pending)

- Confidence-gated passage grading (CORRECT / AMBIGUOUS / INCORRECT)
- Corrective actions ACCEPT / RE_RETRIEVE / WEB_SEARCH (stub)
- Document upload + QA UI, history, stats
