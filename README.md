# Spotted

Did AI spot your business? Spotted shows a small business whether search engines, maps, AI assistants and voice assistants find it, mention it and recommend it, and what to do when they don't.

Status: research and planning.

| Path | Contents |
|---|---|
| [docs/plan.md](docs/plan.md) | Product plan, research findings, test results, tech stack, naming |
| [schema/schema.sql](schema/schema.sql) | PostgreSQL schema, draft v1 (25 tables) |
| [research/gemini_test](research/gemini_test) | Gemini API test for Test 1 (Dallas florists), app results used for comparison, and the 20 Nov 2026 run |

To run the Gemini test: `cd research/gemini_test`, `pip install -r requirements.txt`, copy `.env.example` to `.env` and add your key, then `python test_gemini.py --model gemini-3.8-flash`. `.env` is git-ignored.
