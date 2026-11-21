# Spotted

Did AI spot your business? Spotted shows a small business whether search engines, maps, AI assistants and voice assistants find it, mention it and recommend it, and what to do when they don't.

Status: building. Build-order steps 1 (website → business profile → owner confirms) and 2 (foundation checks) work end to end in `backend/` and `frontend/`.

| Path | Contents |
|---|---|
| [backend](backend) | FastAPI backend: profile extraction, foundation checks, CLI and tests |
| [frontend](frontend) | React + TypeScript app: enter a URL, confirm the profile, see the foundation checks |
| [docs/plan.md](docs/plan.md) | Product plan, research findings, test results, tech stack, naming |
| [schema/schema.sql](schema/schema.sql) | PostgreSQL schema, draft v1 (25 tables) |
| [research/gemini_test](research/gemini_test) | Gemini API test for Test 1 (Dallas florists), app results used for comparison, and the 20 Nov 2026 run |

To run the Gemini test: `cd research/gemini_test`, `pip install -r requirements.txt`, copy `.env.example` to `.env` and add your key, then `python test_gemini.py --model gemini-3.8-flash`. `.env` is git-ignored.

## Backend

Python 3.12+, PostgreSQL 15+. From `backend/`:

```bash
pip install -e '.[dev,render]'
playwright install chromium   # for the JavaScript-rendering check (optional)
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
| `POST /api/businesses/{id}/foundations` | Runs the foundation checks (no AI) and stores them as an audit |
| `GET /api/businesses/{id}/foundations` | Latest foundation checks |

Foundation checks: HTTPS and redirects, robots.txt per crawler (16-crawler registry grouped into search, user-triggered and training), sitemap, noindex, canonical, CDN/WAF blocking (the homepage requested with each crawler's user-agent and compared with a browser request), text with vs without JavaScript (headless Chromium), and WebMCP. Google and Bing indexing and IndexNow are reported as "not verified" until Search Console, Bing Webmaster Tools or search data are connected.

Each value in a profile is `extracted` (stated on the site, with the page and a quote), `inferred` (our guess, the owner must check) or `confirmed`. An LLM claim that the site states something is only kept as `extracted` if its quote is actually on the page.

Tests (`TEST_DATABASE_URL` enables the API tests; the database is wiped):

```bash
TEST_DATABASE_URL=postgresql://spotted:spotted@localhost/spotted_test pytest
```

## Frontend

Node 22+. With the API running on port 8000:

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. `npm test` runs the component tests; `npm run build` type-checks and builds to `dist/`.
