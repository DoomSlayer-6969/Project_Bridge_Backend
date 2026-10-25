# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

The SQLAlchemy models for the full data model exist, along with their repositories and an initial Alembic migration. The only feature routes are the auth routes (signup, login, logout, refresh) and `users/me` (GET and PATCH; see "Auth" below). There are no tests yet.

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
  - `UserRepository` handles `UserPreferences` (`get_preferences`, `save_preferences`) and the user's `Address` (`get_with_address`, `update`, `delete_address`).
  - `ContextNodeRepository` handles `NodeSource` (`add_source`, `list_for_message`).
  - `HypothesisRepository` handles `HypothesisEvidence` (`add_evidence`, `list_evidence`).
  - `ContextEdgeRepository` is separate because edges are queried on their own.
  - `RefreshTokenRepository` (`add`, `get`, `revoke` → bool, `revoke_all_for_user`) has its own repository, separate from `UserRepository`.
- Deletes cascade in the database (`passive_deletes`), so child objects already loaded in the same session aren't evicted. After deleting a parent, don't reuse its loaded children.
- `app/api/`: `deps.py` has the DI providers: `SessionDep`, plus a `get_<x>_repo` provider and an `<X>RepoDep` `Annotated` alias for each repository. Each alias is typed as the interface, and its provider returns the `Postgres…` implementation. That makes `deps.py` the only place that picks the database: route operations take `<X>RepoDep` parameters and never import `Postgres…` classes. In tests, override `get_db`, or a `get_<x>_repo` provider to substitute a fake. FastAPI caches `get_db` per request, so every repository in a request shares one session and one transaction. Endpoints take repositories through these aliases and never build sessions themselves. Versions live in `api/v1/`, `api/v2/` and so on. Each version's `__init__.py` builds an `api_router` from its feature routers (`endpoints/health.py` and the `auth/` and `users/` packages), and `main.py` mounts it under `settings.api_v1_prefix` (`/api/v1`).
- Routes so far: `/api/v1/health`, `/api/v1/health/db` (runs `SELECT 1`), `POST /api/v1/auth/signup`, `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `POST /api/v1/auth/refresh`, `GET /api/v1/users/me` and `PATCH /api/v1/users/me` (both protected).

## Auth

- `app/core/jwt.py` holds everything auth-related outside the routes:
  - Password hashing: Argon2 via pwdlib. It's CPU-heavy, so async code calls it through `run_in_threadpool`.
  - `create_access_token` / `create_refresh_token` / `verify_token(token, expected_type)`. Claims are `sub` (user id), `type`, `jti`, `iat` and `exp`. Every failure, including expiry, raises `jwt.InvalidTokenError`.
  - `hash_token` (SHA-256), plus the cookie helpers `set_auth_cookies` / `clear_auth_cookies`.
- Tokens travel in cookies, never in response bodies. Both cookies are `HttpOnly` and `SameSite=Lax`, with `Secure` set from `COOKIE_SECURE`. The `access_token` cookie has path `/`; the `refresh_token` cookie has path `{api_v1_prefix}/auth`, so it's only sent to auth routes.
- Refresh tokens are stored in `refresh_tokens`: `id` = the token's `jti`, and only the token's SHA-256 hash is kept. `verify_token` proves only that a token is genuine; the caller must also check the row (exists, hash matches, not revoked, not expired). Rotate on use: issue a new token, then `revoke(old_jti, replaced_by_id=new_jti)`. If an already-revoked token is presented, it's a reuse, so call `revoke_all_for_user`.
- Signup (`api/v1/auth/routes.py`) takes email (stored lowercased), username and password, and returns 409 if the email or username is already taken. A DB unique-constraint failure from a concurrent signup also maps to 409. Signup doesn't issue tokens or set cookies; login does.
- Login (`POST /api/v1/auth/login`, same file) takes `password` plus exactly one of `email` / `username` (`LoginRequest` returns 422 otherwise). Email is matched lowercased; username is matched exactly, case included. Unknown users still get a dummy Argon2 check, and every failure returns the same 401 "Invalid credentials", so neither timing nor message reveals whether an account exists. On success, login inserts a `refresh_tokens` row, sets both cookies, and returns `{id, email, username}`. It doesn't revoke the user's other sessions.
- Logout (`POST /api/v1/auth/logout`, same file) reads the `refresh_token` cookie and always clears both cookies and returns 204, even when the cookie is missing, invalid, expired, mismatched or already revoked. It doesn't require an access token. If the token's row is active, it revokes only that session (`replaced_by_id` stays NULL). If the token was already rotated (`replaced_by_id` set), it treats this as reuse and calls `revoke_all_for_user`. The access token isn't stored, so it stays valid until it expires (15 min), by decision; only its cookie is removed.
- Refresh (`POST /api/v1/auth/refresh`, same file) rotates the token on every use. It adds the new row, then `revoke(old, replaced_by_id=new)`, sets new cookies and returns 204 with no body. Each new refresh token gets a fresh 7 days (sliding sessions). Every failure returns 401 "Invalid refresh token":
  - Missing, invalid, expired, mismatched or logged-out token: clear both cookies.
  - Rotated token presented again more than `REFRESH_REUSE_GRACE_PERIOD` (10 s) after its rotation: treated as theft, so `revoke_all_for_user` plus clear cookies.
  - Within the grace period, or losing a concurrent rotation: **don't** clear cookies, because the browser may already hold the winning request's new ones. The frontend should retry once.
  - `revoke` returns `False` when the row was already revoked (its UPDATE only matches `revoked_at IS NULL`), so only one concurrent request can rotate a token. The loser raises, which rolls back its new row.
  - Failures that change the database (revoke-all) or cookies are **returned** as a `JSONResponse`, not raised. A raised `HTTPException` makes `get_db` roll back, and FastAPI drops any cookies set on the injected `Response`.
  - Grace-period math needs time-zone-aware `revoked_at` (Postgres). SQLite returns naive datetimes, so test these paths on Postgres.
- **Protecting a route:** take a `user: CurrentUserDep` parameter (from `app/api/deps.py`). `get_current_user` reads the `access_token` cookie, runs `verify_token(..., "access")` and loads the user. Missing, invalid, expired or wrong-type tokens, and deleted users, all get 401 "Not authenticated". It doesn't check the database for a logged-out session, so a copied access token works until it expires (accepted tradeoff).
- `GET /api/v1/users/me` (`app/api/v1/users/routes.py`) returns `UserProfileResponse` (`app/schemas/user.py`): the profile fields, the derived `age` and the nested `address` (or null), never the password hash. Both `/me` routes reload the user with `UserRepository.get_with_address` (selectinload), because `CurrentUserDep` loads it without the address. Profile routes belong in this `users` package; auth flows go in `auth`.
- `PATCH /api/v1/users/me` (`UserProfileUpdateRequest`) fills in the details signup doesn't collect. It's a partial update: only fields present in the body change (`model_fields_set`), and `null` clears one. Unknown fields (e.g. `username`, `password`) are ignored.
  - Editable: `display_name`, `phone_no` (optional `+`, then 7-15 digits), `gender` (`male` / `female` / `other` / `prefer_not_to_say`), `date_of_birth` (not in the future), `profile_picture` (http(s) URL, at most 2048 chars, stored as a string), `address`, `email`. Strings are stripped, must be non-empty and fit their column length.
  - `address` must be complete (all five fields, matching the NOT NULL columns). It's created if the user has none, otherwise updated in place (same row). `address: null` unlinks it and deletes the row via `delete_address`, which only marks it; the following `update` flushes it.
  - Changing `email` requires `current_password` (422 without it; 401 "Incorrect password" if wrong). The new email is lowercased; 409 if another account has it, including a unique-constraint race at flush. The email can't be set to null. The session isn't affected: tokens carry the user id, not the email.
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
