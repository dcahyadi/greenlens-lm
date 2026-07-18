# 🌿 GreenLens LM

> A Retrieval-Augmented Generation (RAG) powered Q&A application for querying Indonesia's green economy policies and sustainability regulations, including NDC climate commitments, JETP energy transition plans, AMDAL environmental guidelines, carbon credit policies, and KLHK regulations

[![CI](https://github.com/dcahyadi/greenlens-lm/actions/workflows/ci.yml/badge.svg)](https://github.com/dcahyadi/greenlens-lm/actions)

## 🔗 Links

- **Live App**: see [docs/deployed.md](docs/deployed.md)

## 📚 Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS |
| Backend | FastAPI + Python 3.13 |
| RAG | LangChain + ChromaDB (embedded) |
| Embeddings | BAAI/bge-m3 (multilingual EN+ID) |
| LLM | OpenRouter (`openai/gpt-oss-20b:free`) |
| Deployment | Render (Docker backend + Static Site frontend) |
| CI/CD | GitHub Actions |


## 📚 Document Corpus

18 official government documents across 6 categories — all publicly available.

| Category | Regulation | Year | Lang | Source |
|---|---|---|---|---|
| 🌍 Climate commitment | [Enhanced NDC 2022](https://unfccc.int/sites/default/files/NDC/2022-09/23.09.2022_Enhanced%20NDC%20Indonesia.pdf) | 2022 | EN | unfccc.int |
| 🌍 Climate commitment | [Updated NDC 2021](https://unfccc.int/sites/default/files/NDC/2022-06/Updated%20NDC%20Indonesia%202021%20-%20corrected%20version.pdf) | 2021 | EN | unfccc.int |
| ⚡ Energy transition | [JETP CIPP 2023](https://jetp-id.org/storage/official-jetp-cipp-2023-vshare_f_en-1700532655.pdf) | 2023 | EN | jetp-id.org |
| ⚡ Energy transition | [JETP Progress Report 2025 (EN)](https://drive.google.com/file/d/1RhW5MLzbza69uaZHfho4bnQLSmjnAjWO) | 2025 | EN | jetp-id.org |
| ⚡ Energy transition | [JETP Progress Report 2025 (ID)](https://drive.google.com/file/d/1AqXYWAOUFcfCZman41rDBoKeShkZZXcK) | 2025 | ID | jetp-id.org |
| 💰 Carbon market | [Perpres 98/2021 (EN)](https://climate-laws.org/documents/presidential-regulation-no-98-of-2021-on-the-implementation-of-carbon-pricing-to-achieve-the-nationally-determined-contribution-target-and-control-over-greenhouse-gas-emissions-in-the-national-development_6ca2) | 2021 | EN | jdih.maritim.go.id |
| 💰 Carbon market | [Perpres 98/2021 (ID)](https://peraturan.bpk.go.id/details/187122/perpres-no-98-tahun-2021) | 2021 | ID | jdih.maritim.go.id |
| 💰 Carbon market | [Perpres 110/2025 (ID)](https://peraturan.bpk.go.id/Details/334733/perpres-no-110-tahun-2025) | 2025 | ID | setkab.go.id |
| 💰 Carbon market | [POJK 14/2023 — IDX Carbon](https://www.ojk.go.id/id/regulasi/Documents/Pages/Perdagangan-Karbon-Melalui-Bursa-Karbon/POJK%2014%20Tahun%202023%20-%20PERDAGANGAN%20KARBON%20MELALUI%20BURSA%20KARBON.pdf) | 2023 | ID | ojk.go.id |
| 🌿 Environmental law | [PermenLHK 4/2021 — AMDAL](https://peraturan.bpk.go.id/Details/210998/permen-lhk-no-4-tahun-2021) | 2021 | ID | menlhk.go.id |
| 🌿 Environmental law | [PermenLHK 21/2022 — NEK](https://peraturan.bpk.go.id/Details/235421/permen-lhk-no-21-tahun-2022) | 2022 | ID | menlhk.go.id |
| 🌿 Environmental law | [PP 22/2021 — AMDAL framework](https://peraturan.bpk.go.id/Details/161852/pp-no-22-tahun-2021) | 2021 | ID | bpk.go.id |
| 🔋 Renewable energy | [Perpres 112/2022 — EBT](https://peraturan.bpk.go.id/Details/225308/perpres-no-112-tahun-2022) | 2022 | ID | esdm.go.id |
| 🔋 Renewable energy | [Permen ESDM 2/2024 — PLTS Atap](https://peraturan.bpk.go.id/Details/288519/permen-esdm-no-2-tahun-2024) | 2024 | ID | esdm.go.id |
| 🏦 Green finance | [TKBI Version 3 2026 (EN)](https://ojk.go.id/id/Publikasi/Roadmap-dan-Pedoman/Sektor-Jasa-Keuangan/Keuangan-Berkelanjutan/Documents/Indonesia%20Taxonomy%20for%20Sustainable%20Finance%20%28TKBI%29%20Versi%203.pdf) | 2026 | EN | ojk.go.id |
| 🏦 Green finance | [TKBI Version 3 2026 (ID)](https://ojk.go.id/id/Publikasi/Roadmap-dan-Pedoman/Sektor-Jasa-Keuangan/Keuangan-Berkelanjutan/Documents/Buku%20Taksonomi%20untuk%20Keuangan%20Berkelanjutan%20Indonesia%20%28TKBI%29%20Versi%203.pdf) | 2026 | ID | ojk.go.id |
| 🏦 Green finance | [TKBI Fact Sheets](https://ojk.go.id/id/Publikasi/Roadmap-dan-Pedoman/Sektor-Jasa-Keuangan/Keuangan-Berkelanjutan/Documents/Fact%20Sheets%20TKBI.pdf) | 2026 | EN | ojk.go.id |
| 🏦 Green finance | [TKBI FAQ](https://ojk.go.id/id/Publikasi/Roadmap-dan-Pedoman/Sektor-Jasa-Keuangan/Keuangan-Berkelanjutan/Documents/FAQ%20Taksonomi%20untuk%20Keuangan%20Berkelanjutan%20Indonesia%20%28TKBI%29%20Versi%203.pdf) | 2026 | EN | ojk.go.id |

## 🚀 Local Development (Python 3.13)

### Prerequisites
- Python 3.14.x
- Node.js 20+

### 1. Clone & place your documents

```bash
git clone https://github.com/dcahyadi/greenlens-lm.git
cd greenlens-lm
```

Place your PDFs of document corpus into `data/documents/` by category:
```
data/documents/
├── carbon/    perpres-98-2021-en.pdf, perpres-98-2021-id.pdf,
│              perpres-110-2025-id.pdf, pojk-14-2023-id-carbon-trading.pdf
├── esdm/      permen-esdm-2-2024.pdf, perpres-112-2022.pdf
├── jetp/      jetp-cipp-2023.pdf, jetp-progress-report-2025-en.pdf,
│              jetp-progress-report-2025-id.pdf
├── klhk/      permen-LHK-4-2021.pdf, permen-LHK-21-2022.pdf, pp-22-2021.pdf
├── ndc/       enhanced-ndc-2022-en.pdf, updated-ndc-2021-en.pdf
└── ojk/       tkbi-ver3-2026-en.pdf, tkbi-ver3-2026-id.pdf,
               tkbi-fact-sheets.pdf, tkbi-ver3-faq.pdf
```

### 2. Backend setup

```bash
cd backend
cp .env.example .env
# Open .env and set all your env value

python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate

# Python 3.13: install PyTorch CPU first, then the rest
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Run ingestion — builds chroma_db/ folder
python ingestion/indexer.py

# Start API
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env.local   # VITE_API_URL=http://localhost:8000
npm run dev
# → Open http://localhost:5173
```

## 🧪 Testing
The backend has **33 automated tests** covering the ingestion pipeline, API endpoints, rate limiting, and the ChromaDB download-on-startup logic
```bash
cd backend
pytest tests/ -v
```
### What's covered

| Test file | Focus |
|---|---|
| `test_api.py` | API endpoints, incl. rate-limit integration (429 responses) |
| `test_ingestion.py` | PDF → chunk → embed → ChromaDB ingestion pipeline |
| `test_startup.py` | ChromaDB download-on-startup logic (9 tests) — download, extract, skip-if-exists, failure handling, corrupt archive handling |
| `test_rate_limiter.py` | Per-IP sliding-window rate limiter (unit tests) |

## 📄 Docs

- [Design & Testing](docs/design-and-testing.md) — architecture decisions, testing strategy, RAG evaluation
- [AI Tooling](docs/ai-tooling.md) — AI tools used during development
- [Deployed](docs/deployed.md) — live deployment link

## 🚀 Deployment (Render)

1. Push to GitHub
2. Connect repo on render.com → "Use Blueprint" (reads `render.yaml` automatically)
3. Set `OPENROUTER_API_KEY` in Render dashboard under Environment
4. Run ingestion locally, then upload to Render disk:
   ```bash
   export RENDER_SSH=ssh-xxxx@ssh.singapore.render.com
   ./backend/ingestion/upload_to_render.sh
   ```