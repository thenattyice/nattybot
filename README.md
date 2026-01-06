# Degenbot 🪙🎮

Discord bot built with `discord.py`, `asyncpg`, and `dotenv` for managing a lightweight economy, social commands, an MTG card shop & pack-opening flow, and several mini-games.

---

## 🚀 Features

- 💰 **Economy & Shop** — NattyCoin balances, leaderboards, buyable shop items, and inventory management
- 🃏 **MTG Card Shop & Pack Opening** — Buy packs/boxes, open them for earnings, and update sets/prices
- 🎮 **Mini-Games** — Coinflip, Slots (jackpot), Blackjack, Rock-Paper-Scissors, Free spins with wager handling and logging
- 🏆 **Wordle Integration** — Parses daily Wordle summaries, pays out NattyCoins, tracks championship points, and assigns monthly champion role
- 📊 **Stats & Leaderboards** — User stats card, gambling leaderboard, and game logging for analytics

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

Create a `.env` file in the project root. The bot reads several values from environment variables; here are the common ones:

```env
# Required
DISCORD_TOKEN=your-discord-bot-token
DATABASE_URL=postgres://user:pass@host:port/dbname
GUILD_ID=your_guild_id

# Role IDs used to gate admin commands (e.g. `/addmoney`, `/additem`, `/addmtgset`)
MR_ICE_ROLE=your_admin_role_id

# Optional integrations & channels
WORDLE_APP_ID=wordle_bot_app_id    # optional: ID of the Wordle bot to parse daily results
PURCHASE_LOG_CHANNEL=channel_id
DAILYPAYOUT_LOG_CHANNEL=channel_id
PACK_OPENING_CHANNEL=channel_id

# Game role IDs (used by LFG commands)
RL_ROLE=rocket_league_role_id
REMATCH_ROLE=rematch_role_id
MTG_ROLE=mtg_role_id

# Other
BOT_DISABLED=false  # set to 'true' to prevent the bot from starting
```

Note: Do NOT commit your `.env` file to source control.

### 3. Run the Bot

```bash
# Activate your virtualenv then run
python bot.py

# If you want to keep the bot disabled for development, set:
# BOT_DISABLED=true
```

---

## 🗃 Common Commands

Below are the main slash commands you will see in the guild (registered per-guild for faster iteration):

- Economy

  - `/balance` — View your NattyCoin balance
  - `/leaderboard` — NattyCoin leaderboard
  - `/addmoney` — Add NattyCoins to a user (admin role required)
  - `/removemoney` — Remove NattyCoins from a user (admin role required)

- Shop & MTG

  - `/shop` — Browse and purchase shop items
  - `/inventory` — View your inventory
  - `/additem` — Add a shop item (admin role required)
  - `/cardshop` — Browse MTG sets and buy packs/boxes
  - `/addmtgset` — Add an MTG set for pack openings (admin role required)
  - `/openpack` & `/openpacks` — Open pack(s) (must run in the configured pack openings channel)
  - `/updatesetprice` — Update pack/box prices (admin role required)

- Mini-Games

  - `/coinflip`, `/slots`, `/blackjack`, `/rps`, `/freespin` — Play games against the bot (bets interact with your NattyCoin balance)
  - `/slotinfo`, `/jackpot` — Slots details and jackpot info

- Utility & Social
  - `/rl`, `/rematch`, `/mtg` — Tag the corresponding game roles to gather players
  - `/championship` — View the Wordle points leaderboard
  - `/stats` — View a user's stats card
  - `/gamba` — View gambling leaderboard

If a command requires admin privileges, it will return a permission error unless your role ID is included in the admin role(s) configured in the `.env` file.

---

## 🛡 Permissions

Admin-like commands (e.g. `/addmoney`, `/removemoney`, `/additem`, `/addmtgset`, `/updatesetprice`) are gated by role ID(s) configured in your `.env` (see `MR_ICE_ROLE`).

```env
# Replace with your real role ID(s) locally (do NOT commit .env)
MR_ICE_ROLE=your_role_id_here
```

`bot.py` reads these role IDs at startup and checks membership before allowing privileged actions.

---

## 📁 Project Structure

```
nattybot/
├── bot.py
├── f1_schedule_data.py
├── cogs/                   # All Discord command cogs (economy, games, shop, mtg, etc.)
├── services/               # Business logic and DB access
├── item_handlers/          # Item handling implementations
├── tests/                  # Unit tests (pytest)
├── requirements.txt
├── README.md
└── LICENSE
```

---

## 🤝 Contributing

Pull requests and suggestions are welcome.

---

## Development Procedure

- All changes, updates, and fixes will first be merged to the dev branch
- Once tested in dev, they will be merged to main

---

## 📜 License

[MIT License](https://github.com/thenattyice/degenbot/blob/main/LICENSE)
