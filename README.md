<p align="center">
  <img src="https://img.shields.io/badge/%F0%9F%8F%B0-Quest%20Log-7c3aed?style=for-the-badge" alt="Quest Log">
</p>

# Quest Log

> *"Every great adventurer keeps a record of their deeds."*

Quest Log is a gamified habit tracker that transforms your daily tasks into an RPG adventure. Adventurers complete quests, upload proof of their exploits, earn Gems, and spend them on real-world rewards — all under the watchful eye of the Guild Master.

---

## The Adventurer's Handbook

### Core Mechanics

| Feature | Description |
|---|---|
| **Guild Roles** | Guild Masters (admins) assign quests; Adventurers (users) complete them |
| **Proof of Valor** | Upload a photo to prove a quest is done — no honor system here |
| **Gem Economy** | Earn Gems for completed quests, spend them in the Reward Shop |
| **Quest Schedules** | Daily, Weekly (e.g. Mon/Wed/Fri), Bi-Weekly, or Interval (every X days) |
| **Streak Bonuses** | Award a gem multiplier every N consecutive completions per quest |
| **Penalties** | Miss a critical quest? The Guild Master can set Gem deductions |
| **Apprise Notifications** | Alerts via Discord, Telegram, Slack, Ntfy, Gotify, and [100+ more](https://github.com/caronc/apprise/wiki) through Apprise |
| **One-Click Approvals** | Approve or reject quest submissions directly from Discord/Telegram via a link — no login needed |
| **Notification Avatar** | Configure a custom icon URL shown as the bot avatar in Discord and other services |
| **Google → Local Migration** | Convert a Google OAuth account to local email/password login from Settings |
| **User Management** | Create, promote, reset passwords, adjust gems, and delete adventurers from the Guild Hall |
| **Flexible Auth** | Local email/password or Google OAuth |
| **Themes** | Multiple medieval-inspired themes — Dungeon, Royal Court, Ranger's Lodge, and more |

---

## Forged With

- **Backend:** Python, Flask, SQLAlchemy (SQLite)
- **Frontend:** Jinja2, Tailwind CSS, FontAwesome
- **Deployment:** Docker, Docker Compose
- **CI/CD:** GitHub Actions (auto build, test, version, publish)

---

## Embark on Your Quest

### Option 1: Docker (Recommended)

```bash
# Clone the guild's archives
git clone https://github.com/johnfawkes/quest-log.git
cd quest-log

# Prepare your scrolls of configuration
cp .env.example .env
nano .env  # Set your SECRET_KEY, OAuth keys, webhook URLs, etc.

# Raise the fortress
docker compose up -d
```

The guild hall opens at **http://localhost:5000**.

### Option 2: Local Setup

```bash
pip install -r requirements.txt

# Configure your environment
cp .env.example .env
nano .env

# Open the gates
python app.py
```

---

## Guild Master's Guide

### First Login

The realm creates a default Guild Master on first startup:
- **User:** `admin`
- **Password:** `admin`

You will be required to change your credentials immediately. Alternatively, set `ADMIN_EMAIL` in `.env` and log in with that Google account to claim the throne.

### Assigning Quests

1. Enter the **Guild Hall** (Admin Panel)
2. Create a new Quest — choose the adventurer, set the schedule, and decide the Gem reward
3. Optionally enable **penalties** for missed quests

### Reviewing Submissions

When an adventurer submits proof, it appears in the **Quest Review Board**. Approve to award Gems, or reject to send them back.

If notifications are configured, each submission also delivers a message containing **one-click Approve / Reject links** — click directly from Discord, Telegram, or any notification channel to act without opening the app.

### Notifications

Set `APPRISE_URLS` to a comma-separated list of [Apprise-compatible URLs](https://github.com/caronc/apprise/wiki) to receive alerts on any supported platform. `DISCORD_WEBHOOK_URL` is also supported for convenience.

Optionally set a **Notification Avatar URL** in the Guild Hall (*Notification Settings*) to display a custom icon alongside bot messages in Discord and other services.

### User Management

The **Recruit & Promote** section of the Guild Hall lets you create users, promote them to Guild Master, adjust gems, reset passwords, and **delete adventurers** (removing all their quest history).

### Google → Local Account Migration

Adventurers who signed up via Google can set a local password under *Adventurer Settings → Set a Local Password*. Once set, they can log in with email and password without needing Google.

### Maintenance

The **Maintenance** section of the Guild Hall lets you permanently delete all rejected quest log entries and their attached image files to reclaim disk space.

---

## Scrolls of Configuration

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Flask session secret (`openssl rand -hex 32`) |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth client secret |
| `ADMIN_EMAIL` | No | Email that auto-receives Guild Master rights |
| `PUBLIC_DOMAIN` | No | Public URL for OAuth redirects |
| `APPRISE_URLS` | No | Comma-separated [Apprise URLs](https://github.com/caronc/apprise/wiki) (Discord, Telegram, Slack, etc.) |
| `DISCORD_WEBHOOK_URL` | No | Discord webhook URL (automatically converted to Apprise format) |
| `DATA_DIR` | No | Directory for the SQLite database |
| `PORT` | No | Application port (default: `5000`) |
| `TZ` | No | Timezone in IANA format (default: `UTC`) |

---

## Join the Guild

Pull requests are welcome from all adventurers!

1. **Branch** — forge your feature branch
2. **Test** — ensure the Docker build succeeds (CI included)
3. **Style** — keep the RPG theme alive

---

## License

MIT License
