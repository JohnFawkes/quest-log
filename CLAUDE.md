# CLAUDE.md — Quest Log

## Project Overview

Quest Log is a gamified habit tracking web application with RPG theming. Users ("Adventurers") complete daily tasks ("Quests"), upload photo proof, and earn gems. Admins ("Guild Masters") assign quests, approve submissions, and manage a reward shop where users spend gems.

## Tech Stack

- **Backend:** Python 3.12, Flask, Flask-SQLAlchemy, Flask-Login, Authlib (Google OAuth)
- **Frontend:** Jinja2 templates, Tailwind CSS (CDN), FontAwesome 6.0
- **Database:** SQLite (`questlog.db` stored in `/data` directory)
- **Server:** Gunicorn (4 workers, `--preload`)
- **Notifications:** Apprise (Discord, Telegram, Slack, etc.)
- **Container:** Docker (Python 3.12-slim base), Docker Compose

## Architecture

This is a **monolithic single-file Flask application**. All models, routes, helpers, and configuration live in `app.py` (~800 lines).

### Key Files

| File | Purpose |
|---|---|
| `app.py` | Entire application: config, models, routes, helpers |
| `requirements.txt` | Python dependencies (8 packages, version-ranged) |
| `Dockerfile` | Production container image |
| `compose.yaml` | Production deployment (pulls from ghcr.io) |
| `compose-dev.yaml` | Local development (builds from source) |
| `.env.example` | Environment variable template |
| `templates/` | 8 Jinja2 HTML templates |
| `templates/layout.html` | Base template with nav, theme system, shared UI |
| `static/uploads/` | User-uploaded proof images |
| `.github/workflows/docker-ci.yml` | CI/CD pipeline |

### Database Models (SQLAlchemy)

- **User** — email, password_hash, name, picture, points (gems), is_admin, theme, force_password_change, last_penalty_check
- **Habit** — name, description, points_reward, assigned_user_id, schedule_type, schedule_days, interval_days, penalty settings
- **Completion** — user_id, habit_id, habit_name, image_filename, status (`pending`/`approved`/`rejected`/`penalty`), timestamp
- **Reward** — name, cost, description, icon, is_approved, is_demo, requested_by_id
- **Redemption** — user_id, reward_name, cost, timestamp

### Route Groups (~39 endpoints)

- **Auth:** `/login`, `/login/google`, `/authorize`, `/login/demo`, `/register`, `/logout`
- **Dashboard:** `/`, `/dashboard`, `/habit/<id>/complete`, `/settings/profile`
- **Rewards:** `/rewards`, `/rewards/request`, `/rewards/redeem/<id>`
- **Admin:** `/admin`, `/admin/habit/create`, `/admin/habit/delete/<id>`, `/admin/approve/<id>`, `/admin/reject/<id>`, `/admin/user/create`, `/admin/user/promote`, `/admin/reward/*`, `/setup`
- **Infrastructure:** `/health` (Docker healthcheck endpoint)
- **Static:** `/uploads/<filename>`

## Development Setup

### Prerequisites

- Python 3.12+
- Docker and Docker Compose (for containerized development)

### Run Locally (without Docker)

```bash
cp .env.example .env
# Edit .env with your values
pip install -r requirements.txt
python app.py
# App runs at http://localhost:5000
```

### Run with Docker Compose (development)

```bash
cp .env.example .env
docker compose -f compose-dev.yaml up --build
```

### Run with Docker Compose (production image)

```bash
docker compose up
```

### Default Admin Account

On first startup, the app creates a default admin:
- **Email:** `admin`
- **Password:** `admin`
- The admin is forced to change their password on first login.

### Demo Account

A read-only demo user (`demo@questlog.app`) is auto-created with sample data. Demo users cannot upload proofs, request rewards, or modify settings.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session secret (generate with `openssl rand -hex 32`) |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth client secret |
| `ADMIN_EMAIL` | No | Email that auto-receives admin rights on login |
| `PUBLIC_DOMAIN` | No | Public URL for OAuth redirects (default: `http://localhost:5000`) |
| `APPRISE_URLS` | No | Comma-separated Apprise notification URLs |
| `DISCORD_WEBHOOK_URL` | No | Discord webhook for direct notifications |
| `DATA_DIR` | No | Directory for SQLite database (default: app directory) |
| `PORT` | No | Port the application listens on (default: `5000`) |
| `TZ` | No | Timezone in IANA format (default: `UTC`) |

## CI/CD

GitHub Actions workflow (`.github/workflows/docker-ci.yml`):

1. **Triggers:** Push to `main` or PR against `main` (only when `.github/`, `Dockerfile`, `app.py`, `requirements.txt`, or `templates/` change)
2. **Build:** Docker image built with BuildX and GHA cache
3. **Test:** Container started, HTTP 200 check on homepage with retry
4. **Version:** Auto semantic version bump on push to main (mathieudutour/github-tag-action)
5. **Release:** GitHub Release created with changelog
6. **Publish:** Image pushed to `ghcr.io/johnfawkes/quest-log` (signed with Cosign)

PR builds get tagged `pr-<number>`. Main builds get `latest` + version tag.

## Testing

There is no unit or integration test suite. CI testing consists of:
- Docker build succeeds
- Container starts and responds with HTTP 200 on the homepage

To manually verify the app works:
```bash
docker compose -f compose-dev.yaml up --build
curl -L http://localhost:5000  # Should return 200
```

## Code Conventions

### Python / Flask

- Single `app.py` file — no blueprints or module separation
- SQLAlchemy ORM models defined at the top of `app.py`
- Routes use Flask decorators (`@app.route`, `@login_required`)
- All state-changing routes require POST (no GET-based mutations)
- Password hashing via Werkzeug's `scrypt` (generate_password_hash / check_password_hash)
- Form-based POST requests throughout (no JSON API)
- Flash messages for user feedback (auto-dismiss after 5s)
- `ProxyFix` middleware enabled for reverse proxy deployments
- `requests` library imported as `http_requests` to avoid name collision with Flask's `request`
- Uses `logging` module instead of bare `print()` for error reporting
- File upload validation via `ALLOWED_EXTENSIONS` whitelist (png, jpg, jpeg, gif, webp)

### Frontend / Templates

- All templates extend `templates/layout.html`
- Tailwind CSS utility classes (loaded via CDN, no build step)
- Theme system using CSS custom properties (`--bg-body`, `--btn-bg`, etc.)
- Available themes: dark (default), princess, forest — stored per-user in DB
- FontAwesome icons
- No JavaScript framework — form-based interactions only

### Database Patterns

- Auto-migration on startup: `perform_db_migration()` adds missing columns
- Race condition handling with `IntegrityError` catches (supports Gunicorn multi-worker)
- Foreign key relationships with cascading deletes
- Status enums as strings: `pending`, `approved`, `rejected`, `penalty`

### Scheduling System

Habits support four schedule types:
- **daily** — every day
- **weekly** — specific days of the week (0=Monday through 6=Sunday)
- **biweekly** — every other week on specific days
- **interval** — every X days from creation date

Key helper functions: `is_habit_due_on_date()`, `calculate_next_due_date()`, `check_missed_habits()`

## Important Considerations

- **No linter or formatter configured** — no flake8, black, ruff, or pre-commit hooks.
- **Single-file architecture** — all changes go into `app.py`. Keep this in mind when adding features; the file is already ~800 lines.
- **SQLite limitations** — no concurrent write support beyond what SQLite provides. The app uses `IntegrityError` handling for multi-worker safety.
- **File uploads** — stored in `static/uploads/`, served via a custom route with MIME type detection. Max upload size is 16MB. Only image extensions (png, jpg, jpeg, gif, webp) are allowed.
- **Demo user** — `demo@questlog.app` is special-cased throughout the codebase. Demo restrictions are checked inline in route handlers.
- **Docker security** — container runs as non-root `questlog` user. Healthcheck via `/health` endpoint.
- **Session cookies** — configured with `httponly=True` and `samesite=Lax` for security.
- **OAuth insecure transport** — `OAUTHLIB_INSECURE_TRANSPORT=1` is set globally to allow OAuth over HTTP in development. This should be reviewed for production hardening.
