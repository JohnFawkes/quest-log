# Changelog

All notable changes to Quest Log are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v0.3.1] - 2026-06-26

### Fixed
- Security: path traversal in `/uploads/<filename>` — route now sanitises the filename with `secure_filename()` before passing it to `send_from_directory`, and returns 404 for empty/invalid names.
- Security: NaN/Infinity injection — `streak_multiplier` from form input is now validated with `math.isnan`/`math.isinf`; invalid or non-positive values fall back to `2.0`.
- Security: raw HTML in token-based approve/reject responses — `quick_approve` and `quick_reject` now use `render_template_string` with Jinja2 auto-escaping instead of manually-constructed f-string HTML.
- Security: shell injection in CI — `${{ github.ref_name }}` in the screenshot commit step is now passed through an `env:` variable (`BRANCH_NAME`) and quoted in the `run:` script, preventing expression injection.

## [v0.3.0] - 2026-03-29

### Added
- GitHub community health files: issue templates (bug report, feature request), PR template, `CONTRIBUTING.md`, `SECURITY.md`, `CODEOWNERS`, and Dependabot config for GitHub Actions updates.
- Reward Redemption Log in Guild Hall — Guild Masters can now see the 50 most recent reward claims in a new table in the admin panel, showing adventurer name, reward name, gems spent, and timestamp.
- Midnight penalty record creation — the midnight scheduler now runs `check_missed_habits` for every adventurer, ensuring penalty records exist for all missed quests regardless of whether the user loads the dashboard; `check_missed_habits` expanded to cover all habits (not just penalty-enabled ones) so every missed quest gets a record for accurate stats; gem deduction still only applies to habits with penalties enabled.
- Chronicle (Stats Dashboard) — new `/stats` page for every adventurer showing gem/coin earnings and quest completions/failures across Today, This Week, This Month, This Year, and All Time, plus a rolling-average table (per day/week/month/year). Guild Masters get `/admin/stats` (Guild Chronicle) with an at-a-glance table for every adventurer and drill-down links to each player's full stats. Accessible via the "Stats" nav link and a "Guild Chronicle" button in the Guild Hall.
- Midnight Quest Report — a background scheduler sends a daily Apprise notification at midnight (local timezone) listing missed quests from the previous day and all quests due today; uses a DB-backed date key to deduplicate across Gunicorn workers.
- Quest Calendar — new `/calendar` page (linked in nav) shows 5 weeks of upcoming quests in a grid, respecting the configured week start day.
- Auto-backup — app writes a daily zip of `questlog.db` to `/backups/` (configurable via `BACKUP_DIR` env var), keeping the 7 most recent backups; backup is triggered on the first request of each day.
- Admin General Settings panel — Guild Masters can now configure Apprise notification URLs, Discord webhook URL, and week start day directly from the Guild Hall UI (DB values override env vars).
- Discord bot avatar injection — `_build_apprise()` now automatically appends `avatar_url` to any `discord://` Apprise URL when a Notification Icon URL is configured, so the bot posts with the custom avatar instead of the default Apprise icon.
- README Backups section — documents `docker cp` extraction, volume mounting, and the `BACKUP_DIR` env var.

### Removed
- Google SSO — removed Google OAuth login (`/login/google`, `/authorize`), the Google-to-local account migration route (`/settings/convert-to-local`), all related config (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `ADMIN_EMAIL`), and the `authlib` dependency.
- Standalone Discord webhook — removed the dedicated `DISCORD_WEBHOOK_URL` env var and its special-case handling in `_build_apprise()`; Discord can be configured via `APPRISE_URLS` using the `discord://` scheme instead.

### Changed
- Notification Settings panel — Apprise URLs moved from General Settings into the Notification Settings section so all notification config lives in one place; General Settings now only contains Week Start Day.
- Docker — `questlog` user now has a proper home directory (`/home/questlog`) to resolve Gunicorn control server permission errors; `/backups` directory created in image and mounted as a named volume in `compose.yaml`.

### Fixed
- Pending quest not visible to user after proof upload — dashboard timestamp range queries were comparing local-timezone-aware datetimes against naive UTC values stored in the database; SQLAlchemy's SQLite driver strips timezone offsets without converting, causing the range check to fail for non-UTC users (especially UTC-negative timezones in the evening). All date-range filters in `dashboard`, `check_missed_habits`, and `_send_midnight_notifications` now convert local midnight boundaries to naive UTC before querying.
- Quest rejection notifications — `reject_completion` and `quick_reject` (token link) were missing `send_notification` calls; rejecting a quest now fires an ❌ notification to all configured channels.
- Avatar UI — spell slot no longer shows a redundant "None" unequip card; use the owned "No Aura" item instead.
- Avatar SVG — iron helm raised 10 px so the brow ridge clears the character's eyes.
- Avatar SVG — ranger hood redesigned as a split-panel cowl (left/right panels + crown + chin wrap) leaving the face fully visible.
- Avatar SVG — princess dress arm paths widened at the lower section (left inner edge x 56→53, right outer edge x 144→147) to cover body-arm pixels.
- Avatar SVG — plate armor arm guards widened by 2 px on each side (left x 55→53, right width 18→20) to cover body-arm skin pixels.
- Avatar SVG — all weapon sprites shifted left via translate so grips align with the right hand (sword −6, longsword −10, dagger −14, staff −20, bow −18, axe −20, wand −10).
- Avatar SVG — all offhand sprites shifted right via translate so straps/grips align with the left arm (wooden shield +20, kite shield +12, spellbook +18, torch +18, buckler +22).
- Avatar SVG — ranger hood redesigned as a transparent-face cowl so the character's face is no longer covered.
- Avatar SVG — robe sleeves now angle outward at ~50° so arms appear extended rather than hanging straight down.
- Avatar SVG — dress arms replaced with a single continuous puff-to-wrist path, eliminating the segmented "crossed arms" illusion.
- Avatar SVG — plate armor arm guards extended upward to overlap the pauldron base, closing the skin gap.
- Avatar SVG — sword blade shortened and grip centred on the right hand.
- Avatar SVG — dagger blade now starts at the crossguard instead of below it.
- Avatar SVG — bow arrow redirected to point right (away from body) instead of into the character's torso.
- Avatar SVG — battle axe, staff, and wand shifted right to clear the body arm.
- Avatar SVG — longsword crossguard narrowed from 80 px to 50 px.
- Avatar SVG — torch shifted left to clear the left arm.
- Avatar SVG — spellbook shifted up 20 px so the hand grips the centre of the book.
- Avatar SVG — kite shield shifted up and right so the arm strap aligns with the left arm and the shield covers the arm area.
- Avatar SVG — wand sparkles moved to x > 150 so none overlap the body.

---

## [v0.2.0]

### Added
- User deletion — admins can permanently remove an adventurer and all their quest history from the Guild Hall.

### Fixed
- Timestamps in the UI now respect the `TZ` environment variable via a `localtime` Jinja2 filter. Previously UTC was displayed raw, causing off-by-one date issues for non-UTC timezones.

---

## [v0.1.0]

### Added
- Google → local account migration — users signed in via Google OAuth can set a local password under *Adventurer Settings*, enabling email/password login without needing Google.

---

## [v0.0.27]

### Fixed
- Rejected log entry cleanup now performs a bulk SQL `DELETE` instead of per-object ORM deletes, which previously failed to remove rows from the database.

---

## [v0.0.26]

### Fixed
- Maintenance cleanup now deletes entire rejected `Completion` rows (including the database entry), not just the attached image file.

---

## [v0.0.25]

### Added
- Apprise notifications — replaced the Discord-only webhook with [Apprise](https://github.com/caronc/apprise), supporting Discord, Telegram, Slack, Ntfy, Gotify, and [100+ other services](https://github.com/caronc/apprise/wiki) via `APPRISE_URLS`. `DISCORD_WEBHOOK_URL` continues to work alongside it.
- Notification icon / avatar URL — admins can set a custom icon URL in *Notification Settings* used as the bot avatar in Discord and other supported services.
- Approve / Reject quest via link — submission notifications include one-click approve and reject links usable directly from Discord, Telegram, email, etc. without logging in. Links are single-use.
- Maintenance section — new section in the Guild Hall admin panel with a button to permanently delete all rejected quest log entries and their attached image files.

---

## [v0.0.24]

### Added
- Discord webhook notifications for quest submissions, approvals, reward requests, and redemptions.
- Test webhook button in the Guild Hall admin panel.

### Changed
- Improved webhook error logging.

---

## [v0.0.23]

### Changed
- Admin setup (first login with default `admin` account) and post-password-reset flows now use separate routes and pages.

---

## [v0.0.22]

### Added
- Admins can reset any user's password from the Guild Hall. The user is forced to set a new one on next login.

---

## [v0.0.21]

### Added
- Multi-user quest assignment — a single quest can be assigned to multiple adventurers via a many-to-many relationship.
- Manual gem adjustment — admins can add or deduct gems from any user directly from the Guild Hall.

### Fixed
- Debug mode was enabled in production; now controlled by the `FLASK_DEBUG` environment variable.

---

## [v0.0.20]

### Added
- Quest editing — admins can edit existing quests (name, description, assigned adventurers, schedule, penalty, gem reward) from the Guild Hall.
- Streak bonuses — quests can award a gem multiplier every N consecutive approved completions, configurable per quest at creation time.

---

## [v0.0.19]

### Security
- Upgraded pip to v26.0 to address CVE-2026-1703.

---

## [v0.0.18]

### Added
- Trivy vulnerability scanning added to the CI pipeline.
- Active quests list on admin dashboard now shows all users (excluding the demo account).

---

## [v0.0.12] – [v0.0.17]

### Changed
- Renovate automated dependency updates (Docker actions, Python base image).

---

## [v0.0.11]

### Added
- Medieval-themed UI overhaul: multiple themes (Dungeon, Royal Court, Ranger's Lodge, Dragon's Lair, Sorcerer's Tower, Dwarven Forge) with live preview in settings.
- RPG-themed README rewrite.

---

## [v0.0.12]

### Added
- Quest description field added to quest creation form and displayed on the dashboard.

---

## [v0.0.10]

### Added
- CLAUDE.md with comprehensive codebase documentation.

### Fixed
- Demo user's quests now correctly filtered from the admin panel.
- Bind-mounted volume read-only database error resolved.
- Naive vs. aware datetime comparison crash in `check_missed_habits`.

---

## [v0.0.5] – [v0.0.9]

### Changed
- CI/CD: PR build workflow refined (comment triggers → label triggers → permission fixes → caching improvements).

---

## [v0.0.1] – [v0.0.4]

### Added
- Initial release: core habit tracking with RPG theming (quests, gems, adventurers, Guild Masters), photo proof upload, admin approval/rejection workflow, gem-based reward shop, daily/weekly/bi-weekly/interval quest schedules, penalty system, Google OAuth and local email/password authentication, demo user with pre-seeded content, Docker + Docker Compose deployment with Gunicorn, GitHub Actions CI/CD pipeline.
- Renovate configured for automated dependency updates (FontAwesome, Python).
