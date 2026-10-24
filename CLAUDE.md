# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

The SQLAlchemy models for the full data model exist, along with their repositories and an initial Alembic migration. The only feature route is signup (see "Auth" below). There are no tests yet.

## Layout and conventions

Every layer is a package. Its `__init__.py` re-exports the public names, and other code imports from the package (`from app.models import User`), not from the submodule.

- `app/core/`: shared infrastructure. `config.py` has a pydantic-settings `Settings`. Every field is required and comes from the environment or `.env` (copy `.env.example`), so the app won't import when one is missing. Use `settings.database_url` (a property built from the `DB_*` vars) wherever you need the connection string; don't put the URL itself in an env var. `database.py` has the async `engine`, `SessionLocal` (an `async_sessionmaker` with `expire_on_commit=False`) and `get_db`. `get_db` gives each request one `AsyncSession`, commits when the request succeeds and rolls back on an exception, so repositories only `flush`; they never commit. `main.py`'s lifespan disposes the engine on shutdown.
- All database access is async. Endpoints and repository methods are `async def` and `await` session calls. Never touch a lazy-loaded relationship (that raises `MissingGreenlet`); load it eagerly with `selectinload` or similar.
- `app/models/`: SQLAlchemy models, one module per entity, all subclassing `Base` from `models/base.py`. Register each new model in `models/__init__.py` so `Base.metadata` (and Alembic) can see it. Conventions:
  - Primary keys are `id: Mapped[uuid.UUID]` (default `uuid4`); foreign keys are `<entity>_id`. `Base.metadata` has a naming convention, so constraints get deterministic names.
  - Relationship annotations are strings, and the imports they need sit under `TYPE_CHECKING` to avoid import cycles.
  - Child FKs use `ondelete="CASCADE"`, and parent relationships use `cascade="all, delete-orphan", passive_deletes=True`, so deleting a User removes everything under it in the database.
  - Mode, status, sender, role and type fields are plain `String` columns; their allowed values aren't specified yet.
- `app/schemas/`: Pydantic request and response schemas, kept separate from the ORM models and re-exported from `schemas/__init__.py`.
- `app/repositories/`: data access, split into contract and implementation, one pair per aggregate:
  - `interfaces/<x>.py`: `<X>Repository(ABC)`, the database-agnostic contract. It holds the async `@abstractmethod` signatures and the docstrings describing behaviour.
  - `postgres/<x>.py`: `Postgres<X>Repository(<X>Repository)`, the SQLAlchemy `AsyncSession` implementation, with no docstrings of its own (the interface documents it).
  - To add or change a method, change the interface first, then every implementation. A missing method fails at instantiation.
  - A future database gets a sibling package (e.g. `mongo/`) that implements the same interfaces.
  - Each implementation imports only its own interface, `AsyncSession` and `app.models`; repositories never import or call each other. Logic that spans several repositories belongs in the caller (an endpoint, or a future service layer), and that caller shares the request's session through the DI providers. Child entities without a repository of their own are handled by their parent's repository:
  - `UserRepository` handles `UserPreferences` (`get_preferences`, `save_preferences`).
  - `ContextNodeRepository` handles `NodeSource` (`add_source`, `list_for_message`).
  - `HypothesisRepository` handles `HypothesisEvidence` (`add_evidence`, `list_evidence`).
  - `ContextEdgeRepository` is separate because edges are queried on their own.
  - `RefreshTokenRepository` (`add`, `get`, `revoke`, `revoke_all_for_user`) has its own repository, separate from `UserRepository`.
- Deletes cascade in the database (`passive_deletes`), so child objects already loaded in the same session aren't evicted. After deleting a parent, don't reuse its loaded children.
- `app/api/`: `deps.py` has the DI providers: `SessionDep`, plus a `get_<x>_repo` provider and an `<X>RepoDep` `Annotated` alias for each repository. Each alias is typed as the interface, and its provider returns the `Postgres…` implementation. That makes `deps.py` the only place that picks the database: route operations take `<X>RepoDep` parameters and never import `Postgres…` classes. In tests, override `get_db`, or a `get_<x>_repo` provider to substitute a fake. FastAPI caches `get_db` per request, so every repository in a request shares one session and one transaction. Endpoints take repositories through these aliases and never build sessions themselves. Versions live in `api/v1/`, `api/v2/` and so on. Each version's `__init__.py` builds an `api_router` from its feature routers (`endpoints/health.py` and the `auth/` package), and `main.py` mounts it under `settings.api_v1_prefix` (`/api/v1`).
- Routes so far: `/api/v1/health`, `/api/v1/health/db` (runs `SELECT 1`) and `POST /api/v1/auth/signup`.

## Auth

- `app/core/jwt.py` holds everything auth-related outside the routes:
  - Password hashing: Argon2 via pwdlib. It's CPU-heavy, so async code calls it through `run_in_threadpool`.
  - `create_access_token` / `create_refresh_token` / `verify_token(token, expected_type)`. Claims are `sub` (user id), `type`, `jti`, `iat` and `exp`. Every failure, including expiry, raises `jwt.InvalidTokenError`.
  - `hash_token` (SHA-256), plus the cookie helpers `set_auth_cookies` / `clear_auth_cookies`.
- Tokens travel in cookies, never in response bodies. Both cookies are `HttpOnly` and `SameSite=Lax`, with `Secure` set from `COOKIE_SECURE`. The `access_token` cookie has path `/`; the `refresh_token` cookie has path `{api_v1_prefix}/auth`, so it's only sent to auth routes.
- Refresh tokens are stored in `refresh_tokens`: `id` = the token's `jti`, and only the token's SHA-256 hash is kept. `verify_token` proves only that a token is genuine; the caller must also check the row (exists, hash matches, not revoked, not expired). Rotate on use: issue a new token, then `revoke(old_jti, replaced_by_id=new_jti)`. If an already-revoked token is presented, it's a reuse, so call `revoke_all_for_user`.
- Signup (`api/v1/auth/routes.py`) takes email (stored lowercased), username and password, and returns 409 if the email or username is already taken. A DB unique-constraint failure from a concurrent signup also maps to 409. Signup doesn't issue tokens or set cookies; that's left to the future login route.
- Password rules (8+ characters, uppercase, lowercase, digit, special character) are enforced on `SignupRequest` in `app/schemas/auth.py`, not in the database, because only the Argon2 hash is stored. Username has no format rules, by decision; it's only unique and non-null.

## Stack

FastAPI + Uvicorn, SQLAlchemy 2.x (asyncio, which needs greenlet), asyncpg (PostgreSQL), Alembic, pydantic / pydantic-settings (plus email-validator), PyJWT, pwdlib[argon2]. Configuration comes from `.env` (gitignored).

- Alembic uses the async template. `alembic/env.py` takes the URL from `settings.database_url` and the metadata from `app.models.Base` (`sqlalchemy.url` in `alembic.ini` is unused). Because it imports app settings, every `.env` variable must be set even to run migrations. Autogenerate drops any table not registered in `app/models/__init__.py`, so review each generated migration before applying it.

- Set `DB_DRIVER=postgresql+asyncpg`. Don't use `postgresql+psycopg` for the app: psycopg's async mode fails on Windows' default ProactorEventLoop ("Psycopg cannot use the 'ProactorEventLoop'"). psycopg / psycopg-binary are still installed and are only useful for sync tooling.
- Keep `requirements.txt` UTF-8. PowerShell's `pip freeze >` writes UTF-16, so use `pip freeze | Out-File -Encoding utf8 requirements.txt`.

## Commands (Windows, venv in `.venv/`)

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload        # docs at http://localhost:8000/docs
alembic revision --autogenerate -m "msg"   # review the file, then:
alembic upgrade head
alembic check                        # fails if models and DB differ
```

## Data model (`ER_DIAGRAM.excalidraw`)

The ER diagram is the spec for the schema. It's a large JSON file. To read the entity and attribute names, grep for `"text":` instead of opening the whole file.

The domain: a conversational assistant that builds a per-user context graph from chat messages, forms hypotheses about the user backed by evidence, and schedules reflections and notifications about those hypotheses.

Implemented in `app/models/`: entity (module) → table.

- **User** (`user.py` → `users`): email (unique, lowercased), username (unique), hashed_password, display_name (nullable; filled in later from the profile), phone_no, gender, date_of_birth, profile_picture, address_id. `age` is a derived Python property, not a column. **Address** is also defined in `user.py`, by request (the one exception to one-model-per-module); it maps to `addresses` (street, city, state, country, pin_code). `users.address_id` → `addresses.id` is nullable with `ON DELETE SET NULL`. User has N **RefreshToken** rows (`refresh_token.py` → `refresh_tokens`). 1:1 with **UserPreferences** (`user_preferences`, PK = `user_id`): default_mode, memory_allowed, reflection_allowed, notification_enabled.
- **Conversation** (`conversations`): user_id, started_at, ended_at, initial_mode. It has N **Message** rows (`messages`): conversation_id, sender, content, created_at, active_mode, memory_allowed (per message).
- **ContextNode** (`context_nodes`): user_id, node_type, label, review_status. **ContextEdge** (`context_edges`): from_node_id, to_node_id, relation_type. Together they form the per-user knowledge graph. Messages and nodes are M:N through **NodeSource** (`node_sources`, composite PK node_id + message_id).
- **Hypothesis** (`hypotheses`): user_id, statement_text, status, created_at, reviewed_at. It has N **HypothesisEvidence** rows (`hypothesis_evidence`): hypothesis_id, message_id, node_id, evidence_role. message_id and node_id are each nullable, but a CHECK requires at least one.
- **Reflection** (`reflections`): hypothesis_id, user_id, content_text, status, scheduled_for. It has N **Notification** rows (`notifications`): reflection_id, user_id, scheduled_at, delivery_status.

The preference flags (`memory_allowed`, `reflection_allowed`, `notification_enabled`) and the per-message `memory_allowed` are meant to gate the graph, reflection and notification pipelines. Respect them when implementing those flows.
