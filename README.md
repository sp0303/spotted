# Spotted

Did AI spot your business? Spotted shows a small business whether search engines, maps, AI assistants and voice assistants find it, mention it and recommend it, and what to do when they don't.

Status: building. The whole flow works end to end in `backend/` and `frontend/`: website → business profile → owner confirms (step 1), foundation checks (2), AI runs on Gemini with Google Search and Maps (3), search, Maps, listings and Google News press (6), and a report with evidence-based actions (4, 5). The full audit (7) is built but switched off until payment exists (`PAID_AUDITS_ENABLED=1` for dev). ChatGPT, Perplexity, Claude, Copilot and Google AI Mode are "coming soon" until their keys are added; real Google/Bing rankings and Yelp/Bing Places/Apple listings need paid data providers.

| Path | Contents |
|---|---|
| [backend](backend) | FastAPI backend (MongoDB): profile extraction, foundation checks, CLI and tests |
| [frontend](frontend) | React + TypeScript app: enter a URL, confirm the profile, see the foundation checks |
| [docs/plan.md](docs/plan.md) | Product plan, research findings, test results, tech stack, naming |
| [schema/schema.sql](schema/schema.sql) | Reference data model, draft v1 (25 tables, written as PostgreSQL); the backend stores it in MongoDB |
| [research/model_compare](research/model_compare) | Test 2: the same prompts on Gemini, NVIDIA and OpenRouter models, with cost tracking (results in docs/plan.md, Update 9) |
| [research/gemini_test](research/gemini_test) | Gemini API test for Test 1 (Dallas florists), app results used for comparison, and the 20 Nov 2026 run |

To run the Gemini test: `cd research/gemini_test`, `pip install -r requirements.txt`, copy `.env.example` to `.env` and add your key, then `python test_gemini.py --model gemini-3.8-flash`. `.env` is git-ignored.

## Backend

Python 3.12+, MongoDB 6+. From `backend/`:

```bash
pip install -e '.[dev,render]'
playwright install chromium   # for the JavaScript-rendering check (optional)
cp .env.example .env    # add GEMINI_API_KEY and MONGO_URL / MONGO_DB
```

Try extraction on a real site without a database:

```bash
python -m spotted.cli https://example-florist.com
```

Run the API (creates its indexes and seeds the crawler registry on start), then open http://localhost:8000/docs:

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
| `GET /api/businesses/{id}/ai-prompts` | Suggested questions (free run and full audit), available and "coming soon" platforms, limits |
| `POST /api/businesses/{id}/ai-runs` `{"prompts": [...], "platforms": [...], "tier": "free"\|"paid"}` | Starts an AI run in the background (202); reuses a recent identical free run; 429 over the free limits, 403 for the full audit while it's disabled |
| `GET /api/ai-runs/{audit_id}` | AI run progress and results: who was named, competitors, cited sources, wrong facts, cost (poll while `running`) |
| `GET /api/businesses/{id}/ai-runs/latest` | Latest AI run |
| `POST /api/businesses/{id}/search` | Starts the search and listings check (Gemini Maps and Search grounding, Google News press) |
| `GET /api/businesses/{id}/search` | Latest search and listings results |
| `GET /api/businesses/{id}/report` | Combined report (foundations, AI, search, press, before/after) and the action list |
| `GET /api/businesses/{id}/actions` | Action Center list |
| `PATCH /api/businesses/{id}/actions/{action_id}` `{"status": ...}` | Updates an action's status (not_started, in_progress, done, dismissed) |

Foundation checks: HTTPS and redirects, robots.txt per crawler (16-crawler registry grouped into search, user-triggered and training), sitemap, noindex, canonical, CDN/WAF blocking (the homepage requested with each crawler's user-agent and compared with a browser request), text with vs without JavaScript (headless Chromium), and WebMCP. Google and Bing indexing and IndexNow are reported as "not verified" until Search Console, Bing Webmaster Tools or search data are connected.

Each value in a profile is `extracted` (stated on the site, with the page and a quote), `inferred` (our guess, the owner must check) or `confirmed`. An LLM claim that the site states something is only kept as `extracted` if its quote is actually on the page.

Data lives in three MongoDB collections named with `MONGO_COLLECTION_PREFIX` (default `spotted_`): `businesses` (profile, plus confirmed aliases, locations, services and competitors embedded), `audits` (each run with its foundation checks and crawler access results embedded) and `crawlers` (the registry). The prefix lets Spotted share a database with other apps.

Tests (`TEST_MONGO_URL` enables the API tests; they use the `spotted_test` database, or `TEST_MONGO_DB`, and drop only its `spotted_test_` collections):

```bash
TEST_MONGO_URL=mongodb://localhost:27017 pytest
```

## Frontend

Node 22+. With the API running on port 8000:

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. `npm test` runs the component tests; `npm run build` type-checks and builds to `dist/`.
