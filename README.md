# Net Detective

Minimal network monitoring service with a single-page dashboard.

## Backend

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
python -m uvicorn net_detective.main:app --reload
```

### Environment

Copy `.env.example` to `.env` and adjust as needed.

## Frontend

```bash
cd web
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`.

## Scripts

```bash
python scripts/simulate_failure.py
python scripts/generate_report.py
```
