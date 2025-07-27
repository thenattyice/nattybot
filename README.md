# Degenbot 🪙🎮

Discord bot built with `discord.py`, `asyncpg`, and `dotenv` for managing a lightweight economy system, social commands, and a live F1 schedule.

---

## 🚀 Features

- 🎤 **Voice State Listener** – Sends DMs when specific users join voice chat
- 💰 **Economy Commands** – Track and manage NattyCoins for users
- 🧪 **Test Command** – Basic sanity check for bot health
- 🏎 **F1 Command** – Displays the full 2025 Formula 1 schedule
- 🎮 **Rocket League Ping** – Notify the squad to hop on

---

## 📦 Requirements

- Python 3.8+
- PostgreSQL database
- Discord Bot Token
- `.env` file with credentials

---

## 🔧 Setup

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/nattybot.git
cd nattybot
python3 -m venv .venv
source .venv/bin/activate      # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
DISCORD_TOKEN=your-discord-bot-token
DATABASE_URL=postgres://user:pass@host:port/dbname
```

### 3. Run the Bot

```bash
python main.py
```

---

## 🗃 Commands

| Command      | Description                             |
|--------------|-----------------------------------------|
| `/balance`   | Check your NattyCoin balance            |
| `/addmoney`  | Add coins to a user (requires permission) |
| `/test`      | Responds with a success message         |
| `/rl`        | Pings Nate, Jake, and Grayson for RL    |
| `/f1`        | Shows the full 2025 F1 schedule          |

---

## 🛡 Permissions

To use `/addmoney`, your role must be in the allowed set:
```python
ROLES_ALLOWED_ADD_MONEY = {412966700544163840}
```

Update these in the source code as needed.

---

## 📁 Project Structure

```
degenbot/
│
├── bot.py
├── f1_schedule_data.py
├── requirements.txt
├── .env
├── .gitignore
├── LICENSE
└── README.md
```

---

## 🤝 Contributing

Pull requests and suggestions are welcome.

---

## 📜 License

[MIT License](https://github.com/thenattyice/degenbot/blob/main/LICENSE)
