# Invoice Processor (Gemini Vision + VLM)

Production-ready invoice upload + extraction web application using **FastAPI** (backend) and **Next.js (CSR only)** (frontend).
The backend uses **Gemini Vision-Language Model** directly (no OCR libraries).

## What it does

1. Upload invoice files: `pdf`, `docx`, `jpg`, `png`, `txt` (max `10MB`)
2. Convert PDF/DOCX/TXT/images into page-wise images (no OCR)
3. Call Gemini with the required master prompt
4. Parse + validate strict JSON into a structured shape
5. Frontend renders:
   - Raw JSON
   - Clean Header / Body / Footer invoice view
   - Dynamic TanStack table for line items (only when present)

## Folder structure

```text
backend/
  app/
    controllers/
    routes/
    services/
    schemas/
    utils/
  tests/
  requirements.txt
  .env.example
frontend/
  app/
  components/
  styles/
  package.json
  .env.example
README.md
```

## Backend (FastAPI)

1. Prereqs
   - Python 3.11+
2. Install
   - `pip install -r backend/requirements.txt`
3. Configure
   - Create `backend/.env` from `backend/.env.example`
   - Set `GEMINI_API_KEY`
4. Run
   - From `backend/`:
     - `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

### Run tests
- From `backend/`: `pytest`

## Frontend (Next.js CSR)

1. Install
   - From `frontend/`: `npm install`
2. Configure
   - Create `frontend/.env` from `frontend/.env.example`
3. Run
   - `npm run dev`
4. Open
   - Visit the dev URL shown in the terminal (typically `http://localhost:3000`)

## Notes / constraints

- No OCR libraries are used.
- DOCX handling is best-effort text rendering into images (layout fidelity for tables/images may vary).
- Invoice UI never auto-translates; it displays extracted values as returned by Gemini.

