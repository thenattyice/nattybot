import os
import discord
import asyncpg
import asyncio
import re
from discord.ext import commands
from discord import Member
from dotenv import load_dotenv
from f1_schedule_data import schedule_2025
from cogs.economy import Economy

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
    
    
    
    # Event listener for the Wordle channel, specifically tracking daily results
    async def on_message(self, message):
        if message.channel.name != 'wordle': # Filter for the 'wordle' channel
            return
        
        """ if message.author.id != WORDLE_APP_ID: # Filter for only messages by the Wordle app
            return """
        
        if "Here are yesterday's results:" not in message.content: # Finds the summary message via the summary phrase
            return
        
        lines = message.content.splitlines() # Split out the wordle daily summary line by line
        user_rewards = {}
        
        # Loop through each line of the Wordle summary text
        for line in lines:
            match = re.match(r"(👑 )?(\d|X)/6: (.+)", line)
            if match:
                raw_score = match.group(2)
                if raw_score == 'X': # Handles when a user doesnt get the Wordle
                    score = 0
                else:
                    score = int(raw_score)
                raw_name = match.group(3).strip()
                raw_name_lower = raw_name.lower()
                print(f"{score}") # For testing only

                matched_user = None

                # First: Try to match using real mentions
                for user in message.mentions:
                    if user.display_name.lower() in raw_name_lower or user.name.lower() in raw_name_lower:
                        matched_user = user
                        print(f"✅ Matched via mention: {user.display_name} ({user.id})")
                        break

                # Second: Fallback to manual name match if no mention matched
                if not matched_user:
                    for member in message.guild.members:
                        display = member.display_name.lower()
                        username = member.name.lower()
                        if display in raw_name_lower or username in raw_name_lower or \
                        raw_name_lower in display or raw_name_lower in username:
                            matched_user = member
                            print(f"✅ Fallback matched '{raw_name}' to member '{member.display_name}' ({member.id})")
                            break

                # Final handling
                if matched_user:
                    user_rewards[matched_user.id] = score
                else:
                    print(f"⚠️ Could not match user for: '{raw_name}'")
                
        for user_id, score in user_rewards.items():
            reward = self.calculate_wordle_reward(score)
            await client.add_money_to_user(user_id, reward)

            # Fetch the member object from the ID
            member = message.guild.get_member(user_id)
            if member:
                await message.channel.send(f"{member.mention} was awarded {reward} NattyCoins for their Wordle score!")
            else:
                print(f"⚠️ Could not find member with ID {user_id} to announce reward.")
        
        await self.process_commands(message)
    
    # Function to calc the score 
    @staticmethod               
    def calculate_wordle_reward(score):
        if score == 0:
            await message.channel.send(f"{member.mention} was awarded {reward} NattyCoins because they failed the Wordle. Loser!")
        else:
            return max(0, 7 - score) * 10
    
# Declared intents for bot perms in server
intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True
intents.members = True
client = Client(command_prefix="!", intents=intents)

# Test command
@client.tree.command(name="test", description="Nate's test command", guild=GUILD_OBJECT)
async def say_test(interaction: discord.Interaction):
    await interaction.response.send_message("The test worked!")
    
# Wordle test command
@client.tree.command(name="wtestscore", description="Send a real Wordle message into the channel", guild=GUILD_OBJECT)
async def wtest(interaction: discord.Interaction):
    await interaction.channel.send("Here are yesterday's results:\n2/6: Natty")
    await interaction.response.send_message("✅ Real Wordle message sent.")
    
# Wordle test command
@client.tree.command(name="wtestx", description="Send a real Wordle message into the channel", guild=GUILD_OBJECT)
async def wtestx(interaction: discord.Interaction):
    await interaction.channel.send("Here are yesterday's results:\nX/6: Natty")
    await interaction.response.send_message("✅ Real Wordle message sent.")
    
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

# Setup the cogs
async def setup_cogs():
    economy_cog = Economy(client, GUILD_OBJECT,ROLES_ALLOWED_ADD_MONEY)
    await client.add_cog(economy_cog)
    client.add_money_to_user = economy_cog.add_money_to_user #Pulls this in from the economy cog

# Main method
async def main():
    await client.setup_db() #Connect to the DB first
    await setup_cogs()
    await client.start(os.getenv('DISCORD_TOKEN'))

# Run main
if __name__ == '__main__':
    asyncio.run(main())