import os
import discord
import asyncpg
import asyncio
from discord.ext import commands
from discord import app_commands
from discord import Member
from dotenv import load_dotenv

load_dotenv() #Load the env file

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
        print("successfully finished startup")
        
        try:
            await self.tree.sync()
            print(f'Synced commands globally')
            
            guild = discord.Object(id=412828225144750092)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
            
        except Exception as e:
            print(f'Error syncing commands: {e}')
            
    #Event handler for voice state updates
    async def on_voice_state_update(self, member, before, after):
        print(f"Voice state update detected for {member.name}")
        
        if before.channel is None and after.channel is not None and member.id == 280683796020330497:
            print(f'Nate joined the VC')
            try:
                # Fetch your user account (replace with your user ID)
                user = await self.fetch_user(162343822179696640)
                # Send you a DM
                await user.send("Grayson is bad at RL")
                print(f"DM sent to {user.name}")
            except Exception as e:
                print(f"Error sending DM: {e}")

intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True
client = Client(command_prefix="!", intents=intents)

GUILD_ID = discord.Object(id=412828225144750092)
#Test command
@client.tree.command(name="test", description="Nate's test command", guild=GUILD_ID)
async def say_test(interaction: discord.Interaction):
    await interaction.response.send_message("The test worked!")
    
""" Base commands for the economy function """

#Check balance
@client.tree.command(name="balance", description="Check your balance", guild=GUILD_ID)
async def balance_check(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    async with client.db_pool.acquire() as conn:
            result = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", user_id)
            
    balance = result["balance"] if result else 0
    await interaction.response.send_message(f"Your balance is {balance} NattyCoins.", ephemeral=True)
    
#Add money
ROLES_ALLOWED_ADD_MONEY = {412966700544163840} #Mr. Ice for now
@client.tree.command(name="addmoney", description="Add currency to your balance", guild=GUILD_ID)
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

#Command to ping the boys for RL
@client.tree.command(name="rl", description="Ping the homies for rocket league", guild=GUILD_ID)
async def rl_ping(interaction: discord.Interaction):
    grayson = interaction.guild.get_member(162343822179696640)
    jake = interaction.guild.get_member(277997412583473152)
    nate = interaction.guild.get_member(280683796020330497)
    await interaction.response.send_message(f'Lets go boys, its trio time {grayson.mention} {jake.mention} {nate.mention}')
    
#Command to display the F1 schedule
from f1_schedule_data import schedule_2025
@client.tree.command(name="f1", description="Show 2025 F1 schedule", guild=GUILD_ID)
async def f1_schedule(interaction: discord.Interaction):
    embed = discord.Embed(title="2025 Formula 1 Race Schedule", color=0xFF0000)
    for race in schedule_2025.values():
        embed.add_field(name=race['name'], value=f"Date: {race['date']}\nTime: {race['time']} EST", inline=False)
    await interaction.response.send_message(embed=embed)
    
async def main():
    await client.setup_db() #Connect to the DB first
    await client.start(os.getenv('DISCORD_TOKEN'))

if __name__ == '__main__':
    asyncio.run(main())