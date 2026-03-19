# Changelog

All notable changes to Quest Log are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

> Changes on the current branch, not yet merged to `main`.

### Added
- **Apprise notifications** — replaced the Discord-only webhook with [Apprise](https://github.com/caronc/apprise), supporting Discord, Telegram, Slack, Ntfy, Gotify, and [100+ other services](https://github.com/caronc/apprise/wiki) via `APPRISE_URLS`. `DISCORD_WEBHOOK_URL` continues to work alongside it.
- **Notification icon / avatar URL** — admins can set a custom icon URL in *Notification Settings* (Guild Hall) used as the bot avatar in Discord and other supported services.
- **Approve / Reject quest via link** — submission notifications include one-click approve and reject links usable directly from Discord, Telegram, email, etc. without logging in. Links are single-use.
- **Delete user** — admins can permanently remove an adventurer and all their quest history from the Guild Hall.
- **Google → local account migration** — users signed in via Google OAuth can set a local password under *Adventurer Settings*, enabling email/password login without Google.
- **Maintenance: clean up rejected entries** — button in the *Maintenance* section of the Guild Hall to permanently delete all rejected quest log entries and their attached image files.

### Fixed
- Timestamps in the UI now respect the server's `TZ` environment variable via a `localtime` Jinja2 filter (previously UTC was displayed raw, causing off-by-one date issues for non-UTC timezones).
- Rejected log entry cleanup now performs a bulk SQL `DELETE` rather than per-object ORM deletes, which previously left rows in the database.

### Changed
- Test notification button now reflects all configured Apprise services (not just Discord).
- Notification helper renamed from `send_discord_webhook` to `send_notification`.

---

## [0.6.0] — Quest Editing & Streak Bonuses

### Added
- **Quest editing** — admins can edit existing quests (name, description, assigned adventurers, schedule, penalty, gem reward) from the Guild Hall.
- **Streak bonuses** — quests can award a gem multiplier every N consecutive approved completions (configurable per quest at creation time).
- **Multi-user quest assignment** — a single quest can now be assigned to multiple adventurers via a many-to-many relationship.

---

## [0.5.0] — User & Password Management

### Added
- **Admin password reset** — Guild Masters can reset any user's password; the user is forced to set a new one on next login.
- **Separate password-change flow** — admin setup (first login) and post-reset password changes now use separate routes and pages.
- **Manual gem adjustment** — admins can add or deduct gems from any user directly from the Guild Hall.

### Fixed
- Debug mode was enabled in production; now controlled by `FLASK_DEBUG` environment variable.

---

## [0.4.0] — Notifications & Discord Webhook

### Added
- Discord webhook notifications for quest submissions, approvals, reward requests, and redemptions.
- Test webhook button in the Guild Hall admin panel.
- Improved webhook logging.

---

## [0.3.0] — Quest Descriptions & Schedule Improvements

### Added
- Quest description field displayed on the dashboard.
- Active quests list on the admin dashboard (excluding demo account).

---

## [0.2.0] — Security & Quality

### Changed
- Improved codebase security, quality, and consistency (input validation, session config, proxy fix).
- CI pipeline hardened; Docker image signed with Cosign.
- Trivy vulnerability scanning added to CI.
- Renovate configured for automated dependency updates.

---

## [0.1.0] — Initial Release

### Added
- Core habit tracking with RPG theming (quests, gems, adventurers, Guild Masters).
- Photo proof upload for quest completions.
- Admin approval / rejection workflow.
- Gem-based reward shop with user reward requests.
- Daily, weekly, bi-weekly, and interval quest schedules.
- Penalty system for missed quests.
- Google OAuth and local email/password authentication.
- Demo user with pre-seeded content.
- Multiple UI themes (Dungeon, Royal Court, Ranger's Lodge, Dragon's Lair, Sorcerer's Tower, Dwarven Forge).
- Docker + Docker Compose deployment with Gunicorn.
- GitHub Actions CI/CD pipeline (build, test, version, publish to GHCR).
