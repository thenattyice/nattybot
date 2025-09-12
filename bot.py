import os
import discord
import asyncpg
import asyncio
import re
import traceback
from discord.ext import commands
from discord import Member
from dotenv import load_dotenv
from f1_schedule_data import schedule_2025
from cogs.economy import Economy
from cogs.lfg import LookingForGroup
from cogs.mcserver import setup as setup_mcserver
from cogs.shop.shop import setup as setup_shop
from cogs.shop.businesses import setup as setup_businesses
from cogs.wordle import Wordle
from cogs.games.coinflip import setup as setup_coinflip
from cogs.games.rps import setup as setup_rps
from cogs.games.blackjack import setup as setup_blackjack
from cogs.games.freespin import setup as setup_freespin
from cogs.magicthegathering.buildpack import setup as setup_openpack

load_dotenv() #Load the env file

# Vars instead of hard coding guids
GUILD_ID = int(os.getenv("GUILD_ID"))
GUILD_OBJECT = discord.Object(id=GUILD_ID)
ROLES_ALLOWED_ADD_MONEY = {int(os.getenv("MR_ICE_ROLE"))}  # Mr. Ice for now
WORDLE_APP_ID = 1211781489931452447
PURCHASE_LOG_CHANNEL = int(os.getenv("PURCHASE_LOG_CHANNEL"))
DAILYPAYOUT_LOG_CHANNEL = int(os.getenv("DAILYPAYOUT_LOG_CHANNEL"))
PACK_OPENING_CHANNEL = int(os.getenv("PACK_OPENING_CHANNEL"))

GAME_ROLES = {
    "rocket league": int(os.getenv("RL_ROLE")),
    "rematch": int(os.getenv("REMATCH_ROLE")),
    "mtg": int(os.getenv("MTG_ROLE"))
}

# User mappings for adding and removing users
USERS = {
    "grayson": 162343822179696640,
    "jake": 277997412583473152,
    "nate": 280683796020330497,
    "gunnar": 768246922766450689
}

class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_pool = None #Stores the pool
        
    # DB conenction details method
    async def setup_db(self):
        try:
            self.db_pool = await asyncpg.create_pool(dsn=os.getenv("DATABASE_URL"))
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        balance BIGINT NOT NULL DEFAULT 0,
                        wordle_pts BIGINT NOT NULL DEFAULT 0,
                        daily_spin BOOLEAN DEFAULT FALSE
                    );
                    CREATE TABLE IF NOT EXISTS shop (
                        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        price INTEGER NOT NULL,
                        is_business BOOLEAN DEFAULT FALSE,
                        daily_payout INTEGER
                    );
                    CREATE TABLE IF NOT EXISTS inventory (
                        user_id BIGINT REFERENCES users(user_id),
                        item_id INTEGER REFERENCES shop(id),
                        quantity INTEGER NOT NULL DEFAULT 1,
                        is_business BOOLEAN REFERENCES shop(is_business),
                        PRIMARY KEY (user_id, item_id)
                    );
                    CREATE TABLE IF NOT EXISTS purchases (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES users(user_id),
                        item_id INTEGER REFERENCES shop(id),
                        quantity INTEGER NOT NULL DEFAULT 1,
                        purchase_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE TABLE IF NOT EXISTS mtg_sets (
                        id SERIAL PRIMARY KEY,
                        set_code TEXT UNIQUE NOT NULL,
                        set_name TEXT UNIQUE NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS mc_server (
                        id SERIAL PRIMARY KEY,
                        ip_address TEXT,
                        setup_status BOOLEAN DEFAULT FALSE,
                        category_id BIGINT,
                        status_channel_id BIGINT,
                        playercount_channel_id BIGINT
                    );
                """)
            print("Database connection pool created and schema ensured.")

        except asyncpg.PostgresError as e:
            print(f"❌ Failed to connect to the database: {e}")
            
    # Bot startup method
    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        print("Successfully finished startup")

        try:
            synced = await self.tree.sync(guild=GUILD_OBJECT)
            print(f'Synced {len(synced)} commands to guild {GUILD_ID}')

        except Exception as e:
            print(f'Error syncing commands: {e}')

    # Event handler for voice state updates
    async def on_voice_state_update(self, member, before, after):
        print(f"Voice state update detected for {member.name}")

        if before.channel is None and after.channel is not None and member.id == USERS["nate"]:
            print(f'Nate joined the VC')
            try:
                # Send you a DM
                user = await self.fetch_user(USERS["grayson"])
                await user.send("Grayson is bad at RL")
                print(f"DM sent to {user.name}")
            except Exception as e:
                print(f"Error sending DM: {e}")
    
# Declared intents for bot perms in server
intents = discord.Intents.all()
intents.message_content = True
intents.reactions = True
intents.voice_states = True
intents.members = True
client = Client(command_prefix="!", intents=intents)

# F1 schedule command. Pulls from f1_schedule_data.py
@client.tree.command(name="f1", description="Show 2025 F1 schedule", guild=GUILD_OBJECT)
async def f1_schedule(interaction: discord.Interaction):
    embed = discord.Embed(title="2025 Formula 1 Race Schedule", color=0xFF0000)
    for race in schedule_2025.values():
        embed.add_field(name=race['name'], value=f"Date: {race['date']}\nTime: {race['time']} EST", inline=False)
    await interaction.response.send_message(embed=embed)

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
    # Economy Cog
    economy_cog = Economy(client, GUILD_OBJECT,ROLES_ALLOWED_ADD_MONEY)
    await load_cog("Economy", client.add_cog(economy_cog))
    client.add_money_to_user = economy_cog.add_money_to_user #Pulls this in from the economy cog
    
    # LFG Cog
    lfg_cog = LookingForGroup(client, GUILD_OBJECT,GAME_ROLES)
    await load_cog("LookingForGroup", client.add_cog(lfg_cog))
    
    # Shop Cogs
    await load_cog("Shop", setup_shop(client, GUILD_OBJECT, ROLES_ALLOWED_ADD_MONEY, PURCHASE_LOG_CHANNEL))
    await load_cog("Businesses", setup_businesses(client, DAILYPAYOUT_LOG_CHANNEL, GUILD_OBJECT))
    
    # Wordle Cog
    wordle_cog = Wordle(client, GUILD_OBJECT, WORDLE_APP_ID)
    await load_cog("Wordle", client.add_cog(wordle_cog))
    
    #Game Cogs
    await load_cog("Coinflip", setup_coinflip(client, GUILD_OBJECT))
    await load_cog("RockPaperScissors", setup_rps(client, GUILD_OBJECT, ROLES_ALLOWED_ADD_MONEY))
    await load_cog("Blackjack", setup_blackjack(client, GUILD_OBJECT))
    await load_cog("FreeDailySpin", setup_freespin(client, GUILD_OBJECT))
    
    # MTG
    await load_cog("BuildBoosterPack", setup_openpack(client, GUILD_OBJECT,ROLES_ALLOWED_ADD_MONEY, PACK_OPENING_CHANNEL))
    
    # MC Server Status
    await load_cog("MinecraftServerStatus", setup_mcserver(client, GUILD_OBJECT, ROLES_ALLOWED_ADD_MONEY))
    
# Main method
async def main():
    await client.setup_db() #Connect to the DB first
    await setup_cogs()
    await client.start(os.getenv('DISCORD_TOKEN'))

# Run main
if __name__ == '__main__':
    asyncio.run(main())