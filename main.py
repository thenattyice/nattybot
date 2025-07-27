import os
import discord
import asyncpg
import asyncio
from discord.ext import commands
from discord import app_commands
from discord import Member
from dotenv import load_dotenv
from f1_schedule_data import schedule_2025

load_dotenv() #Load the env file

# Vars instead of hard coding guids
GUILD_ID = 412828225144750092
GUILD_OBJECT = discord.Object(id=GUILD_ID)
ROLES_ALLOWED_ADD_MONEY = {412966700544163840}  # Mr. Ice for now

# User mappings for adding and removing users
USERS = {
    "grayson": 162343822179696640,
    "jake": 277997412583473152,
    "nate": 280683796020330497
}

class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_pool = None #Stores the pool
        
    #DB conenction details method
    async def setup_db(self):
        try:
            self.db_pool = await asyncpg.create_pool(dsn=os.getenv("DATABASE_URL"))
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        balance BIGINT NOT NULL DEFAULT 0
                    );
                """)
            print("Database connection pool created and schema ensured.")

        except asyncpg.PostgresError as e:
            print(f"❌ Failed to connect to the database: {e}")

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        print("Successfully finished startup")

        try:
            await self.tree.sync()
            print(f'Synced commands globally')

            synced = await self.tree.sync(guild=GUILD_OBJECT)
            print(f'Synced {len(synced)} commands to guild {GUILD_ID}')

        except Exception as e:
            print(f'Error syncing commands: {e}')

    #Event handler for voice state updates
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

intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True
client = Client(command_prefix="!", intents=intents)

@client.tree.command(name="test", description="Nate's test command", guild=GUILD_OBJECT)
async def say_test(interaction: discord.Interaction):
    await interaction.response.send_message("The test worked!")

@client.tree.command(name="balance", description="Check your balance", guild=GUILD_OBJECT)
async def balance_check(interaction: discord.Interaction):
    user_id = interaction.user.id

    async with client.db_pool.acquire() as conn:
        result = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", user_id)

    balance = result["balance"] if result else 0
    await interaction.response.send_message(f"Your balance is {balance} NattyCoins.", ephemeral=True)

@client.tree.command(name="addmoney", description="Add currency to your balance", guild=GUILD_OBJECT)
async def add_money(interaction: discord.Interaction, user: Member, amount: int):
    user_role_ids = [role.id for role in interaction.user.roles]
    if not any(role_id in ROLES_ALLOWED_ADD_MONEY for role_id in user_role_ids):
        await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message("The balance addition cannot be negative.", ephemeral=True)
        return

    target_user_id = user.id

    async with client.db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, balance)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
            SET balance = users.balance + $2;
        """, target_user_id, amount)

    await interaction.response.send_message(f"Added {amount} coins to {user.mention}'s balance.", ephemeral=True)

@client.tree.command(name="rl", description="Ping the homies for rocket league", guild=GUILD_OBJECT)
async def rl_ping(interaction: discord.Interaction):
    mentions = []
    for name, user_id in USERS.items():
        member = interaction.guild.get_member(user_id)
        if member:
            mentions.append(member.mention)

    await interaction.response.send_message(f"Let's go boys, it's trio time {' '.join(mentions)}")

@client.tree.command(name="f1", description="Show 2025 F1 schedule", guild=GUILD_OBJECT)
async def f1_schedule(interaction: discord.Interaction):
    embed = discord.Embed(title="2025 Formula 1 Race Schedule", color=0xFF0000)
    for race in schedule_2025.values():
        embed.add_field(name=race['name'], value=f"Date: {race['date']}\nTime: {race['time']} EST", inline=False)
    await interaction.response.send_message(embed=embed)

async def main():
    await client.setup_db()
    await client.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    asyncio.run(main())

