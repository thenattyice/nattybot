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
from cogs.games import Games
from cogs.lfg import LookingForGroup
from cogs.shop import Shop

load_dotenv() #Load the env file

# Vars instead of hard coding guids
GUILD_ID = int(os.getenv("GUILD_ID"))
GUILD_OBJECT = discord.Object(id=GUILD_ID)
ROLES_ALLOWED_ADD_MONEY = {int(os.getenv("MR_ICE_ROLE"))}  # Mr. Ice for now
WORDLE_APP_ID = 1211781489931452447
PURCHASE_LOG_CHANNEL = int(os.getenv("PURCHASE_LOG_CHANNEL"))

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
                        balance BIGINT NOT NULL DEFAULT 0
                    );
                    CREATE TABLE IF NOT EXISTS shop (
                        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        price INTEGER NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS inventory (
                        user_id BIGINT REFERENCES users(user_id),
                        item_id INTEGER REFERENCES shop(id),
                        quantity INTEGER NOT NULL DEFAULT 1,
                        PRIMARY KEY (user_id, item_id)
                    );
                    CREATE TABLE IF NOT EXISTS purchases (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES users(user_id),
                        item_id INTEGER REFERENCES shop(id),
                        quantity INTEGER NOT NULL DEFAULT 1,
                        purchase_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
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
        
        if message.author.id != WORDLE_APP_ID: # Filter for only messages by the Wordle app
            return
        
        if "Here are yesterday's results:" not in message.content: # Finds the summary message via the summary phrase
            return
        
        lines = message.content.splitlines() # Split out the wordle daily summary line by line
        user_rewards = {}
        
        description = '' # Init the field for the embed
        
        # Loop through each line of the Wordle summary text
        for line in lines:
            line = line.replace("👑", "").strip()
            match = re.match(r"(\d|X)/6: (.+)", line)

            if not match:
                continue

            raw_score = match.group(1)
            raw_mentions_or_names = match.group(2).strip()
            raw_mentions_or_names_lower = raw_mentions_or_names.lower()

            score = 0 if raw_score == 'X' else int(raw_score)
            print(f"🧪 Score: {score}, Raw value: {raw_mentions_or_names}")

            matched_user_ids = set()

            # Log all mentions in the message
            print("📋 Mentions in message:", [f"{u.display_name} ({u.id})" for u in message.mentions])
            print(f"📋 Processing line: {raw_mentions_or_names}")

            # 1. Match from actual parsed mentions - but only those in this specific line
            line_mention_ids = re.findall(r"<@!?(\d+)>", raw_mentions_or_names)
            line_mention_ids = [int(uid) for uid in line_mention_ids]
            
            for user in message.mentions:
                if user.id in line_mention_ids and user.id not in matched_user_ids:
                    user_rewards[user.id] = score
                    matched_user_ids.add(user.id)
                    print(f"✅ Matched via Discord mention: {user.display_name} ({user.id})")

            # 2. Match from raw <@user_id> strings that weren't caught by Discord parsing
            for user_id_str in line_mention_ids:
                user_id = int(user_id_str)
                if user_id not in matched_user_ids:
                    member = message.guild.get_member(user_id)
                    if member:
                        user_rewards[user_id] = score
                        matched_user_ids.add(user_id)
                        print(f"✅ Matched via raw ID: {member.display_name} ({user_id})")

            # 3. Fallback match using display name or username - process remaining text after removing mentions
            # Remove the actual mention syntax to get remaining plain text names
            remaining_text = raw_mentions_or_names
            for mention_id in line_mention_ids:
                # Remove both <@ID> and <@!ID> patterns
                remaining_text = re.sub(rf"<@!?{mention_id}>", "", remaining_text)
            
            remaining_text = remaining_text.strip()
            
            if remaining_text:  # Only run fallback if there's remaining text to process
                # Split the remaining text by @ to get individual name segments
                name_segments = [seg.strip() for seg in remaining_text.split('@') if seg.strip()]
                
                # If no @ symbols, treat the whole remaining text as one segment
                if not name_segments and remaining_text:
                    name_segments = [remaining_text]
                
                for segment in name_segments:
                    segment_lower = segment.lower()
                    best_match = None
                    best_match_score = 0
                    
                    for member in message.guild.members:
                        if member.bot or member.id in matched_user_ids:
                            continue
                            
                        display = member.display_name.lower()
                        username = member.name.lower()
                        
                        # Calculate match quality (prefer exact matches, then partial)
                        match_score = 0
                        if segment_lower == display or segment_lower == username:
                            match_score = 3  # Exact match
                        elif segment_lower in display or segment_lower in username:
                            match_score = 2  # Name contains segment
                        elif display in segment_lower or username in segment_lower:
                            match_score = 1  # Segment contains name
                        
                        if match_score > best_match_score:
                            best_match = member
                            best_match_score = match_score
                    
                    if best_match:
                        user_rewards[best_match.id] = score
                        matched_user_ids.add(best_match.id)
                        print(f"✅ Fallback matched '{segment}' to '{best_match.display_name}' ({best_match.id}) from remaining text")

            if not matched_user_ids:
                print(f"⚠️ Could not match any users for: '{raw_mentions_or_names}'")

        for user_id, score in user_rewards.items():
            reward = self.calculate_wordle_reward(score)
            await client.add_money_to_user(user_id, reward)

            member = message.guild.get_member(user_id)
            if member:
                description += f"{member.mention} is awarded **{reward}** NattyCoins🪙\n"
            else:
                print(f"⚠️ Could not find member with ID {user_id} to announce reward.")
        
        if description:    
            reward_embed = discord.Embed(
                title="🪙**Daily Wordle Rewards**🪙",
                description=description,
                color=discord.Color.gold()
            )
            
            await message.channel.send(embed=reward_embed)

        await self.process_commands(message)

    # Function to calc the score 
    @staticmethod               
    def calculate_wordle_reward(score):
        return 0 if score == 0 else max(0, 7 - score) * 10
    
# Declared intents for bot perms in server
intents = discord.Intents.all()
intents.message_content = True
intents.reactions = True
intents.voice_states = True
intents.members = True
client = Client(command_prefix="!", intents=intents)
    
""" # Wordle test command
@client.tree.command(name="wtestscore", description="Send a real Wordle message into the channel", guild=GUILD_OBJECT)
async def wtest(interaction: discord.Interaction):
    await interaction.channel.send("Here are yesterday's results:\n2/6: Natty\nX/6: @Guru Pathik")
    await interaction.response.send_message("✅ Real Wordle message sent.")
    
# Wordle test command
@client.tree.command(name="wtestx", description="Send a real Wordle message into the channel", guild=GUILD_OBJECT)
async def wtestx(interaction: discord.Interaction):
    await interaction.channel.send("Here are yesterday's results:\nX/6: Natty")
    await interaction.response.send_message("✅ Real Wordle message sent.") """

# F1 schedule command. Pulls from f1_schedule_data.py
@client.tree.command(name="f1", description="Show 2025 F1 schedule", guild=GUILD_OBJECT)
async def f1_schedule(interaction: discord.Interaction):
    embed = discord.Embed(title="2025 Formula 1 Race Schedule", color=0xFF0000)
    for race in schedule_2025.values():
        embed.add_field(name=race['name'], value=f"Date: {race['date']}\nTime: {race['time']} EST", inline=False)
    await interaction.response.send_message(embed=embed)

# Setup the cogs
async def setup_cogs():
    # Economy Cog
    economy_cog = Economy(client, GUILD_OBJECT,ROLES_ALLOWED_ADD_MONEY)
    await client.add_cog(economy_cog)
    client.add_money_to_user = economy_cog.add_money_to_user #Pulls this in from the economy cog
    
    # Games Cog
    games_cog = Games(client, GUILD_OBJECT,ROLES_ALLOWED_ADD_MONEY)
    await client.add_cog(games_cog)
    
    # LFG Cog
    lfg_cog = LookingForGroup(client, GUILD_OBJECT,GAME_ROLES)
    await client.add_cog(lfg_cog)
    
    # Shop Cog
    shop_cog = Shop(client, GUILD_OBJECT, ROLES_ALLOWED_ADD_MONEY, PURCHASE_LOG_CHANNEL)
    await client.add_cog(shop_cog)

# Main method
async def main():
    await client.setup_db() #Connect to the DB first
    await setup_cogs()
    await client.start(os.getenv('DISCORD_TOKEN'))

# Run main
if __name__ == '__main__':
    asyncio.run(main())