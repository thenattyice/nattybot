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
GUILD_ID = int(os.getenv("GUILD_ID"))
GUILD_OBJECT = discord.Object(id=GUILD_ID)
ROLES_ALLOWED_ADD_MONEY = {int(os.getenv("MR_ICE_ROLE"))}  # Mr. Ice for now
WORDLE_APP_ID = 1211781489931452447

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
        
    # DB conenction details method
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
            
    # Bot startup method
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
    
    # Function for adding money to users in DB
    async def add_money_to_user(self, user_id: int, amount: int):
        async with client.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, balance)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET balance = users.balance + $2;
            """, user_id, amount)
                
    # Event listener for the Wordle channel, specifically tracking daily results
    async def on_message(self, message):
        if message.channel.name != 'wordle': # Filter for the 'wordle' channel
            return
        
        if message.author.id != WORDLE_APP_ID: # Filter for only messages by the Wordle app
            return
        
        if "Here are yesterday's results:" not in message.content: # Finds the summary message via the sumamry phrase
            return
        
        lines = message.content.splitlines() # Split out the worlde daily summary line by line
        user_rewards = {}
        
        # Loop through each line
        for line in lines:
            match = re.match(r"(👑 )?(\d)/6: (.+)", line) # Regex for the line format. Crown optional as group 1, group 2 is the score, and group 3 is the name
            if match:
                score = int(match.group(2))
                raw_name = match.group(3).strip()
                
                matched_user = None # Init the matched user
                
                # First look for actual user mentions
                for user in message.mentions:
                    if user.display_name in raw_name or user.name in raw_name:
                        matched_user = user
                        break
                    
                # Sometimes it fails to mention, so we grab the raw_name and search using that
                if not matched_user:
                    for member in message.guild.members:
                        if member.display_name in raw_name or member.name in raw_name:
                            matched_user = member
                            break
                        
                if matched_user:
                    user_rewards[matched_user.id] = score
                else:
                    print(f"⚠️ Could not match user for: {raw_name}")
                    
        for user_id, score in user_rewards.items():
            reward = calculate_wordle_reward(score)
            await client.add_money_to_user(user_id, reward)

            # Fetch the member object from the ID
            member = message.guild.get_member(user_id)
            if member:
                await message.channel.send(f"{member.mention} was awarded {reward} NattyCoins for their Wordle score!")
            else:
                print(f"⚠️ Could not find member with ID {user_id} to announce reward.")
            
        await self.process_commands(message)
    
    # Function to calc the score                
    def calculate_wordle_reward(score):
        return max(0, 7 - score) * 10
    
# Declared intents for bot perms in server
intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True
client = Client(command_prefix="!", intents=intents)

# Test command
@client.tree.command(name="test", description="Nate's test command", guild=GUILD_OBJECT)
async def say_test(interaction: discord.Interaction):
    await interaction.response.send_message("The test worked!")
    
# Balance check command
@client.tree.command(name="balance", description="Check your balance", guild=GUILD_OBJECT)
async def balance_check(interaction: discord.Interaction):
    user_id = interaction.user.id

    async with client.db_pool.acquire() as conn:
        result = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", user_id)

    balance = result["balance"] if result else 0
    await interaction.response.send_message(f"Your balance is {balance} NattyCoins.", ephemeral=True)
    
# Add money command
@client.tree.command(name="addmoney", description="Add currency to a user's balance", guild=GUILD_OBJECT)
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

# Remove money command
@client.tree.command(name="removemoney", description="Remove currency from a user's balance", guild=GUILD_OBJECT)
async def remove_money(interaction: discord.Interaction, user: Member, amount: int):
    user_role_ids = [role.id for role in interaction.user.roles]
    if not any(role_id in ROLES_ALLOWED_ADD_MONEY for role_id in user_role_ids):
        await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message("The balance edit cannot be negative.", ephemeral=True)
        return

    target_user_id = user.id
    
    async with client.db_pool.acquire() as conn:
        result = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", target_user_id)
        current_balance = result["balance"] if result else 0
        
        if current_balance < amount:
            await interaction.response.send_message(f"The balance removal cannot be larger than the user's current balance. {user.mention}'s current balance: {current_balance} NattyCoins.", ephemeral=True)
            return

    async with client.db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (user_id, balance)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
            SET balance = users.balance - $2;
        """, target_user_id, amount)

    await interaction.response.send_message(f"Removed {amount} coins from {user.mention}'s balance.", ephemeral=True)

# RL LFG ping command
@client.tree.command(name="rl", description="Ping the homies for rocket league", guild=GUILD_OBJECT)
async def rl_ping(interaction: discord.Interaction):
    mentions = []
    for name, user_id in USERS.items():
        member = interaction.guild.get_member(user_id)
        if member:
            mentions.append(member.mention)

    await interaction.response.send_message(f"Lets go boys, its trio time {' '.join(mentions)}")

# F1 schedule command. Pulls from f1_schedule_data.py
@client.tree.command(name="f1", description="Show 2025 F1 schedule", guild=GUILD_OBJECT)
async def f1_schedule(interaction: discord.Interaction):
    embed = discord.Embed(title="2025 Formula 1 Race Schedule", color=0xFF0000)
    for race in schedule_2025.values():
        embed.add_field(name=race['name'], value=f"Date: {race['date']}\nTime: {race['time']} EST", inline=False)
    await interaction.response.send_message(embed=embed)

# Main method
async def main():
    await client.setup_db() #Connect to the DB first
    await client.start(os.getenv('DISCORD_TOKEN'))

# Run main
if __name__ == '__main__':
    asyncio.run(main())

