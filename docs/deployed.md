# Deployed Application

## Deployment (Render)
This project uses Render for deployment as an example only, but other deployment platforms can also be used.

1. Push to GitHub
2. Connect repo on render.com → "Use Blueprint" (reads `render.yaml` automatically)
3. Set `OPENROUTER_API_KEY` in Render dashboard under Environment
4. Run ingestion locally, then upload to Render disk:
   ```bash
   export RENDER_SSH=ssh-xxxx@ssh.singapore.render.com
   ./backend/ingestion/upload_to_render.sh
   ```
   
## Live Links

| Service | URL                                                     |
|---|---------------------------------------------------------|
| **Frontend (Web App)** | https://greenlens-lm.onrender.com                       |
| **Backend API** | https://greenlens-lm-api.onrender.com                   |
| **API Docs (Swagger)** | https://greenlens-lm-api.onrender.com/docs *(dev only)* |

## GitHub Repository

**Repository:** https://github.com/dcahyadi/greenlens-lm

The repository contains:
- All source code (backend + frontend)
- This deployment documentation
- [Design & Testing document](design-and-testing.md)
- CI/CD pipeline (`.github/workflows/ci.yml`)
- Render Blueprint (`render.yaml`)

## Deployment Architecture

```
GitHub (main branch)
    │
    ├── push → GitHub Actions CI
    │           └── lint + test + build check
    │
    └── CI passes → Render auto-deploy (autoDeployTrigger: checksPass)
                ├── greenlens-lm-api  (Docker Web Service, Singapore, free plan)
                │   └── FastAPI + ChromaDB, downloaded from a GitHub Release
                │       asset on container startup (no persistent disk —
                │       see app/startup.py)
                └── greenlens      (Static Site, global CDN, free plan)
                    └── React app built from frontend/dist/
```

## Deployment Steps (for reference)

1. Connected GitHub repo to Render → selected "Use Blueprint" → Render reads `render.yaml`
2. Set `OPENROUTER_API_KEY` and `HF_TOKEN` in Render dashboard → greenlens-lm-api → Environment
3. Ran ingestion locally: `cd backend && python ingestion/indexer.py`
4. Zipped the resulting `chroma_db/` folder and uploaded it as a GitHub Release
   asset for avoiding the cost of a paid persistent disk
5. Set `CHROMA_DB_DOWNLOAD_URL` in `render.yaml` to the Release asset's direct
   download URL
6. On each cold start, `app/startup.py` downloads and extracts this archive
   into the container's local (ephemeral) filesystem before the app begins
   serving requests — verified via `/health` returning `chroma_accessible: true`
   and `collection_count: 1`