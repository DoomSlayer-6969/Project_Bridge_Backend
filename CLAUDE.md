# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

Boilerplate only: there are no models, tests, or Alembic migrations yet. The data model is designed (see below) but not implemented.

## Layout and conventions

Every layer is a package. Its `__init__.py` re-exports the public names, and other code imports from the package (`from app.models import User`), not from the submodule.

- `app/core/`: shared infrastructure. `config.py` has a pydantic-settings `Settings`. Every field is required and comes from the environment or `.env` (copy `.env.example`), so the app won't import when one is missing. Use `settings.database_url` (a property built from the `DB_*` vars) wherever you need the connection string; don't put the URL itself in an env var. `database.py` has the async `engine`, `SessionLocal` (an `async_sessionmaker` with `expire_on_commit=False`) and `get_db`. `get_db` gives each request one `AsyncSession`, commits when the request succeeds and rolls back on an exception, so repositories only `flush`; they never commit. `main.py`'s lifespan disposes the engine on shutdown.
- All database access is async. Endpoints and repository methods are `async def` and `await` session calls. Never touch a lazy-loaded relationship (that raises `MissingGreenlet`); load it eagerly with `selectinload` or similar.
- `app/models/`: SQLAlchemy models, one module per entity, all subclassing `Base` from `models/base.py`. Register each new model in `models/__init__.py` so `Base.metadata` (and Alembic) can see it.
- `app/schemas/`: Pydantic request and response schemas, kept separate from the ORM models and re-exported from `schemas/__init__.py`.
- `app/repositories/`: data access. Subclass `BaseRepository[Model]` (get / list / add / delete) and set `model = ...`.
- `app/api/`: `deps.py` has the DI providers: `SessionDep`, plus one `get_<x>_repo` provider and an `Annotated` alias per repository. Endpoints take repositories through these aliases and never build sessions themselves. Versions live in `api/v1/`, `api/v2/` and so on. Each version's `__init__.py` builds an `api_router` from `endpoints/*.py` routers, and `main.py` mounts it under `settings.api_v1_prefix` (`/api/v1`).
- The only routes so far are `/api/v1/health` and `/api/v1/health/db` (the second runs `SELECT 1`).

## Stack

FastAPI + Uvicorn, SQLAlchemy 2.x (asyncio, which needs greenlet), asyncpg (PostgreSQL), Alembic, pydantic / pydantic-settings. Configuration comes from `.env` (gitignored).

- Set `DB_DRIVER=postgresql+asyncpg`. Don't use `postgresql+psycopg` for the app: psycopg's async mode fails on Windows' default ProactorEventLoop ("Psycopg cannot use the 'ProactorEventLoop'"). psycopg / psycopg-binary are still installed and are only useful for sync tooling.
- Keep `requirements.txt` UTF-8. PowerShell's `pip freeze >` writes UTF-16, so use `pip freeze | Out-File -Encoding utf8 requirements.txt`.

## Commands (Windows, venv in `.venv/`)

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload        # docs at http://localhost:8000/docs
alembic init alembic                 # not yet run
alembic revision --autogenerate -m "msg"; alembic upgrade head
```

## Data model (`ER_DIAGRAM.excalidraw`)

The ER diagram is the spec for the schema. It's a large JSON file. To read the entity and attribute names, grep for `"text":` instead of opening the whole file.

The domain: a conversational assistant that builds a per-user context graph from chat messages, forms hypotheses about the user backed by evidence, and schedules reflections and notifications about those hypotheses.

- **User** (user_id, email, display_name, phone, gender, date_of_birth/age, profile_picture, composite address: street/area/flat, city, state, country, pin code). 1:1 with **User_preferences** (default_mode, memory_allowed, reflection_allowed, notification_enabled).
- **Conversation** (convo_id, user_id FK, started_at, ended_at, initial_mode, memory_allowed). A User has N conversations.
- **Messages** (message_id, convo_id FK, sender, content, created_at, active_mode). A Conversation has N messages.
- **Context_node** (node_id, user_id FK, node_type, label, review_status) and **Context_edge** (edge_id, from_node_id, to_node_id, relation_type): the per-user knowledge graph. Messages and nodes are M:N through **Node_source** (composite PK node_id + message_id).
- **Hypothesis** (hypothesis_id, user_id FK, statement_text, status, creation/review time). Has N **Hypothesis_evidence** rows (evidence_id, hypothesis_id FK, message_id FK, node_id FK, evidence_role). Evidence links a hypothesis to both a source message and a context node.
- **Reflection** (reflection_id, hypothesis_id FK, user_id FK, content_text, status, scheduled_at) is about one hypothesis. **Notification** (notification_id, reflection_id FK, user_id FK, delivery_status) is sent for one reflection.

The preference flags (`memory_allowed`, `reflection_allowed`, `notification_enabled`) and the per-conversation `memory_allowed` are meant to gate the graph, reflection, and notification pipelines. Respect them when implementing those flows.
