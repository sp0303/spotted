# Spotted

Did AI spot your business? Spotted shows a small business whether search engines, maps, AI assistants and voice assistants find it, mention it and recommend it, and what to do when they don't.

Status: building. Step 1 of the build order (website → business profile → owner confirms) is in `backend/`.

| Path | Contents |
|---|---|
| [backend](backend) | FastAPI backend: profile extraction API, CLI and tests |
| [docs/plan.md](docs/plan.md) | Product plan, research findings, test results, tech stack, naming |
| [schema/schema.sql](schema/schema.sql) | PostgreSQL schema, draft v1 (25 tables) |
| [research/gemini_test](research/gemini_test) | Gemini API test for Test 1 (Dallas florists), app results used for comparison, and the 20 Nov 2026 run |

To run the Gemini test: `cd research/gemini_test`, `pip install -r requirements.txt`, copy `.env.example` to `.env` and add your key, then `python test_gemini.py --model gemini-3.8-flash`. `.env` is git-ignored.

## Backend

Python 3.12+, PostgreSQL 15+. From `backend/`:

```bash
pip install -e '.[dev]'
cp .env.example .env    # add GEMINI_API_KEY and DATABASE_URL
```

Try extraction on a real site without a database:

```bash
python -m spotted.cli https://example-florist.com
```

Run the API (creates the schema on first start if the database is empty), then open http://localhost:8000/docs:

```bash
uvicorn spotted.api:app --reload
```

| Endpoint | Does |
|---|---|
| `POST /api/profiles` `{"url": "..."}` | Fetches the homepage and up to 5 key pages, extracts a draft profile, saves it unconfirmed |
| `GET /api/businesses/{id}` | Current profile |
| `PUT /api/businesses/{id}/profile` | Owner confirms the (edited) profile; values become `confirmed` and are written to the business tables |

Each value in a profile is `extracted` (stated on the site, with the page and a quote), `inferred` (our guess, the owner must check) or `confirmed`. An LLM claim that the site states something is only kept as `extracted` if its quote is actually on the page.

Tests (`TEST_DATABASE_URL` enables the API tests; the database is wiped):

```bash
TEST_DATABASE_URL=postgresql://spotted:spotted@localhost/spotted_test pytest
```
