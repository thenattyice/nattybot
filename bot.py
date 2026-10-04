import os
import discord
import asyncpg
import asyncio
import re
import traceback
from discord.ext import commands
from discord import Member
from config import load_config
from db import create_db_pool, close_db_pool
from cogs.economy import setup as setup_economy
from cogs.lfg import LookingForGroup
from cogs.mcserver import setup as setup_mcserver
from cogs.stats import setup as setup_stats
from cogs.shop.shop import setup as setup_shop
from cogs.shop.businesses import setup as setup_businesses
from cogs.wordle import setup as setup_wordle
from cogs.games.games import setup as setup_games
from cogs.games.coinflip import setup as setup_coinflip
from cogs.games.rps import setup as setup_rps
from cogs.games.blackjack import setup as setup_blackjack
from cogs.games.freespin import setup as setup_freespin
from cogs.games.slots import setup as setup_slots
from cogs.games.roulette import RouletteGame
from cogs.magicthegathering.buildpack import setup as setup_openpack
from cogs.magicthegathering.cardshop import setup as setup_cardshop
from cogs.magicthegathering.edhtable import setup as setup_edhtable
from cogs.formula1 import setup as setup_f1
from cogs.nickname import setup as setup_nickname
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
from services.formula1_service import Formula1Service
from services.nickname_service import NicknameService

config = load_config()

GUILD_OBJECT = discord.Object(id=config.guild_id)

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
            print(f'Synced {len(synced)} commands to guild {config.guild_id}')

        except Exception as e:
            print(f'Error syncing commands: {e}')
        
    # DB connection details method
    async def setup_db(self):
        try:
            self.db_pool = await create_db_pool(config.database_url)    
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
    game_service = GameService(client.db_pool, economy_service)
    user_service = UserService(client.db_pool, economy_service, game_service)
    slots_service = SlotsService(client.db_pool, economy_service, game_service)
    wordle_service = WordleService(client.db_pool, user_service)
    f1_service = Formula1Service(client.db_pool)
    nickname_service = NicknameService(client.db_pool, inventory_service, item_service)
    roulette = RouletteGame() # Instantiate roulette game

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
    await load_cog("Shop", setup_shop(client, GUILD_OBJECT, config.mr_ice_role, config.purchase_log_channel, shop_service, inventory_service, item_service, mtg_service))
    await load_cog("Businesses", setup_businesses(client, config.daily_payout_log_channel, GUILD_OBJECT, business_service))
    
    # Economy Cog
    await load_cog("Economy", setup_economy(client, GUILD_OBJECT,config.mr_ice_role, economy_service))
    
    # LFG Cog
    lfg_cog = LookingForGroup(client, GUILD_OBJECT,config.game_roles)
    await load_cog("LookingForGroup", client.add_cog(lfg_cog))
    
    # Wordle Cog
    await load_cog("Wordle", setup_wordle(client, GUILD_OBJECT, config.wordle_app_id, config.wordle_channel, economy_service, wordle_service))
    
    # User Stats Cog
    await load_cog("Stats", setup_stats(client, GUILD_OBJECT, config.mr_ice_role, user_service, game_service))
    
    #Game Cogs
    await load_cog("Games", setup_games(client, GUILD_OBJECT, economy_service, game_service, roulette))
    await load_cog("Coinflip", setup_coinflip(client, GUILD_OBJECT, economy_service, game_service))
    await load_cog("RockPaperScissors", setup_rps(client, GUILD_OBJECT, config.mr_ice_role, economy_service, game_service))
    await load_cog("Blackjack", setup_blackjack(client, GUILD_OBJECT, economy_service, game_service))
    await load_cog("FreeDailySpin", setup_freespin(client, GUILD_OBJECT, economy_service))
    await load_cog("SlotMachine", setup_slots(client, GUILD_OBJECT, economy_service, game_service, slots_service))
    
    # MTG
    await load_cog("BuildBoosterPack", setup_openpack(client, GUILD_OBJECT, config.mr_ice_role, config.pack_opening_channel, economy_service, mtg_service, inventory_service))
    await load_cog("CardShop", setup_cardshop(client, GUILD_OBJECT, config.mr_ice_role, config.purchase_log_channel, shop_service, inventory_service, item_service, mtg_service))
    await load_cog("EDHTable", setup_edhtable(client, GUILD_OBJECT, config.game_roles))
    
    # MC Server Status
    await load_cog("MinecraftServerStatus", setup_mcserver(client, GUILD_OBJECT, config.mr_ice_role))
    
    # F1 Cog
    await load_cog("Formula1", setup_f1(client, GUILD_OBJECT, config.f1_notifications_channel, f1_service))
    
    # NicknameChange cog
    await load_cog("NicknameChange", setup_nickname(client, GUILD_OBJECT, inventory_service, nickname_service))
    
# Main method
async def main():
    await client.start(config.discord_token)

# Run main
if __name__ == '__main__':
    asyncio.run(main())