# Changelog

All notable changes to Quest Log are documented here.

---

## [Unreleased]

### Added

- **Apprise notifications** — replaced the Discord-only webhook with [Apprise](https://github.com/caronc/apprise), supporting Discord, Telegram, Slack, Ntfy, Gotify, and [100+ other services](https://github.com/caronc/apprise/wiki) via the `APPRISE_URLS` environment variable. `DISCORD_WEBHOOK_URL` continues to work alongside it.
- **Notification icon / avatar URL** — admins can now set a custom icon URL in the Guild Hall that is used as the avatar image in Discord (and other supported services). Configurable under *Notification Settings* in the admin panel.
- **Approve / Reject quest via link** — quest submission notifications now include one-click approve and reject links. Clicking the link performs the action immediately without logging into the app — useful for approving directly from Discord, Telegram, or email. Links are single-use and invalidated after use.
- **Clean up rejected images** — new *Maintenance* section in the admin panel with a button to permanently delete image files attached to rejected quest submissions, freeing disk space.
- **Quest editing** — admins can now edit existing quests (name, description, assigned adventurers, schedule, penalty, and gem reward) from the Guild Hall.
- **Streak bonuses** — quests can optionally award a gem multiplier every N consecutive completions (configurable per quest).
- **Multi-user quest assignment** — a single quest can now be assigned to multiple adventurers at once.

### Changed

- Test webhook button in the admin panel now reflects all configured notification services (not just Discord).
- Notification helper renamed internally from `send_discord_webhook` to `send_notification`.

---

## Earlier

Refer to git history for changes prior to the Apprise migration.
