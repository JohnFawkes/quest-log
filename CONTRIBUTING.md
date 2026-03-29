# Contributing to Quest Log

All contributions are welcome — bug fixes, new features, documentation improvements, and theme ideas.

---

## Table of Contents

1. [Getting started](#getting-started)
2. [Project structure](#project-structure)
3. [Making changes](#making-changes)
4. [Commit conventions](#commit-conventions)
5. [Branch naming](#branch-naming)
6. [Submitting a pull request](#submitting-a-pull-request)
7. [Coding style](#coding-style)
8. [The RPG theme rule](#the-rpg-theme-rule)
9. [Reporting bugs and requesting features](#reporting-bugs-and-requesting-features)

---

## Getting started

### Option 1: Docker Compose (recommended)

This is the fastest path to a working dev environment.

```bash
git clone https://github.com/JohnFawkes/quest-log.git
cd quest-log

cp .env.example .env
# Edit .env — at minimum set SECRET_KEY

docker compose -f compose-dev.yaml up --build
```

The app builds from your local source and runs at **http://localhost:5000**.

Default credentials on first run:
- **Username:** `admin`
- **Password:** `admin`
  You will be prompted to change both immediately.

A demo account (`demo@questlog.app`) is seeded automatically with sample quests and gems.

### Option 2: Local Python

Requires Python 3.12+.

```bash
git clone https://github.com/JohnFawkes/quest-log.git
cd quest-log

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env — at minimum set SECRET_KEY

python app.py
```

App runs at **http://localhost:5000** in Flask's development server.

### Verifying your setup

```bash
curl -L http://localhost:5000     # Should return HTTP 200
curl http://localhost:5000/health  # Should return HTTP 200
```

---

## Project structure

```
quest-log/
├── app.py                  # Entire application — all models, routes, helpers
├── requirements.txt        # Python dependencies
├── Dockerfile              # Production container
├── compose.yaml            # Production deployment (pulls ghcr.io image)
├── compose-dev.yaml        # Local development (builds from source)
├── .env.example            # Environment variable template
├── templates/              # Jinja2 HTML templates
│   └── layout.html         # Base template — nav, theme system
├── static/
│   └── uploads/            # User-uploaded proof images (gitignored)
├── screenshots/            # Auto-generated CI screenshots (do not edit manually)
└── .github/
    └── workflows/
        ├── docker-ci.yml   # Main CI: build → test → version → publish
        └── pr-build.yml    # PR label-triggered builds
```

`app.py` is intentionally a single-file monolith (~2000 lines). All new code goes into `app.py`.

---

## Making changes

1. **Fork** the repository and create a branch (see [Branch naming](#branch-naming)).
2. **Make your changes** in `app.py`, templates, or static files.
3. **Update documentation** — this is required, not optional:
   - Add an entry to `CHANGELOG.md` under the top versioned section (e.g. `## [v0.3.0] - 2026-03-29`) in the correct heading (`Added`, `Fixed`, `Changed`, `Removed`). If none exists yet, create one. There is no `[Unreleased]` section.
   - Update `README.md` if you added a feature or changed existing behavior.
4. **Test locally** using one of the setup options above.
5. **Open a pull request** against `main`.

---

## Commit conventions

Quest Log uses [Conventional Commits](https://www.conventionalcommits.org/). Every commit message must start with a lowercase type prefix.

### Format

```
<type>: <short imperative description>

[optional body]

[optional footer: Closes #123]
```

### Types

| Type | Use for |
|---|---|
| `feat:` | A new feature visible to users |
| `fix:` | A bug fix |
| `docs:` | Documentation changes only (README, CHANGELOG, CLAUDE.md) |
| `style:` | Template/CSS changes with no logic changes |
| `refactor:` | Code restructuring with no behavior change |
| `perf:` | Performance improvements |
| `chore:` | Maintenance tasks: dependency bumps, CI tweaks, build config |
| `ci:` | Changes to GitHub Actions workflows only |

### Rules

- **Lowercase type** — `feat:` not `Feat:` or `FEAT:`
- **Imperative mood** — "add gem multiplier" not "added gem multiplier"
- **No period** at the end of the subject line
- **72-character limit** on the subject line
- **`Closes #N`** in the footer for issues, not the subject line

### Examples

```
feat: add streak bonus multiplier per quest

fix: prevent path traversal in avatar SVG routes

docs: update README with Apprise notification setup

chore: bump gunicorn to 23.1.0

ci: add Playwright screenshot capture on push to main
```

---

## Branch naming

Use a prefix matching the commit type, followed by a short slug.

| Prefix | Use for |
|---|---|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `docs/` | Documentation-only changes |
| `chore/` | Maintenance, dependency updates |
| `ci/` | Workflow changes |
| `refactor/` | Code restructuring |

Examples:

```
feat/midnight-quest-report
fix/avatar-weapon-alignment
docs/improve-contributing-guide
chore/bump-flask-3-2
ci/split-trivy-scan-job
```

---

## Submitting a pull request

1. Push your branch and open a PR against `main`.
2. Fill out the PR template — all checklist items should be completed before requesting review.
3. CI runs automatically via `docker-ci.yml`:
   - Builds the Docker image from source
   - Runs a container smoke test (HTTP 200 on homepage and `/health`)
   - Takes demo screenshots and commits them (on push to `main` only)
   - Runs a Trivy vulnerability scan
   - Publishes to `ghcr.io` (on push to `main` only)
4. You can trigger a manual build by applying the `BUILD` label to your PR. Use `PUSH` to also push to the registry.
5. PRs are reviewed by `@JohnFawkes`. All PRs will receive a response, though there is no fixed timeline.

---

## Coding style

There is no linter or formatter configured. Follow the patterns already present in `app.py`.

### Python

- **PEP 8** spacing and naming — functions are `snake_case`, classes are `PascalCase`.
- **POST for mutations** — all state-changing routes use POST; no GET-based mutations.
- **Flash messages** for user-facing feedback (auto-dismiss after 5 seconds in the template).
- **`logging` module** for error reporting — do not use bare `print()`.
- **`requests` is imported as `http_requests`** to avoid collision with Flask's `request`.
- **File uploads** — validate against `ALLOWED_EXTENSIONS` whitelist; use `secure_filename` from Werkzeug.
- **Passwords** use Werkzeug's `scrypt` via `generate_password_hash` / `check_password_hash`.
- **Avoid new dependencies** unless necessary — open an issue to discuss before building around a new package.

### Templates (Jinja2 / HTML)

- All templates extend `templates/layout.html`.
- Use **Tailwind CSS utility classes** — loaded via CDN, no build step required.
- Use **FontAwesome** for icons (already loaded in layout).
- No JavaScript framework. Interactions are form-based. Avoid adding JS unless absolutely necessary.
- Theme system uses CSS custom properties (`--bg-body`, `--btn-bg`, etc.) defined per theme in `layout.html` — new UI elements should use these variables, not hardcoded colors.

### Database

- All schema changes go in `perform_db_migration()` — the app auto-migrates on startup.
- Foreign key relationships should use `cascade="all, delete-orphan"` where appropriate.
- Wrap multi-worker-unsafe operations in `try/except IntegrityError`.

---

## The RPG theme rule

Quest Log uses a consistent RPG vocabulary. When adding UI text, notifications, or documentation, use the established terms:

| Use this | Not this |
|---|---|
| Adventurer | User / Player |
| Guild Master | Admin / Administrator |
| Quest | Task / Habit |
| Gem | Point / Credit / Token |
| Guild Hall | Admin panel |
| Proof of Valor | Proof / Submission / Upload |
| Chronicle | Stats / History |

This applies to:
- Visible UI text in templates
- Notification messages sent via Apprise
- Flash messages
- README and CHANGELOG prose

It does **not** apply to:
- Code identifiers (`user`, `admin`, `habit`, `points` in Python/SQL are intentional — changing them would break things)
- Technical documentation like `CLAUDE.md`
- Commit messages and PR descriptions (use plain English there)

When in doubt: if a user sees it, use the RPG term. If only a developer sees it, plain English is fine.

---

## Reporting bugs and requesting features

- **Bugs:** [Open a bug report](../../issues/new?template=bug_report.yml)
- **Features:** [Open a feature request](../../issues/new?template=feature_request.yml)
- **Questions:** [Start a discussion](../../discussions)

Search existing issues and discussions before opening a new one.
