# Graduation Finance Platform

Unified FastAPI portal for:

- Quant stock selection for STAR Market
- Stock prediction service rebuilt from `6main_clean.py`
- Built-in AI finance assistant

## Run

1. Activate the existing conda environment:

```powershell
conda activate finance
```

2. Copy `.env.example` to `.env` and fill:

- `MYSQL_HOST`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DB`
- `TUSHARE_TOKEN`
- `ZHIPU_API_KEY` if LLM fallback chat is needed
- `MODEL_NAME` if a non-default LLM model is used

3. Create the database:

```sql
CREATE DATABASE graduation_finance DEFAULT CHARACTER SET utf8mb4;
```

4. Start the app:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Only the main platform service is required.

## Pages

- `/`
- `/quant`
- `/predictor`
- `/assistant`

## Current status

- Portal and routing are ready.
- Quant module has STAR Market sync, factor calculation, scoring, model training, and prediction workflow.
- Predictor service and page are available.
- AI assistant is built into the main FastAPI app and uses `/api/assistant/...` APIs.
- AI assistant is served by the main platform.
