import asyncpg

# DB Schema
SCHEMA = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    balance BIGINT NOT NULL DEFAULT 0,
    wordle_pts BIGINT NOT NULL DEFAULT 0,
    daily_spin BOOLEAN DEFAULT FALSE,
    wordle_streak INT NOT NULL DEFAULT 0,
    last_wordle_date DATE,
    best_wordle_streak INT
);

-- Shop items table (item_type stored as text)
CREATE TABLE IF NOT EXISTS shop_items (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    price INTEGER NOT NULL CHECK (price > 0),
    item_type TEXT NOT NULL CHECK (item_type IN ('consumable', 'bundle', 'business', 'collectible')),
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User inventory table
CREATE TABLE IF NOT EXISTS inventory (
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES shop_items(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 0),
    metadata JSONB DEFAULT '{}',
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, item_id)
);

-- MTG sets table (for pack opening feature)
CREATE TABLE IF NOT EXISTS mtg_sets (
    id SERIAL PRIMARY KEY,
    set_code TEXT UNIQUE NOT NULL,
    set_name TEXT UNIQUE NOT NULL,
    pack_price INTEGER NOT NULL,
    box_price INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Purchase history/log table
CREATE TABLE IF NOT EXISTS purchases (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES shop_items(id) ON DELETE SET NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price_paid INTEGER NOT NULL,
    purchase_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Item usage log (for consumables, pack openings, etc.)
CREATE TABLE IF NOT EXISTS item_usage (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES shop_items(id) ON DELETE SET NULL,
    usage_type TEXT NOT NULL, -- 'consume', 'activate', 'daily_payout'
    quantity INTEGER DEFAULT 1,
    result_data JSONB, -- Store pack contents, payout amounts, etc.
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Game stats table (for leaderboards)
CREATE TABLE IF NOT EXISTS game_stats (
    id SERIAL PRIMARY KEY,  -- Add an auto-incrementing ID
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    game TEXT NOT NULL,
    result TEXT NOT NULL,
    wager INTEGER DEFAULT 0,
    balance_change INTEGER DEFAULT 0,
    game_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Game stats table (for leaderboards)
CREATE TABLE IF NOT EXISTS gambling_stats (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    total_wagered INTEGER DEFAULT 0,
    total_won INTEGER DEFAULT 0,
    games_played INTEGER DEFAULT 0,
    biggest_win INTEGER DEFAULT 0,
    last_game_timestamp TIMESTAMP
);

-- Minecraft server tracking
CREATE TABLE IF NOT EXISTS mc_server (
    id SERIAL PRIMARY KEY,
    ip_address TEXT UNIQUE NOT NULL,
    setup_status BOOLEAN DEFAULT FALSE,
    category_id BIGINT,
    status_channel_id BIGINT,
    player_count_channel_id BIGINT
);

-- Jackpot for slots
CREATE TABLE IF NOT EXISTS jackpot (
    total INTEGER DEFAULT 1000,
    last_winner_id BIGINT,
    last_winner_date DATE
);

-- F1 session data
CREATE TABLE IF NOT EXISTS f1_sessions (
    id SERIAL PRIMARY KEY,
    circuit_key INT NOT NULL,
    circuit TEXT NOT NULL,
    date_start TIMESTAMPTZ NOT NULL,
    date_end TIMESTAMPTZ NOT NULL,
    session_name TEXT NOT NULL,
    session_key INT NOT NULL,
    location TEXT NOT NULL,
    year INT NOT NULL,
    UNIQUE(circuit_key, session_name, year)
);

-- F1 season data
CREATE TABLE IF NOT EXISTS f1_seasons (
    id SERIAL PRIMARY KEY,
    round INT NOT NULL,
    circuit_key INT NOT NULL,
    circuit TEXT NOT NULL,
    meeting_name TEXT NOT NULL,
    date_start TIMESTAMPTZ NOT NULL,
    date_end TIMESTAMPTZ NOT NULL,
    year INT NOT NULL,
    UNIQUE(circuit_key, year)
);

-- Wordle results table
CREATE TABLE IF NOT EXISTS wordle_results (
    user_id BIGINT REFERENCES users(user_id),
    guesses INT NOT NULL,
    game_date DATE NOT NULL,
    PRIMARY KEY (user_id, game_date)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id);
CREATE INDEX IF NOT EXISTS idx_purchases_user_id ON purchases(user_id);
CREATE INDEX IF NOT EXISTS idx_purchases_timestamp ON purchases(purchase_time DESC);
CREATE INDEX IF NOT EXISTS idx_shop_items_type ON shop_items(item_type);
CREATE INDEX IF NOT EXISTS idx_shop_items_active ON shop_items(is_active) WHERE is_active = TRUE;
"""

# Initialize the DB and open it as a pool. Gets passed to main bot on setup and dependency to cogs 
async def create_db_pool(dsn: str) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(dsn=dsn)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA)
    return pool

# Closes the DB pool
async def close_db_pool(pool: asyncpg.Pool):
    await pool.close()
