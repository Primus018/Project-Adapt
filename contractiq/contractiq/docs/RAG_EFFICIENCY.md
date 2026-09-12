# ContractIQ — RAG Efficiency Notes

## Current behavior

The corrective RAG loop is:

`retrieve → grade each passage → ACCEPT | RE_RETRIEVE | WEB_SEARCH → generate answer`

This is **functionally working** for contract QA demos.

## Why it is not efficient yet

1. **Demo / lexical path** scans all chunks with token overlap (O(n) per query), no inverted index.
2. **Live path** may re-encode the query inside each passage grade and run NLI per passage.
3. **RE_RETRIEVE** expands the query and re-grades a larger candidate set (extra latency).
4. **WEB_SEARCH** is a stub — no external retrieval, so “recovery” does not add new evidence.
5. **Answer generation** in demo is extractive (fast) but weaker than an LLM; live Ollama `llama3.1:8b` is slower and depends on local GPU/CPU.

## Planned efficiency upgrades (pending)

- Cache query embedding once per request
- Batch NLI / grade only top-k passages
- Use FAISS / ANN for retrieval instead of brute-force similarity
- Skip second full grade pass when RE_RETRIEVE returns near-duplicates
- Measure and report latency breakdown (retrieve / grade / generate)

## LLM used for answers

| Mode | Generator |
|------|-----------|
| `DEMO_MODE=1` (default demo) | **No LLM** — best overlapping sentence from context |
| `DEMO_MODE=0` + Ollama up | **`llama3.1:8b`** via Ollama chat API |
| Ollama down | Extractive fallback |

Retriever/grader models (when not in demo): **BAAI/bge-small-en-v1.5** + **cross-encoder/nli-deberta-v3-base**.
