import discord
import traceback
import re
import datetime
from zoneinfo import ZoneInfo
from discord import app_commands, Member, TextChannel
from discord.ext import commands, tasks

eastern = ZoneInfo("America/New_York")
class Wordle(commands.Cog):
    def __init__(self, bot, guild_object, wordle_app_id, economy_service):
        self.bot = bot
        self.guild_object = guild_object
        self.wordle_app_id = wordle_app_id
        self.economy_service = economy_service
        
        # Register commands to my specific guild/server
        self.bot.tree.add_command(self.wordle_championship, guild=self.guild_object) # /championship
        
    def cog_unload(self):
        self.monthly_wordle_champ_process.cancel()
    
    # Method to insert the wordle_pts
    async def add_wordle_pts_to_user(self, target_user_id: int, points: int):
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, wordle_pts)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET wordle_pts = users.wordle_pts + $2;
            """, target_user_id, points)
            
    # Function for pulling the wordle points data
    async def championship_pull(self):
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch("""SELECT 
                                    RANK() OVER (ORDER BY wordle_pts DESC) AS rank,
                                    user_id,
                                    wordle_pts
                                    FROM users LIMIT 5;""")
        
        description = '' # Init the field
        for row in rows:
            user_id = row['user_id']
            points = row['wordle_pts']
            rank = row['rank']
            
            # Mention the user based on id
            display_name = f"<@{user_id}>"
            
            # Add emoji for top 3
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"
            else:
                medal = f"#{rank}"
            
            description += f"**{medal}** – {display_name}: {points} points\n" # Formatting for each row in the embed
            
        # Discord embed structure
        championship_embed = discord.Embed(
            title="🏆 Wordle Championship Leaderboard 🏆",
            description=description,
            color=discord.Color.gold()
        )
        
        return championship_embed
        
    # Determine championship winner
    async def determine_champ(self):
        async with self.bot.db_pool.acquire() as conn:
            result = await conn.fetchrow("""WITH ranked AS (
                                            SELECT user_id, wordle_pts,
                                                RANK() OVER (ORDER BY wordle_pts DESC) AS rnk
                                            FROM users
                                        )
                                        SELECT user_id, wordle_pts
                                        FROM ranked
                                        WHERE rnk = 1;""")
        champion = result["user_id"]
        return champion
    
    # Create and assign the wordle champ role
    async def wordle_champ_role(self):
        try:
            guild = self.bot.get_guild(self.guild_object.id)
            
            # Get champ details
            champ_id = await self.determine_champ()
            
            champ = guild.get_member(champ_id)
            if champ is None:
                print(f"[WARN] Champion with ID {champ_id} not found in guild.")
                return
            
            # Get PREVIOUS month and year for the role name
            now = datetime.datetime.now(eastern)
            # Calculate first day of current month, then subtract 1 day to get last day of previous month
            first_day_current = now.replace(day=1)
            previous_month = first_day_current - datetime.timedelta(days=1)
            role_name = f"Wordle Champion - {previous_month.strftime('%B %Y')}"
            
            # Create the role for current month/year
            # Check if role already exists
            existing_role = discord.utils.get(guild.roles, name=role_name)
            if existing_role:
                wordle_champ_role = existing_role
            else:
                wordle_champ_role = await guild.create_role(
                    name=role_name,
                    color=discord.Color.yellow(),
                    reason="Monthly Wordle Champion role"
                )
            
            # Assign it to the champ
            await champ.add_roles(wordle_champ_role, reason="Awarded Wordle Champion")
            print(f"[DEBUG] Assigned {role_name} to {champ.display_name}")
            return True
        except Exception:
            traceback.print_exc()
            return False
    
    # Clear all wordle champ pts monthly
    @tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=eastern))
    async def monthly_wordle_champ_process(self):
        now = datetime.datetime.now(eastern)
        if now.day != 1:  # Only run on the 1st of the month
            return
        
        success = await self.wordle_champ_role()
        if success:
            # Clear the points
            try:
                async with self.bot.db_pool.acquire() as conn:
                    rows = await conn.execute("""
                                        WITH users_with_pts AS (
                                            SELECT user_id FROM users
                                            WHERE wordle_pts > 0
                                        )
                                        UPDATE users
                                        SET wordle_pts = 0
                                        FROM users_with_pts uwp
                                        WHERE users.user_id = uwp.user_id
                                    """)
                print("[TASK] Monthly Wordle Championship Points reset completed!")
            except:
                traceback.print_exc()
                print("[ERROR] Monthly Wordle Championship Points reset FAILED!")
        else:
            print("[ERROR] Failed to process the champion and their role")
    
    @monthly_wordle_champ_process.before_loop
    async def before_monthly_wordle_champ_process(self):
        await self.bot.wait_until_ready()
        print("[DEBUG] monthly_wordle_champ_process loop starting")
    
    # Event listener for the Wordle channel, specifically tracking daily results
    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            # Ignore DMs
            if not isinstance(message.channel, TextChannel):
                return
            
            if message.channel.name != 'wordle': # Filter for the 'wordle' channel
                return
            
            if message.author.id != self.wordle_app_id: # Filter for only messages by the Wordle app
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
                await economy_service.add_money_to_user(user_id, reward)
                
                points = self.calculate_wordle_pts(score)
                await self.add_wordle_pts_to_user(user_id, points)

                member = message.guild.get_member(user_id)
                if member:
                    description += f"{member.mention} is awarded **{reward}** NattyCoins🪙 and **{points}** championship points!\n"
                else:
                    print(f"⚠️ Could not find member with ID {user_id} to announce reward.")
            
            if description:    
                reward_embed = discord.Embed(
                    title="🪙**Daily Wordle Rewards**🪙",
                    description=description,
                    color=discord.Color.gold()
                )
                
                await message.channel.send(embed=reward_embed)
            
            # Display the Wordle points championship leaderboard
            championship_embed = await self.championship_pull()
            await message.channel.send(embed=championship_embed)
            
            # Display the NattyCoin leaderboard
            leaderboard_embed = await economy_cog.leaderboard_pull()
            await message.channel.send(embed=leaderboard_embed)

            await self.bot.process_commands(message)
        except Exception as e:
            traceback.print_exc()

    # Function to calc the NattyCoins reward
    @staticmethod               
    def calculate_wordle_reward(score):
        return 0 if score == 0 else max(0, 7 - score) * 10
    
    # Function to calc the wordle_pts score reward
    @staticmethod               
    def calculate_wordle_pts(score):
        return 0 if score == 0 else max(0, 7 - score)
    
    # Leaderboard command
    @app_commands.command(name="championship", description="Shows the Wordle points championship leaderboard")
    async def wordle_championship(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Display the Wordle points championship leaderboard
        championship_embed = await self.championship_pull()
        await interaction.followup.send(embed=championship_embed)
        
async def setup(bot, guild_object, wordle_app_id, economy_service):
    cog = Wordle(bot, guild_object, wordle_app_id, economy_service)          
    await bot.add_cog(cog) 
    cog.monthly_wordle_champ_process.start()