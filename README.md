# AI Finance Copilot

Ask questions about your finances in plain English. Upload a bank statement, then ask things like *"how much did I spend on Swiggy?"* or *"give me insights on my spending"* — a multi-agent system routes each question to the right specialist agent and answers from your own data.

**Live demo:** https://finance-copilot-dnzx.onrender.com
**API docs:** https://finance-copilot-api-d3bf.onrender.com/docs

> **Note:** The backend runs on Render's free tier and spins down after inactivity. The first request may take 30–60 seconds to wake up.

---

## What it does

- **Natural-language queries** over your transactions — an LLM writes the SQL, guarded by read-only validation and enforced per-user scoping.
- **Automatic expense categorization** using a hybrid rules-plus-LLM approach.
- **Spending insights** computed deterministically in Python, phrased by an LLM.
- **PDF report generation** covering income, spending, and category breakdowns.
- **Duplicate upload protection** via SHA-256 content hashing.
- **Multi-agent orchestration** — a LangGraph supervisor classifies each request and routes it to the SQL, analytics, expense, or report agent.

---

## Architecture

A single `/chat/ask` endpoint sends every question through a LangGraph supervisor. The supervisor's router node classifies intent, then a conditional edge dispatches to one specialist agent. Every agent runs scoped to the authenticated user.

```
                    ┌─────────────┐
   question  ─────► │  Supervisor │  (LangGraph router)
                    └──────┬──────┘
              ┌────────────┼────────────┬────────────┐
              ▼            ▼            ▼            ▼
          ┌───────┐   ┌─────────┐  ┌────────┐  ┌────────┐
          │  SQL  │   │Analytics│  │Expense │  │ Report │
          │ agent │   │  agent  │  │ agent  │  │ agent  │
          └───────┘   └─────────┘  └────────┘  └────────┘
```

### Design decisions

**The SQL agent generates queries, but never runs them unchecked.** Generated SQL is validated as read-only (SELECT only — no INSERT/UPDATE/DELETE/DROP), and the required `user_id` filter must be present in the query before it executes. If the model omits the filter, the query is rejected rather than run unscoped — fail-closed, not fail-open.

An earlier version wrapped the model's query as a subquery and filtered externally. That broke on aggregates: `SELECT SUM(amount)` returns no `user_id` column, so the outer filter matched nothing and totals came back empty. Requiring and verifying the filter inside the query handles both row-level and aggregate results correctly.

**Financial math is never left to the LLM.** The analytics and report agents compute every figure in Python and use the model only to phrase results. LLMs hallucinate arithmetic, so anything involving money is calculated deterministically and the raw numbers are returned alongside the prose.

**Categorization is a hybrid.** Keyword rules handle the common merchants instantly with no API call; only unrecognized descriptions go to the LLM, batched into a single request.

**Deduplication happens at the file level, not the transaction level.** Identical transactions are legitimate — two coffees on the same day at the same price is normal. Re-uploading the same statement is not. Uploads are therefore deduplicated by SHA-256 hash of the file contents, which also catches renamed copies. In production, the bank's transaction reference number would be the proper per-transaction key.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React (Vite), Recharts, Axios |
| Backend | FastAPI, SQLAlchemy |
| AI | LangChain, LangGraph, Groq (`openai/gpt-oss-20b`) |
| Database | PostgreSQL (Supabase) |
| Auth | JWT (python-jose), bcrypt |
| Reports | ReportLab |
| Hosting | Render (web service + static site) |

---

## Security

- Passwords hashed with bcrypt (salted, one-way); only the hash is stored.
- Login returns the same error for unknown emails and wrong passwords, so registered addresses can't be enumerated.
- JWT-based auth; every data route is guarded and scoped to the authenticated user.
- LLM-generated SQL is validated read-only and rejected if the user scope filter is missing.
- All application-issued database writes are parameterized.
- Secrets are supplied via environment variables and are not committed to the repository.

**Known limitation:** user scoping is enforced at the application layer. A production deployment should add PostgreSQL row-level security and a read-only database role so isolation is guaranteed by the database itself, independent of generated SQL.

---

## Running locally

**Prerequisites:** Python 3.12, Node 18+, a PostgreSQL database (Supabase works well), and a Groq API key.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

Create `backend/.env`:

```
GROQ_API_KEY=your_groq_key
DATABASE_URL=your_postgres_connection_string
JWT_SECRET=your_generated_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Generate a strong JWT secret with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Create the tables and start the server:

```bash
python -m database.init_db
uvicorn main:app --reload --port 8010
```

Interactive API docs at `http://127.0.0.1:8010/docs`.

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`:

```
VITE_API_URL=http://127.0.0.1:8010
```

Start it:

```bash
npm run dev
```

Open `http://localhost:5173`.

### Try it

1. Register an account.
2. Upload a CSV containing `date`, `description`, and `amount` columns (a sample is in `backend/data/`).
3. Ask a question, generate insights, or download a PDF report.

---

## Deployment

The app deploys as two Render services from the same repository.

**Backend — Web Service**
- Root directory: `backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment: the same variables as `backend/.env`, plus `PYTHON_VERSION=3.12.8`

**Frontend — Static Site**
- Root directory: `frontend`
- Build: `npm install && npm run build`
- Publish directory: `dist`
- Environment: `VITE_API_URL` set to the deployed backend URL

The deployed frontend's origin must be added to the CORS `allow_origins` list in `backend/main.py`, otherwise the browser blocks every API call.

---

## Project structure

```
finance-copilot/
├── backend/
│   ├── agents/          supervisor + specialist agents
│   ├── api/             auth, upload, chat routes
│   ├── database/        engine, session, table setup
│   ├── models/          SQLAlchemy models + Pydantic schemas
│   ├── services/        auth, parsing, request guards
│   └── main.py
└── frontend/
    └── src/             React app (auth, dashboard, API client)
```

---

## Notes

This is a portfolio project built to explore multi-agent LLM orchestration, natural-language database access, and the security considerations of letting a model generate SQL. Figures shown are derived from uploaded data and are not financial advice.