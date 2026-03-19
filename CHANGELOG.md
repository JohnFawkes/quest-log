# Changelog

All notable changes to Quest Log are documented here.

---

## [Unreleased]

### Added

- **Apprise notifications** — replaced the Discord-only webhook with [Apprise](https://github.com/caronc/apprise), supporting Discord, Telegram, Slack, Ntfy, Gotify, and [100+ other services](https://github.com/caronc/apprise/wiki) via the `APPRISE_URLS` environment variable. `DISCORD_WEBHOOK_URL` continues to work alongside it.
- **Notification icon / avatar URL** — admins can set a custom icon URL in the Guild Hall (*Notification Settings*) used as the avatar/bot icon in Discord and other supported services.
- **Approve / Reject quest via link** — quest submission notifications include one-click approve and reject links. Works directly from Discord, Telegram, email, etc. without logging into the app. Links are single-use and invalidated after use.
- **Maintenance: clean up rejected entries** — new *Maintenance* section in the admin panel with a button to permanently delete all rejected quest log entries and their attached image files, freeing disk space.
- **Delete user** — admins can now remove adventurers from the Guild Hall. All their quest history and habit assignments are removed alongside the account.
- **Google → local account migration** — users signed in via Google OAuth can set a local password in *Adventurer Settings*, allowing login with email and password without Google. The section only appears for accounts that don't yet have a password.
- **Quest editing** — admins can edit existing quests (name, description, assigned adventurers, schedule, penalty, gem reward) from the Guild Hall.
- **Streak bonuses** — quests can optionally award a gem multiplier every N consecutive completions (configurable per quest at creation time).
- **Multi-user quest assignment** — a single quest can be assigned to multiple adventurers at once.

### Changed

- Maintenance cleanup now deletes entire rejected `Completion` rows, not just their image filenames.
- Test webhook button in the admin panel now reflects all configured notification services (not just Discord).
- Notification helper renamed internally from `send_discord_webhook` to `send_notification`.

---

## Earlier

Refer to git history for changes prior to the Apprise migration.
