📜 QuestLog

QuestLog is a gamified habit tracker that turns your daily chores and tasks into an RPG-style adventure. Users complete quests (habits), upload photo proof, earn Gems, and redeem them for real-world rewards set by the Guild Master (Admin).

✨ Features

🛡️  Role-Based Access: Admins (Guild Masters) assign quests; Users (Adventurers) complete them.

📸 Proof of Work: Users must upload a photo to complete a quest.

🔔 Notifications: Real-time notifications via Apprise (Discord, Telegram, Slack, etc.) for completions, approvals, and rewards.

💎 Economy System: Earn Gems for tasks, spend them in the Reward Shop.

📅 Advanced Scheduling: Daily, Weekly (e.g., Mon/Wed/Fri), Interval (Every X days), or Bi-Weekly schedules.

⚔️  Penalties: Option to deduct Gems if a critical quest is missed.

🔐 Flexible Auth: Login via Google OAuth or local Email/Password.

🎨 Themes: Customize your experience with multiple themes including Dark Mode, Light Mode, Royal Court, and Ranger's Lodge.

🛠️ Tech Stack

Backend: Python, Flask, SQLAlchemy (SQLite)

Frontend: HTML5, Tailwind CSS, FontAwesome

Containerization: Docker, Docker Compose

CI/CD: GitHub Actions

🚀 Quick Start

Option 1: Docker (Recommended)

1. Clone the repo:

``git clone [https://github.com/johnfawkes/quest-log.git](https://github.com/johnfawkes/quest-log.git)``
``cd questlog``


2. Configure Environment: Copy the example environment file and edit it with your keys.

``cp .env.example .env``
# Edit the file with your Google keys, Webhook URL, etc.
``nano .env`` 

3. Run:

``docker compose up --build -d``

The app will be available at http://localhost:5000.

Option 2: Local Python Setup

1. Install Dependencies:

``pip install -r requirements.txt``


2. Set Environment Variables: (Or create the .env file as shown above if using a loader, otherwise export them manually)

``export APPRISE_URLS="discord://webhook_id/webhook_token"``
``export GOOGLE_CLIENT_ID="your_id"``
``export GOOGLE_CLIENT_SECRET="your_secret"``


3. Run the App:

``python app.py``


👑 Admin Usage

1. First Login:

  - If no admin exists, use the default credentials:

    - User: admin

    - Pass: admin

  - You will be forced to update your email and password immediately.

  - Alternatively, set ADMIN_EMAIL in your .env file and login with that Google account to instantly become Admin.

2. Assigning Quests:

  - Go to the "Guild Hall" (Admin Panel).

  - Create a Habit, select the user, set the schedule (e.g., "Every other day"), and set the Gem reward.

3. Approvals:

  - When a user submits proof, it appears in the "Pending" queue.

  - Approve to award Gems; Reject to send them back to the drawing board.

🤝 Contributing

Pull requests are welcome!

  - Branch: Create a feature branch.

  - Tests: Ensure the Docker build passes (GitHub Action included).

  - Style: Keep the RPG theme alive!

📄 License

MIT License.
