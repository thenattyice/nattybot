import os
import discord
import asyncpg
import asyncio
import re
import traceback
from discord.ext import commands
from discord import Member
from dotenv import load_dotenv
from cogs.economy import setup as setup_economy
from cogs.lfg import LookingForGroup
from cogs.mcserver import setup as setup_mcserver
from cogs.stats import setup as setup_stats
from cogs.shop.shop import setup as setup_shop
from cogs.shop.businesses import setup as setup_businesses
from cogs.wordle import setup as setup_wordle
from cogs.games.coinflip import setup as setup_coinflip
from cogs.games.rps import setup as setup_rps
from cogs.games.blackjack import setup as setup_blackjack
from cogs.games.freespin import setup as setup_freespin
from cogs.games.slots import setup as setup_slots
from cogs.magicthegathering.buildpack import setup as setup_openpack
from cogs.magicthegathering.cardshop import setup as setup_cardshop
from services.item_service import ItemService
from services.inventory_service import InventoryService
from services.shop_service import ShopService
from services.economy_service import EconomyService
from services.mtg_service import MtgService
from services.handler_registry import get_default_registry
from services.business_service import BusinessService
from services.game_service import GameService
from services.user_service import UserService
from services.slots_service import SlotsService
from services.wordle_service import WordleService

load_dotenv() #Load the env file

# Vars instead of hard coding guids
GUILD_ID = int(os.getenv("GUILD_ID"))
GUILD_OBJECT = discord.Object(id=GUILD_ID)
ROLES_ALLOWED_ADD_MONEY = {int(os.getenv("MR_ICE_ROLE"))}  # Mr. Ice for now
WORDLE_APP_ID = int(os.getenv("WORDLE_APP_ID")) if os.getenv("WORDLE_APP_ID") else None
PURCHASE_LOG_CHANNEL = int(os.getenv("PURCHASE_LOG_CHANNEL"))
DAILYPAYOUT_LOG_CHANNEL = int(os.getenv("DAILYPAYOUT_LOG_CHANNEL"))
PACK_OPENING_CHANNEL = int(os.getenv("PACK_OPENING_CHANNEL"))

GAME_ROLES = {
    "rocket league": int(os.getenv("RL_ROLE")),
    "rematch": int(os.getenv("REMATCH_ROLE")),
    "mtg": int(os.getenv("MTG_ROLE"))
}

class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_pool = None #Stores the pool
    
    async def setup_hook(self):
        await self.setup_db() # Setup the DB
        await setup_cogs() # Load all cogs
        
        # Sync all commands after cogs load and bot initializes
        try:
            synced = await self.tree.sync(guild=GUILD_OBJECT)
            print(f'Synced {len(synced)} commands to guild {GUILD_ID}')

        except Exception as e:
            print(f'Error syncing commands: {e}')
        
    # DB conenction details method
    async def setup_db(self):
        try:
            self.db_pool = await asyncpg.create_pool(dsn=os.getenv("DATABASE_URL"))
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
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

                    -- Indexes for performance
                    CREATE INDEX IF NOT EXISTS idx_inventory_user_id ON inventory(user_id);
                    CREATE INDEX IF NOT EXISTS idx_purchases_user_id ON purchases(user_id);
                    CREATE INDEX IF NOT EXISTS idx_purchases_timestamp ON purchases(purchase_time DESC);
                    CREATE INDEX IF NOT EXISTS idx_shop_items_type ON shop_items(item_type);
                    CREATE INDEX IF NOT EXISTS idx_shop_items_active ON shop_items(is_active) WHERE is_active = TRUE;
                """)
            print("Database connection pool created and schema ensured.")

        except asyncpg.PostgresError as e:
            print(f"❌ Failed to connect to the database: {e}")
            
    # Bot startup method
    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        print("Successfully finished startup")
    
# Declared intents for bot perms in server
intents = discord.Intents.all()
intents.message_content = True
intents.reactions = True
intents.voice_states = True
intents.members = True
client = Client(command_prefix="!", intents=intents)

async def load_cog(name: str, coro):
    """
    Runs a cog loading coroutine with logging.
    name  = Display name for logging
    coro  = The coroutine object to await
    """
    try:
        await coro
    except Exception:
        print(f"[ERROR] Failed to load {name} cog:")
        traceback.print_exc()
    else:
        print(f"[SUCCESS] {name} cog loaded.")


# Setup the cogs
async def setup_cogs():
    # 1. Build core services
    economy_service = EconomyService(client.db_pool)
    item_service = ItemService(client.db_pool)
    inventory_service = InventoryService(client.db_pool)
    mtg_service = MtgService(client.db_pool, inventory_service, item_service)
    business_service = BusinessService(client.db_pool, economy_service)
    game_service = GameService(client.db_pool)
    user_service = UserService(client.db_pool, economy_service, game_service)
    slots_service = SlotsService(client.db_pool, economy_service, game_service)
    wordle_service = WordleService(client.db_pool)

    # 2. Get the handler registry
    handler_registry = get_default_registry()

    # 3. Build shop service with registry
    shop_service = ShopService(
        db_pool=client.db_pool,
        economy_service=economy_service,
        item_service=item_service,
        inventory_service=inventory_service,
        mtg_service=mtg_service,
        handler_registry=handler_registry
    )
    
    # 4. Load cogs that need services
    # Shop Cogs
    await load_cog("Shop", setup_shop(client, GUILD_OBJECT, ROLES_ALLOWED_ADD_MONEY, PURCHASE_LOG_CHANNEL, shop_service, inventory_service, item_service, mtg_service))
    await load_cog("Businesses", setup_businesses(client, DAILYPAYOUT_LOG_CHANNEL, GUILD_OBJECT, business_service))
    
    # Economy Cog
    await load_cog("Economy", setup_economy(client, GUILD_OBJECT,ROLES_ALLOWED_ADD_MONEY, economy_service))
    
    # LFG Cog
    lfg_cog = LookingForGroup(client, GUILD_OBJECT,GAME_ROLES)
    await load_cog("LookingForGroup", client.add_cog(lfg_cog))
    
    # Wordle Cog
    await load_cog("Wordle", setup_wordle(client, GUILD_OBJECT, WORDLE_APP_ID, economy_service, wordle_service))
    
    # User Stats Cog
    await load_cog("Stats", setup_stats(client, GUILD_OBJECT, ROLES_ALLOWED_ADD_MONEY, user_service, game_service))
    
    #Game Cogs
    await load_cog("Coinflip", setup_coinflip(client, GUILD_OBJECT, economy_service, game_service))
    await load_cog("RockPaperScissors", setup_rps(client, GUILD_OBJECT, ROLES_ALLOWED_ADD_MONEY, economy_service, game_service))
    await load_cog("Blackjack", setup_blackjack(client, GUILD_OBJECT, economy_service, game_service))
    await load_cog("FreeDailySpin", setup_freespin(client, GUILD_OBJECT, economy_service))
    await load_cog("SlotMachine", setup_slots(client, GUILD_OBJECT, economy_service, game_service, slots_service))
    
    # MTG
    await load_cog("BuildBoosterPack", setup_openpack(client, GUILD_OBJECT, ROLES_ALLOWED_ADD_MONEY, PACK_OPENING_CHANNEL, economy_service, mtg_service, inventory_service))
    await load_cog("CardShop", setup_cardshop(client, GUILD_OBJECT, ROLES_ALLOWED_ADD_MONEY, PURCHASE_LOG_CHANNEL, shop_service, inventory_service, item_service, mtg_service))
    
    # MC Server Status
    await load_cog("MinecraftServerStatus", setup_mcserver(client, GUILD_OBJECT, ROLES_ALLOWED_ADD_MONEY))
    
# Main method
async def main():
    # Check if bot should run
    if os.getenv("BOT_DISABLED") == "true":
        print("Bot is disabled via BOT_DISABLED environment variable")
        print("Remove or set to 'false' to re-enable")
        return
    
    await client.start(os.getenv('DISCORD_TOKEN'))

# Run main
if __name__ == '__main__':
    asyncio.run(main())