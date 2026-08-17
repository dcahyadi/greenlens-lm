# Design & Testing Document

## 1. System Overview

GreenLens LM is a full-stack RAG (Retrieval-Augmented Generation) application that allows users to ask natural language questions about Indonesia's green economy, environmental regulations, and energy transition policies. It answers using a curated corpus of 18 official government documents, always citing the source regulation and year.

### 1.1 Full System Architecture

```
┌──────────────┐     ┌───────────────────────────────────────────────────┐
│     User     │────>│              React Frontend                       │
│  Web browser │     │  Chat UI · citations · topic filter · EN/ID       │
└──────────────┘     └───────────────────────────┬───────────────────────┘
                                                 │ HTTP /api/query
                                                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Python 3.14)                        │
│                                                                        │
│  ┌────────────────────┐     ┌────────────────────────────────────┐     │
│  │    API routers     │────>│           RAG chain                │     │
│  │  /query /ingest    │     │  LCEL chain (RunnablePassthrough)  │     │
│  │  /health           │     │  MMR retrieval · k=5               │     │
│  └────────────────────┘     │  context + chat history in prompt  │     │
│                             │  retry w/ backoff (tenacity)       │     │
│                             │  metadata category filter          │     │
│                             └────────────────────────────────────┘     │
│                                                                        │
└───────────────┬─────────────────────────┬───────────────┬─────────────-┘
                │                         │               │
                ▼                         ▼               ▼
┌──────────────────────┐  ┌─────────────────────┐  ┌───────────────┐
│      ChromaDB        │  │     Embeddings      │  │     LLM       │
│  Embedded vector     │  │  BAAI/bge-m3        │  │  OpenRouter   │
│  store (local /      │  │  multilingual EN+ID │  │  gpt-oss-20b  │
│  Render disk)        │  └─────────────────────┘  └───────────────┘
└──────────┬───────────┘
           │  (one-time offline ingestion)
           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                 Document Ingestion Pipeline (offline)                │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐   │
│  │    PDF loader    │  │  Text splitter   │  │   Embed + index   │   │
│  │  PyPDF/PyMuPDF   │─>│  chunk+overlap   │─>│  write to ChromaDB│   │
│  └──────────────────┘  └──────────────────┘  └───────────────────┘   │
│                                                                      │
│  metadata.py registry · FAQ = 512 tok · regulations = 1000 tok       │
│  18 files · 6 categories · bilingual EN + ID                         │
└──────────────────────────────────────────────────────────────────────┘

Supporting:
  CI/CD  │ GitHub Actions → lint + test + build → auto-deploy to Render
  Eval   │ evaluation/eval_suite.py → keyword score + source accuracy
```

### 1.2 Document Corpus

| Category | Regulation | Year | Lang |
|---|---|---|---|
| Climate commitment | Enhanced NDC 2022 | 2022 | EN |
| Climate commitment | Updated NDC 2021 | 2021 | EN |
| Energy transition | JETP CIPP 2023 | 2023 | EN |
| Energy transition | JETP Progress Report 2025 | 2025 | EN |
| Energy transition | JETP Progress Report 2025 | 2025 | ID |
| Carbon market | Perpres 98/2021 | 2021 | EN |
| Carbon market | Perpres 98/2021 | 2021 | ID |
| Carbon market | Perpres 110/2025 | 2025 | ID |
| Carbon market | POJK 14/2023 (IDX Carbon) | 2023 | ID |
| Environmental law | PermenLHK 4/2021 (AMDAL) | 2021 | ID |
| Environmental law | PermenLHK 21/2022 (NEK) | 2022 | ID |
| Environmental law | PP 22/2021 (AMDAL framework) | 2021 | ID |
| Renewable energy | Perpres 112/2022 (EBT acceleration) | 2022 | ID |
| Renewable energy | Permen ESDM 2/2024 (PLTS Atap) | 2024 | ID |
| Green finance | TKBI Version 3 2026 | 2026 | EN |
| Green finance | TKBI Version 3 2026 | 2026 | ID |
| Green finance | TKBI Fact Sheets | 2026 | EN |
| Green finance | TKBI FAQ | 2026 | EN |

**Total: 18 files across 6 categories** (Updated NDC 2021 is in corpus with status `superseded` retained for historical context).

---

## 2. Architecture Decisions

### 2.1 RAG over Fine-tuning

**Decision:** Use retrieval-augmented generation rather than fine-tuning a model on the document corpus.

**Reason:** The documents are authoritative government regulations requiring exact, citable answers. RAG preserves the original text and lets us attribute every answer to a specific regulation name and page. Fine-tuning would bake knowledge into model weights with no traceability, and would require expensive retraining every time a regulation is updated (e.g., when Perpres 110/2025 superseded parts of Perpres 98/2021).

### 2.2 ChromaDB in Embedded Mode

**Decision:** Use ChromaDB as an embedded vector store (runs inside the FastAPI process, persists to a local folder) rather than a hosted vector database like Pinecone or Weaviate.

**Reason:**
- Zero infrastructure cost, no separate server or API key needed
- Data stays local during development; on Render it uses a persistent disk
- Simple Python API integrates directly with LangChain
- The corpus (18 documents, ~50k chunks) is small enough that a local store is more than sufficient

**Trade-off:** Not suitable for very large corpora or multi-instance deployments requiring shared state.

### 2.3 BAAI/bge-m3 Embeddings

**Decision:** Use `BAAI/bge-m3` instead of the more common `all-MiniLM-L6-v2`.

**Reason:** The document corpus is bilingual, NDC and JETP documents are in English while KLHK, ESDM, OJK, and carbon regulations are in Bahasa Indonesia. `bge-m3` is a multilingual model that handles both languages in the same vector space, so a user asking in Indonesian retrieves from Indonesian-language documents correctly, and vice versa.

**Trade-off:** Larger model (2.27GB in fp32, not ~570MB as originally estimated before checking the actual downloaded weight file size) vs `all-MiniLM-L6-v2` (~90MB), longer first-load time. Mitigated by pre-downloading at Docker build time (see `Dockerfile`). This size later caused a real production issue — see the ablation study below.

**Ablation study: smaller embedding models for free-tier RAM constraints:**

Render's free-tier web services are limited to 512MB RAM. Loading `bge-m3` (2.27GB) into memory, on top of PyTorch, FastAPI, and ChromaDB overhead, caused an out-of-memory crash in production (`Ran out of memory (used over 512MB)`). Before accepting the cost of a paid plan, three smaller alternatives were evaluated locally against the same 25-question evaluation suite (`evaluation/eval_suite.py`), using an isolated `CHROMA_PATH`/`EMBEDDING_MODEL` override so the production `bge-m3` index was never touched during testing:

| Model | Size (fp32) | Params | Multilingual? | Keyword Score | Source Accuracy |
|---|---|---|---|---|---|
| `BAAI/bge-m3` (current) | 2.27GB | 567M | ✅ 100+ languages | 72.0% | **84.0%** |
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | ~470MB | 118M | ✅ 50+ languages | **76.0%** | 72.0% |
| `sentence-transformers/all-MiniLM-L6-v2` | ~90MB | 22M | ❌ English-only | 52.0% | 72.0% |

Two other candidates under 500MB were ruled out before testing without even needing to run them, since their model cards explicitly state English-only support: `thenlper/gte-small` and `BAAI/bge-small-en-v1.5` (the small, English-only sibling of `bge-m3` itself).

**Finding:** the multilingual MiniLM model scored slightly higher on keyword accuracy than `bge-m3`, but source retrieval accuracy dropped to 72%, below this project's own target of ≥80% (see 4.3) with several *new* source-retrieval misses that did not occur with `bge-m3` (e.g. retrieving `perpres-110-2025-id.pdf` instead of `perpres-98-2021-en.pdf` for a basic carbon-pricing question). The English-only `all-MiniLM-L6-v2` performed worst overall its 52% keyword score is the clearest empirical evidence for why an English-only embedding model is unsuitable for this corpus: with 24% of the evaluation questions asked in Bahasa Indonesia and roughly a third of the source documents Indonesian-only, an English-only model cannot properly embed a large fraction of the corpus and questions into a comparable vector space, directly confirming the reasoning stated in the Decision above.

**Decision:** keep `BAAI/bge-m3` and address the memory constraint at the infrastructure level (Render plan tier) rather than by degrading retrieval quality below the project's documented target, or by dropping multilingual support entirely. `intfloat/multilingual-e5-small` (also ~470MB, but retrieval-optimized and specifically validated for Indonesian by LazarusNLP's benchmarking work) remains a candidate for future testing if further cost optimization is needed, but was not evaluated in this round given time constraints and the clear regression already observed with two same-size-class alternatives.

### 2.4 LCEL Chain (not a separate Prompt Builder)

**Decision:** Use LangChain Expression Language (LCEL) to build the RAG pipeline using `RunnablePassthrough` and `RunnableLambda` the modern LangChain 1.x approach rather than the legacy `ConversationalRetrievalChain`.

**Reason:** LangChain 1.x deprecated `ConversationalRetrievalChain` in favor of composable LCEL chains. LCEL gives explicit control over each step, retrieval, context formatting, history injection, prompt construction, and LLM call making the pipeline easier to debug, test, and extend. It also avoids the import errors that come with the legacy chain system in LangChain 1.x.

**Implementation:** `backend/app/services/rag_service.py` builds a chain using `RunnablePassthrough` for the question, `RunnableLambda` for formatting retrieved docs and chat history, and a custom prompt template that instructs the LLM to cite regulations and match the user's language. The chain deliberately stops at the LLM call rather than piping through `StrOutputParser`, so the raw `AIMessage` including `response_metadata` is preserved. This is required to report which underlying model actually answered (`model_used` in the API response), since the LLM is served via OpenRouter's `openai/gpt-oss-20b:free`, and earlier in development, the `openrouter/free` auto-router (see `ai-tooling.md` for the full model history).

### 2.5 MMR Retrieval Strategy

**Decision:** Use Maximal Marginal Relevance (MMR) retrieval instead of basic cosine similarity top-k.

**Reason:** Multiple documents overlap on the same topics (e.g., both Perpres 98/2021 and Perpres 110/2025 cover carbon pricing; both PermenLHK 21/2022 and PP 22/2021 cover environmental law). Basic top-k retrieval would return 5 near-identical chunks from the same document. MMR balances relevance with diversity, ensuring retrieved chunks come from different sections or documents, giving the LLM richer context.

### 2.6 Metadata Tagging per Document

**Decision:** Tag every chunk with structured metadata (`category`, `regulation`, `year`, `language`, `source_file`, `page`) during ingestion.

**Reason:** Enables filtered retrieval — when a user selects "Carbon Market" in the topic filter, the retriever only searches chunks tagged `category: carbon_market`. Without this, a question about AMDAL might retrieve carbon pricing chunks that happen to share keywords.

**Implementation:** `backend/ingestion/metadata.py` is a central registry mapping every filename to its full metadata. This keeps ingestion logic clean and makes it easy to update metadata when regulations change.

### 2.7 Chunking Strategy

**Decision:** Use different chunk sizes by document type 512 tokens for FAQ/factsheets, 1000 tokens for full regulations.

**Reason:** The OJK TKBI FAQ (`tkbi-ver3-faq.pdf`) contains short discrete Q&A pairs. Chunking at 1000 tokens would merge multiple Q&As into one chunk, degrading retrieval precision. Full regulations like the JETP CIPP (234 pages) need larger chunks to preserve paragraph-level context around policy provisions.

### 2.8 Technology Stack

| Component | Choice                                 | Reason |
|---|----------------------------------------|---|
| Backend | FastAPI + Python 3.14                  | Async, auto OpenAPI docs, Pydantic validation |
| Frontend | React + TypeScript + Vite              | Fast build, type safety, component reuse |
| Styling | Tailwind CSS                           | Utility-first, no separate CSS files to maintain |
| LLM | OpenRouter (`openai/gpt-oss-20b:free`) | Free tier, OpenAI-compatible API; final choice after two earlier models were discontinued or swapped unpredictably see `ai-tooling.md` for full history |
| Deployment | Render                                 | Free tier, Docker support, auto-deploy from GitHub, Singapore region |
| CI/CD | GitHub Actions                         | Lint + test + build check on every PR |

**Render advantages:** Single `render.yaml` deploys both services, Singapore region (low latency from Indonesia), CI-gated auto-deploy via `autoDeployTrigger: checksPass`. An earlier version of this project used a paid persistent disk (~$9.50/month) to store ChromaDB; this was removed in favor of downloading a pre-built archive on startup (see 2.12), keeping the entire deployment on the free plan.

### 2.9 Per-IP Rate Limiting

**Decision:** Add a simple in-memory sliding-window rate limiter, configurable via `RATE_LIMIT_PER_MINUTE`, applied to `/api/query` as a FastAPI dependency.

**Reason:** The query endpoint is public and every request costs an OpenRouter API call. Without any limit, a single client (accidental infinite loop, or deliberate abuse) could exhaust the free-tier LLM quota for all users. An in-memory limiter rather than a Redis-backed one was chosen because the Dockerfile already runs a single process (`--workers 1`) on a single Render instance; adding Redis would introduce an external dependency and cost with no benefit at this scale. This would need to move to shared storage if the app were later horizontally scaled across multiple instances.

**Implementation:** `backend/app/rate_limiter.py` and `InMemoryRateLimiter` tracks request timestamps per client IP in a sliding 60-second window, correctly reading the real client IP from `X-Forwarded-For` (required since Render sits behind a proxy `request.client.host` alone would show the proxy's IP for every request). Exceeding the limit returns `429 Too Many Requests` with a `Retry-After` header.

### 2.10 Explicit Language Enforcement

**Decision:** Inject an explicit, strongly-worded language instruction into the prompt based on the user's selected UI language (`en`/`id`), rather than relying on the LLM to infer output language from context.

**Reason:** Early testing showed that with the language toggle set to English, answers still mixed in Indonesian terms and phrases because most retrieved source documents are in Bahasa Indonesia, and a soft instruction like "match the user's language" was not enough to override that influence. The fix adds a `LANGUAGE_INSTRUCTIONS` dict with direct, imperative instructions per language (e.g. "Respond ENTIRELY in English... Translate any Indonesian terms...") and an explicit rule telling the model not to mix languages, even for quoted regulation terms.

**Implementation:** `backend/app/services/rag_service.py` the instruction is injected into the prompt as `{language_instruction}`, selected from `LANGUAGE_INSTRUCTIONS` based on the `language` parameter passed from the frontend toggle.

**Known limitation:** language enforcement controls the LLM's *output* language only — it does not influence which documents are *retrieved*. Section 4.4/4.5 documents a case (Q12) where an Indonesian-language question still retrieved the English sibling document, since the multilingual embedding model matches on topic rather than language.

---

## 3. Software Patterns Used

| Pattern | Where | Reason                                                                   |
|---|---|--------------------------------------------------------------------------|
| Repository abstraction | `retriever_service.py` | Decouples ChromaDB from RAG logic; easy to swap vector store             |
| Singleton via `lru_cache` | `embed_service.py`, `retriever_service.py` | Heavy models (570MB embedding) loaded once per process                   |
| Strategy pattern | `get_splitter()` in `indexer.py` | Different chunking strategy per document type without if/else throughout |
| Retry with exponential backoff | `rag_service.py` via `tenacity` | LLM API (OpenRouter) can return 429s; retry transparently                |
| Background tasks | `ingest.py` router | Ingestion takes minutes, runs without blocking the API                   |
| Metadata registry | `ingestion/metadata.py` | Central truth for all document metadata; ingestion stays clean           |

---

## 4. RAG Evaluation

### 4.1 Approach

Evaluation uses a ground-truth Q&A set (`evaluation/test_queries.json`) with **25 questions** covering all 6 document categories, both languages (19 English, 6 Indonesian), and 2 adversarial questions with no answer in the corpus. Three things are measured:

**Keyword Score** : percentage of expected answer keywords present in the model's response. Tests whether the answer contains the right factual content.

**Source Accuracy** : whether the expected source document appears in the top-3 retrieved chunks. Tests whether retrieval is working correctly.

**Refusal behavior (adversarial cases)** : for the 2 questions with no corresponding document in the corpus, whether the system correctly declines to answer rather than hallucinating a plausible-sounding but fabricated response. `expected_source` is left empty for these, which the scoring script treats as an automatic source-accuracy pass, so these cases are scored primarily by keyword/manual review of the answer text.

Run: `cd backend && python evaluation/eval_suite.py`

### 4.2 Test Cases

| # | Question | Expected Source | Category | Lang |
|---|---|---|---|---|
| 1 | Indonesia's unconditional NDC target? | enhanced-ndc-2022-en.pdf | climate_commitment | en |
| 2 | JETP financing commitment? | jetp-cipp-2023.pdf | energy_transition | en |
| 3 | PLTS Atap under Permen ESDM 2/2024? | permen-esdm-2-2024.pdf | renewable_energy | en |
| 4 | Carbon instruments in Perpres 98/2021? | perpres-98-2021-en.pdf | carbon_market | en |
| 5 | JETP status 2025? | jetp-progress-report-2025-en.pdf | energy_transition | en |
| 6 | Apa itu AMDAL? | permen-LHK-4-2021.pdf | environmental_law | id |
| 7 | TKBI v3 renewable classification? | tkbi-ver3-2026-en.pdf | green_finance | en |
| 8 | IDX Carbon regulation? | pojk-14-2023-id-carbon-trading.pdf | carbon_market | en |
| 9 | Renewable targets Perpres 112/2022? | perpres-112-2022.pdf | renewable_energy | en |
| 10 | Perpres 110/2025 carbon economy update? | perpres-110-2025-id.pdf | carbon_market | id |
| 11 | 2021 NDC conditional target (pre-enhancement)? | updated-ndc-2021-en.pdf | climate_commitment | en |
| 12 | Status implementasi JETP 2025? | jetp-progress-report-2025-id.pdf | energy_transition | id |
| 13 | PermenLHK 21/2022 carbon economic value (NEK)? | permen-LHK-21-2022.pdf | environmental_law | en |
| 14 | PP 22/2021 environmental protection framework? | pp-22-2021.pdf | environmental_law | en |
| 15 | OJK TKBI fact sheets summary? | tkbi-fact-sheets.pdf | green_finance | en |
| 16 | TKBI FAQ — transition activity classification? | tkbi-ver3-faq.pdf | green_finance | en |
| 17 | Klasifikasi aktivitas transisi TKBI v3? | tkbi-ver3-2026-id.pdf | green_finance | id |
| 18 | Instrumen nilai ekonomi karbon Perpres 98/2021? | perpres-98-2021-id.pdf | carbon_market | id |
| 19 | NDC 2022 adaptation measures? | enhanced-ndc-2022-en.pdf | climate_commitment | en |
| 20 | JETP CIPP coal retirement plans? | jetp-cipp-2023.pdf | energy_transition | en |
| 21 | Permen ESDM 2/2024 net metering scheme? | permen-esdm-2-2024.pdf | renewable_energy | en |
| 22 | Perpres 112/2022 coal plant retirement? | perpres-112-2022.pdf | renewable_energy | en |
| 23 | POJK 14/2023 carbon exchange participants? | pojk-14-2023-id-carbon-trading.pdf | carbon_market | en |
| 24 | **Adversarial:** EV tax incentives (not in corpus) | — | none | en |
| 25 | **Adversarial:** BBM subsidy price (not in corpus) | — | none | id |

Compared to the original 10-question set, this expansion adds coverage for 5 previously-untested documents (Updated NDC 2021, PermenLHK 21/2022, PP 22/2021, TKBI Fact Sheets, TKBI FAQ), increases the Indonesian-language share from 20% to 24%, and adds the 2 adversarial cases to test for hallucination avoidance.

### 4.3 Target Metrics

| Metric | Target | Notes |
|---|---|---|
| Keyword Score | ≥ 0.70 | 70%+ of expected terms present in answer |
| Source Accuracy | ≥ 0.80 | Correct document retrieved in top-3 |
| Refusal behavior | Qualitative | Both adversarial questions should decline to answer rather than fabricate a response reviewed manually via `answer_preview` in the eval output |

### 4.4 Results

```
=== EVALUATION RESULTS (25-question set) ===
Total   : 25
OK      : 25
Keywords: 72.0%
Sources : 84.0%
```

Both metrics exceed target (Keyword Score ≥ 70%, Source Accuracy ≥ 80%).

**Keyword-only misses (source correctly retrieved, model phrased the answer differently):**

| # | Question | Missing keyword(s) |
|---|---|---|
| 2 | JETP financing commitment | "20 billion" |
| 3 | PLTS Atap regulation | "net metering" |
| 4 | Perpres 98/2021 carbon instruments | "carbon levy" |
| 5 | JETP 2025 status | "financing", "approved" |
| 8 | IDX Carbon / POJK 14/2023 | "bursa karbon", "carbon" |
| 13 | PermenLHK 21/2022 (NEK) | "carbon economic value", "NEK" |
| 21 | Net metering (ESDM 2/2024) | "net metering", "rooftop" |
| 23 | Carbon exchange participants | "participant" |
| 25 | Adversarial (fuel subsidy, id) | "tidak" |

**Source retrieval misses: a distinct, more interesting pattern:**

| # | Question | Expected source | Actually retrieved | Root cause                                                                                                                                                                              |
|---|---|---|---|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 11 | 2021 NDC conditional target | `updated-ndc-2021-en.pdf` | `enhanced-ndc-2022-en.pdf` | Sibling-document confusion, both are Indonesia's NDC submissions in the same `climate_commitment` category, and the newer 2022 version is retrieved instead of the 2021 one it superseded |
| 12 | JETP 2025 status (asked in Indonesian) | `jetp-progress-report-2025-id.pdf` | `jetp-progress-report-2025-en.pdf` | **Cross-language retrieval miss** `bge-m3` matched on semantic topic, not language; the Indonesian question retrieved the English sibling document instead of the Indonesian one        |
| 16 | TKBI FAQ classification | `tkbi-ver3-faq.pdf` | `tkbi-ver3-2026-en.pdf` / `-id.pdf` | Sibling-document confusion FAQ and the main TKBI v3 document both cover classification and share the `green_finance` category                                                           |
| 20 | JETP CIPP coal retirement | `jetp-cipp-2023.pdf` | `jetp-progress-report-2025-en.pdf` | Sibling-document confusion the original CIPP plan and its own 2025 progress report are topically close enough within `energy_transition` for MMR to conflate them                       |

**Analysis:** the topic-filter fix from the 10-question evaluation (see 2.6) successfully eliminated *cross-category* retrieval errors no question retrieved a document from the wrong category in this 25-question run. What remains is a narrower, more subtle failure mode: *within-category sibling confusion*, where two or more documents in the same category (different years, different languages, or a source document vs. its own progress report) are similar enough that MMR retrieval sometimes returns the wrong one. This affected 4 of 25 questions (16%), all still landing at 84% source accuracy overall above target, but a clear direction for further improvement (see 4.5).

### 4.5 Known Limitations

- Indonesian-language questions (Q6, Q10) depend on `bge-m3` correctly embedding Bahasa Indonesia retrieval quality is slightly lower than English due to smaller Indonesian training data in the base model
- Free-tier LLM (`openai/gpt-oss-20b:free`) occasionally truncates long regulatory text in the answer mitigated by `max_tokens=1024`
- The specific free model in use has changed twice during development (`meta-llama/llama-3.1-8b-instruct:free` → `openrouter/free` → `openai/gpt-oss-20b:free`) as OpenRouter's free-tier lineup shifted; see `ai-tooling.md` for the full history and rationale
- **Category filtering is important for retrieval accuracy when documents overlap heavily on topic.** An early evaluation run without category filtering scored only 70% source accuracy, 3 of 4 `carbon_market` questions (Perpres 98/2021, POJK 14/2023, Perpres 110/2025 all cover similar carbon pricing topics) retrieved the wrong sibling document via MMR. Passing the topic filter during evaluation (mirroring how a real user would apply it in the UI) raised source accuracy to 100%. This confirms the topic filter feature (see 2.6) is not just a UX convenience but materially improves retrieval precision for overlapping-topic categories.
- Initial evaluation also incorrectly forced English output on Indonesian-language questions (`get_rag_response` defaulted to `language="en"` when not explicitly passed), which masked the language-enforcement feature working correctly (see 2.11) and undercounted keyword score. Fixed by passing each question's actual language in `evaluation/test_queries.json`.
- **Category filtering does not resolve confusion between sibling documents *within* the same category.** The expanded 25-question evaluation (see 4.4) found 4 source-retrieval misses, all involving two documents that share a category but cover closely related content e.g. the original NDC 2021 vs. its 2022 update, or the JETP CIPP 2023 plan vs. its own 2025 progress report. Category filtering narrows the search space but cannot distinguish between siblings at that level of granularity.
- **Multilingual embeddings match on topic, not language.** Question 12 (asked in Indonesian, expecting the Indonesian-language JETP progress report) instead retrieved the English sibling document. `bge-m3` embeds semantically similar content close together regardless of language, so a same-topic, different-language document can outrank the language-matched one. A more targeted fix not yet implemented would be to also filter retrieval by the document's `language` metadata field when it matches the query's selected language, similar to how the existing category filter works.
- Both findings above suggest a natural next improvement: finer-grained retrieval filtering (e.g. by regulation year, or an automatic language-match boost) rather than category alone, for corpora containing multiple versions or translations of closely related regulations.

---

## 5. Testing Strategy

### 5.1 Unit Tests (`tests/test_ingestion.py`)
Tests the metadata registry and chunking logic without touching ChromaDB or the LLM:
- All 18 documents have required metadata fields
- All categories are from the valid set
- All year values are in reasonable range (2000–2030)
- FAQ/factsheet documents use smaller chunk size than full regulations

### 5.2 API Tests (`tests/test_api.py`)
Tests the FastAPI layer using `TestClient` with mocked RAG responses:
- Endpoint availability (root, health, query, ingest status)
- Input validation empty question, too-long question, invalid language code
- Correct forwarding of category filter and language to the RAG service
- Multi-turn chat history passing
- Rate limiting is actually enforced end-to-end through the real endpoint
  (temporarily lowers the limit to 2, confirms the 3rd request returns
  `429 Too Many Requests` with a `Retry-After` header)

### 5.3 Startup Tests (`tests/test_startup.py`)
Tests the ChromaDB download-on-startup logic (`app/startup.py`) that production
deployment depends on since moving off a paid persistent disk (see 2.12), using
a mocked `httpx.Client` so no real network call is made during CI:
- Correctly detects populated vs. empty vs. non-existent ChromaDB directories
- Skips the download entirely when data already exists (e.g. local dev)
- Warns and returns cleanly when no download URL is configured, without crashing
- Downloads and extracts a zip archive correctly, including nested directories
- Calls the exact configured URL (protects against a stale or mistyped value)
- Raises clearly on a failed download or a corrupt/invalid zip file, rather
  than leaving a silently empty or partially-extracted ChromaDB

### 5.4 Rate Limiter Tests (`tests/test_rate_limiter.py`)
Tests `InMemoryRateLimiter` (see 2.10) in isolation, without going through
the full FastAPI app:
- Allows requests under the configured limit, blocks the request that exceeds it
- Tracks different client IPs independently one client hitting its limit
  does not affect another
- Sliding window correctly resets after the configured time period passes
- Reads the real client IP from `X-Forwarded-For` when present (Render sits
  behind a proxy), falling back to `request.client.host` otherwise
- Error response includes a `Retry-After` header and a clear message stating
  the configured limit

### 5.5 CI/CD Pipeline (`.github/workflows/ci.yml`)
Runs on every pull request and push to `main`:
- Python lint (ruff)
- pytest unit + API + startup + rate limiter tests (33 total)
- TypeScript type check (`tsc --noEmit`)
- Frontend production build