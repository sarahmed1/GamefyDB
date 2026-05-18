# Frontend Stack Design — GamefyDB Web App

**Date:** 2026-05-18
**Status:** Approved (pending written-spec review)
**Scope:** Add a React + shadcn + Vite frontend that complements the existing Power BI dashboard, exposes the ETL/ML/chatbot capabilities, and is defensible as a PFE deliverable.

---

## 1. Goals & Non-Goals

### Goals

- Single web app covering **eight surfaces**: analytics dashboard (Overview, Transactions, Sessions, Stock, Members), forecasts UI (Prophet / SARIMA / XGBoost), Gemini chatbot, and admin (pipeline trigger + user management).
- **Complement** — not replace — the existing Power BI dashboard (`gamefyyy.pbix`, `SalesDashboard.pbit`).
- Real authentication with two roles (admin, viewer).
- Long-running operations (pipeline runs, forecast retrains) handled with background jobs + polling.
- Production-shaped local-dev setup; deployment is out of scope but the architecture is deploy-ready.

### Non-Goals (v1)

- No Redis / Celery — FastAPI `BackgroundTasks` suffices.
- No Postgres — SQLite is sized for the demo. Schema kept portable (SQLAlchemy + Alembic) so a future swap is a config change.
- No SSE / WebSocket — JSON request/response only.
- No i18n — English UI only.
- No mobile-specific layouts — responsive shadcn defaults only.
- No saved dashboards / user-customizable views.

---

## 2. Stack Decisions

| Concern | Choice | Rationale |
|---|---|---|
| Frontend bundler | **Vite 7** | Already scaffolded in `Gamefy/apps/web`. |
| UI framework | **React 19 + TypeScript** | Already scaffolded. |
| Monorepo | **Turborepo + bun workspaces** | Already scaffolded — `apps/web` + `packages/ui`. |
| Component library | **shadcn/ui + Tailwind v4** | Already scaffolded in `packages/ui`. |
| Charts | **shadcn Charts (Recharts)** | Themes via the same CSS variables as the rest of shadcn. Heatmaps built as a custom shadcn primitive on top of Recharts cells. ECharts is the documented escape hatch if Recharts proves insufficient for any specific chart; no ECharts in v1. |
| Routing | **React Router v7** | Familiar, biggest ecosystem, most shadcn tutorials assume it. |
| Server state | **TanStack Query** | Cache, dedupe, invalidate. |
| Tables | **TanStack Table** | Sort/filter/paginate for fact-table browsers; virtualization where row count justifies it. |
| Forms | **react-hook-form + zod** | Schema-validated forms for login, upload, admin user CRUD. |
| Toasts | **sonner** | shadcn default. |
| Date pickers | **react-day-picker via shadcn** | `<DatePicker>` and `<DateRangePicker>`. |
| Theming | **next-themes** | Light/dark toggle. Works in Vite despite the name. |
| Icons | **lucide-react** | Already in deps. |
| HTTP client | **native `fetch` + small typed wrapper** | No axios. |
| Backend | **FastAPI** | At repo root in `api/`, imports `gamefydb/`, `chatbot/`, `figures/` directly. |
| Auth library | **fastapi-users** | Cookie-based JWT strategy, async SQLAlchemy backend, role hooks. |
| User store | **SQLite** at `api/gamefydb.sqlite` via SQLAlchemy + Alembic. |
| Long jobs | **FastAPI `BackgroundTasks` + Job model + polling** | No external queue. |

---

## 3. Repo Layout

```
GamefyDB/
├── api/                          NEW — FastAPI server
│   ├── main.py                   app entry, CORS, router includes, startup cache build
│   ├── deps.py                   get_db, current_user, require_admin
│   ├── db.py                     SQLAlchemy engine + Base, sqlite:///api/gamefydb.sqlite
│   ├── models/
│   │   ├── user.py               User (id, email, hashed_password, role, created_at)
│   │   └── job.py                Job (id, user_id, kind, status, progress, log, result, created_at, finished_at)
│   ├── schemas/                  pydantic request/response models
│   ├── routers/
│   │   ├── auth.py               fastapi-users routes
│   │   ├── facts.py              /api/facts/{table}
│   │   ├── dims.py               /api/dims/{table}
│   │   ├── kpis.py               /api/kpis/overview, /heatmap, /by-terminal, /by-cashier
│   │   ├── forecasts.py          /api/forecasts/{model}, /compare, /retrain
│   │   ├── chat.py               /api/chat, /api/chat/history
│   │   ├── pipeline.py           /api/pipeline/upload, /api/pipeline/run
│   │   ├── jobs.py               /api/jobs, /api/jobs/{id}
│   │   └── admin.py              /api/admin/users/*
│   ├── services/                 thin wrappers around gamefydb/, chatbot/, figures/
│   │   ├── data_cache.py         in-memory DataFrame cache, rebuild on pipeline run
│   │   ├── kpis.py               pandas aggregations
│   │   ├── forecasts.py          calls into figures/forecasting module
│   │   └── jobs.py               background worker, Future tracking
│   ├── alembic/                  migrations
│   └── tests/                    pytest with TestClient + in-memory SQLite
│
├── Gamefy/                       existing scaffold, kept
│   ├── apps/web/
│   │   ├── src/
│   │   │   ├── main.tsx
│   │   │   ├── routes/           React Router v7 route tree
│   │   │   ├── pages/            one per route segment
│   │   │   ├── components/
│   │   │   │   ├── shell/        IconRail, SecondaryPanel, TopBar, ProtectedRoute
│   │   │   │   ├── charts/       wrappers around shadcn Charts
│   │   │   │   ├── tables/       TanStack Table presets per fact
│   │   │   │   └── chat/         Chatbot UI primitives
│   │   │   ├── lib/
│   │   │   │   ├── api.ts        typed fetch client, credentials: 'include'
│   │   │   │   ├── auth.ts       useAuth, useLogin, useLogout
│   │   │   │   └── jobs.ts       useJob(id) polling hook
│   │   │   └── styles/
│   │   ├── vite.config.ts        proxy /api → http://localhost:8000
│   │   └── package.json
│   └── packages/ui/              shadcn primitives (existing)
│
├── gamefydb/  chatbot/  figures/  unchanged — imported by api/services/
├── run.py                        unchanged CLI entry
└── docs/superpowers/specs/       this design doc
```

**Three dev processes:**

1. `uvicorn api.main:app --reload` on `:8000`
2. `bun run dev` (in `Gamefy/apps/web`) on `:5173`, proxies `/api/*` → `:8000`
3. Browser on `:5173`

---

## 4. Navigation & Pages

**Shell — icon rail + secondary panel pattern:**

```
┌──────────────────────────────────────────────────────────────┐
│ TopBar: brand · date range picker · user menu · theme toggle │
├────┬───────────┬─────────────────────────────────────────────┤
│ ◆  │ Today     │                                             │
│ ≣  │ Terminal  │           Active sub-view canvas            │
│ ◷  │ Cashier   │              (charts, tables)               │
│ ⬚  │ Heatmap   │                                             │
│ ☺  │           │                                             │
│ ↗  │           │                                             │
│ 💬 │           │                                             │
│ ⚙  │           │                                             │
└────┴───────────┴─────────────────────────────────────────────┘
```

Icon rail switches the active **section**; secondary panel lists sub-views within that section.

**Route tree:**

```
/login                            public, redirects to / on success
/                                 redirect → /overview/today

/overview/today                   KPIs, today's totals, top items
/overview/terminal                by-terminal breakdown
/overview/cashier                 by-cashier breakdown
/overview/heatmap                 hour × weekday heatmap

/transactions                     fact_cash_transactions browser
/transactions/aggregates          revenue / method aggregates

/sessions                         fact_sessions browser
/sessions/aggregates              duration, terminal utilization
/sessions/members                 member vs walk-in split

/stock                            fact_stock_movements browser
/stock/aggregates                 movement totals by item

/members                          dim_member directory
/members/stats                    fact_member_stats charts

/forecasts/prophet                Prophet daily forecast + wMAPE
/forecasts/sarima                 SARIMA
/forecasts/xgboost                XGBoost
/forecasts/compare                side-by-side wMAPE comparison

/chat                             Gemini function-calling chatbot

/admin/pipeline                   upload .xls + trigger run             admin only
/admin/jobs                       job history + live status             admin only
/admin/users                      CRUD users                            admin only
```

**Role gating:**

- `viewer` sees everything except `/admin/*` and write actions (run pipeline, upload, retrain).
- Enforced both client-side (`<ProtectedRoute role="admin">` + conditional render) and server-side (FastAPI `require_admin` dependency).

**State management:**

- Server state → TanStack Query, keyed by route + URL search params.
- Auth state → `useAuth()` hook backed by `GET /api/auth/me`, cached in Query.
- URL state → date range, filters, pagination live in query string (`?from=&to=&terminal=...`) so refresh/share preserves the view.
- No global store (Zustand/Redux) in v1.

---

## 5. API Surface

All endpoints under `/api`, JSON-in/JSON-out except `/api/pipeline/upload` (multipart) and the chat endpoint (JSON in v1, SSE deferred).

```
Auth
  POST   /api/auth/login                       cookie set, httpOnly + SameSite=Lax
  POST   /api/auth/logout
  GET    /api/auth/me                          current user + role
  POST   /api/auth/register                    admin-only

KPIs
  GET    /api/kpis/overview?from&to            totals, top items, top terminals
  GET    /api/kpis/heatmap?from&to             hour × weekday matrix
  GET    /api/kpis/by-terminal?from&to
  GET    /api/kpis/by-cashier?from&to

Facts (paged, filtered, sortable)
  GET    /api/facts/cash?from&to&terminal&cashier&method&page&size&sort
  GET    /api/facts/sessions?...
  GET    /api/facts/stock?...
  GET    /api/facts/members?...

Dims
  GET    /api/dims/{terminal|cashier|item|member}

Forecasts
  GET    /api/forecasts/{prophet|sarima|xgboost}?horizon=N&target=revenue|sessions
  GET    /api/forecasts/compare?horizon=N      wMAPE table for all three
  POST   /api/forecasts/{model}/retrain        → returns { job_id }

Chatbot
  POST   /api/chat                             { messages[] } → { reply, tool_calls[] }
  GET    /api/chat/history                     persisted past sessions (per-user)

Pipeline (admin)
  POST   /api/pipeline/upload                  multipart .xls files
  POST   /api/pipeline/run                     → returns { job_id }

Jobs
  GET    /api/jobs                             list current user's jobs
  GET    /api/jobs/{id}                        { status, progress, log_tail, result_url }

Admin
  GET    /api/admin/users
  POST   /api/admin/users
  PATCH  /api/admin/users/{id}
  DELETE /api/admin/users/{id}
```

**Data source for KPIs/facts/dims:** the API runs `gamefydb.transformer.transform()` on the latest cleaned data **once at startup** and caches the star-schema DataFrames in memory. A successful pipeline-run job triggers a cache refresh. No SQL warehouse needed for v1.

---

## 6. Auth Flow

1. `POST /api/auth/login` validates email + password against the `User` table (bcrypt). Sets `gamefydb_session` httpOnly cookie containing a 24-hour JWT.
2. Every subsequent request carries the cookie; `current_user` dependency decodes the JWT and loads the user from SQLite.
3. `require_admin` dependency wraps admin-only routes; returns 403 for viewers.
4. Frontend uses `credentials: 'include'` on every fetch; a route guard redirects to `/login` on 401.
5. Logout clears the cookie and invalidates the auth query.

Cookie config: `HttpOnly`, `SameSite=Lax`, `Secure` in prod, path `/`.

---

## 7. Long-Running Jobs

**Job model:**

```python
class Job(Base):
    id: UUID                       # primary key
    user_id: FK(User)
    kind: str                      # "pipeline_run" | "forecast_retrain" | ...
    status: str                    # "pending" | "running" | "done" | "failed"
    progress: int                  # 0..100
    log: str                       # tail of stdout
    result: JSON                   # optional payload
    created_at: datetime
    finished_at: datetime | None
```

**Flow:**

1. `POST /api/pipeline/run` (or `/api/forecasts/{model}/retrain`) creates a `Job` row with `status=pending` and dispatches the work via `BackgroundTasks` into a single worker thread.
2. Worker updates `progress` and appends to `log` as it runs.
3. Frontend `useJob(id)` polls `GET /api/jobs/{id}` every 1s while `status ∈ {pending, running}`, then stops.
4. On `done`, frontend invalidates affected TanStack Query keys (e.g., `kpis/*`, `facts/*`) so charts refresh.
5. In-memory `dict[uuid, Future]` lets the app cancel pending work on graceful shutdown.

**Concurrency:** single worker thread in v1 (jobs are serialized). Two simultaneous pipeline runs queue.

---

## 8. Data Flow Examples

**Read — dashboard chart load:**

```
Browser /overview/today
   → React Router renders OverviewToday
   → useQuery(['kpis/overview', {from, to}], fetch('/api/kpis/overview?...'))
   → Vite proxies → :8000
FastAPI /api/kpis/overview
   → current_user dependency (cookie → JWT → SQLite users)
   → services/kpis.py.get_overview(from, to)
   → reads cached DataFrames
   → pandas aggregations → pydantic response
Browser ← JSON ← TanStack Query caches
```

**Write — pipeline run:**

```
Admin clicks "Re-run pipeline"
   → POST /api/pipeline/run                     → { job_id }
   → useJob(job_id) starts polling /api/jobs/{id} every 1s
Worker thread:
   ingest_all() → progress=25, log="ingested cash"
   clean_all()  → progress=50
   transform()  → progress=75, replaces in-memory cache
   write_all()  → progress=100, status=done, result_url=/api/outputs/{run_id}
Frontend → sonner toast "Pipeline complete · 3.2s"
        → Query invalidates kpis/*, facts/*
```

**Chat:**

`POST /api/chat` forwards messages to `chatbot/agent.py` (the Gemini function-calling rewrite, see `2026-05-18-chatbot-tool-calling-design.md`). Tool calls inside `agent.py` query the cached DataFrames directly — no extra plumbing.

---

## 9. Testing

**Backend (pytest):**

- `TestClient` against the FastAPI app, in-memory SQLite, fixtures for a seeded admin + viewer and a tiny pre-built DataFrame cache.
- One test per router: auth (login/logout/me, role enforcement), facts (filters + paging), kpis (aggregation correctness on the fixture), jobs (lifecycle pending → running → done), pipeline (job dispatch), admin (CRUD users).
- Target ~20 tests; not chasing coverage.

**Frontend (Vitest + RTL + Playwright):**

- Vitest unit tests for `lib/api.ts`, `useAuth`, `useJob`.
- One Playwright smoke test: login → land on `/overview/today` → see a chart render.
- ~5 component tests + 1 e2e.

**Boundaries that matter most:** auth dependency, role gating, job state machine, cache-refresh-after-pipeline-run.

---

## 10. Deployment (out of v1 scope, documented)

- `docker-compose.yml` with two services: `api` (uvicorn + gunicorn workers) and `web` (nginx serving `Gamefy/apps/web/dist`).
- nginx routes `/api/*` to api, everything else to the static web build.
- SQLite mounted as a volume; `excel/` mounted read-only.

---

## 11. Open Questions / Future Work

- **Output file downloads** — `result_url` on jobs returns the generated CSV/Excel. Streaming endpoint or pre-signed local-fs link? Defer to plan.
- **Chat history persistence** — schema for `chat_session` and `chat_message` tables; reuse `Job`-style polling for streaming later.
- **Saved views** — let users persist their filter combinations. Out of v1; revisit after defense.
- **SSE for chat** — defer until JSON response feels insufficient.
