import discord
import traceback
import re
import datetime
from zoneinfo import ZoneInfo
from discord import app_commands, Member, TextChannel
from discord.ext import commands, tasks
from typing import Optional

eastern = ZoneInfo("America/New_York")
class Wordle(commands.Cog):
    def __init__(self, bot, guild_object, wordle_app_id, wordle_channel, economy_service, wordle_service):
        self.bot = bot
        self.guild_object = guild_object
        self.wordle_app_id = wordle_app_id
        self.wordle_channel = wordle_channel
        self.economy_service = economy_service
        self.wordle_service = wordle_service
        
        print(f"[DEBUG] Wordle App ID passed to cog: {wordle_app_id}")
        
        # Register commands to my specific guild/server
        self.bot.tree.add_command(self.wordle_championship, guild=self.guild_object) # /championship
        #self.bot.tree.add_command(self.test_monthly_champ, guild=self.guild_object) # /test-monthly-champ
        
    def cog_unload(self):
        self.monthly_wordle_champ_process.cancel()
    
    # Create and assign the wordle champ role
    async def assign_wordle_champ_role(self, champ_id):
        try:
            # Get the actual Guild object
            guild = self.bot.get_guild(self.guild_object.id)
            
            # Get the champion member
            champ = guild.get_member(champ_id)
            if not champ:
                print(f"[WARN] Champion with ID {champ_id} not found in guild.")
                return False
            
            # Get previous month and year for the role name
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
        except Exception as e:
            print(f"[ERROR]: {e}")
            traceback.print_exc()
            return False
    
    # Method to build the monthly winner embed
    async def monthly_winner_embed(self, champ_id):
        
        champ_embed = discord.Embed(
            title="**Monthly Wordle Championship**",
            description=f"WINNER: <@{champ_id}>\n\nThe month has ended and a new one begins!\n\nWho will be the Wordle Champ?!",
            color=discord.Color.gold()
        )
        return champ_embed
    
    # Clear all wordle champ pts monthly AND crown the champion
    @tasks.loop(time=datetime.time(hour=12, minute=0, tzinfo=eastern))
    async def monthly_wordle_champ_process(self):
        
        wordle_channel = self.bot.get_channel(self.wordle_channel)
        
        now = datetime.datetime.now(eastern)
        if now.day != 1:  # Only run on the 1st of the month
            return
        
        champ_id = await self.wordle_service.determine_champ() # Get champ user ID
        
        success = await self.assign_wordle_champ_role(champ_id) # Process to create and assign the champ role
        if success:
            try:
                champ_embed = await self.monthly_winner_embed(champ_id) # Call the announcement embed
                
                await wordle_channel.send(embed=champ_embed) # Send the embed message
                
                await self.wordle_service.clear_all_wordle_pts() # Clear the points
                
                print("[TASK] Monthly Wordle Championship Points reset completed!")
            except Exception as e:
                traceback.print_exc()
                print(f"[ERROR] Monthly Wordle Championship Points reset FAILED! Error: {e}")
        else:
            print("[ERROR] Failed to process the champion and their role")
    
    # Start the task loop
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

            economy_cog = self.bot.get_cog("Economy")
            if not economy_cog:
                print("[ERROR] Economy cog not found")
                return
            
            # Process the wordle streaks (only if users played) and log the scores in wordle_streaks table
            if user_rewards:
                await self.wordle_service.wordle_streak_process(list(user_rewards.keys()))
                
                # Log all of the wordle results
                await self.wordle_service.log_wordle_results(user_rewards)
            
            for user_id, score in user_rewards.items():
                
                # Get wordle streak count
                current_streak = await self.wordle_service.get_user_wordle_streak(user_id)
                
                # NattyCoin payout
                reward = self.calculate_wordle_reward(score)
                
                # Check for wordle streak multiplier
                multiplier = await self.wordle_service.wordle_payout_multiplier(reward, user_id)
                
                payout = round(reward * multiplier)
                
                await self.economy_service.add_money_to_user(user_id, payout)
                
                # Wordle points
                points = self.calculate_wordle_pts(score)
                await self.wordle_service.add_wordle_pts_to_user(user_id, points)

                member = message.guild.get_member(user_id)
                if member:
                    description += f"{member.mention} is awarded **{payout}** NattyCoins🪙 and **{points}** championship points! (Current streak: {current_streak} - {multiplier}x payout)\n"
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
            championship_embed = await self.wordle_service.championship_pull()
            await message.channel.send(embed=championship_embed)
            
            # Display the NattyCoin leaderboard
            leaderboard_embed = await economy_cog.build_leaderboard()
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
        championship_embed = await self.wordle_service.championship_pull()
        await interaction.followup.send(embed=championship_embed)
    
    # Command to get a player's wordle summary for a month
    @app_commands.command(name="wordle_stats", description="Shows a player's wordle summary for a given month")
    @app_commands.choices(month=[
        app_commands.Choice(name="January", value=1),
        app_commands.Choice(name="February", value=2),
        app_commands.Choice(name="March", value=3),
        app_commands.Choice(name="April", value=4),
        app_commands.Choice(name="May", value=5),
        app_commands.Choice(name="June", value=6),
        app_commands.Choice(name="July", value=7),
        app_commands.Choice(name="August", value=8),
        app_commands.Choice(name="September", value=9),
        app_commands.Choice(name="October", value=10),
        app_commands.Choice(name="November", value=11),
        app_commands.Choice(name="December", value=12)
    ])
    async def wordle_stats(self,
                           interaction: discord.Interaction,
                           member: Optional[discord.Member] = None,
                           month: Optional[app_commands.Choice[int]] = None,
                           year: Optional[app_commands.Range[int, 2026, 2100]] = None
                           ):
        try:
            user = member or interaction.user
            user_id = user.id
            
            today = datetime.datetime.now()
            month_value = month.value if month is not None else today.month
            year_value = year if year is not None else today.year
            
            results = await self.wordle_service.user_wordle_summary(user_id, month_value, year_value)
            
            if not results:
                await interaction.response.send_message(f"Could not find any Wordle stats for that combination of Player: {user}, Month: {month_value}, and Year: {year_value}", ephemeral=True)
                return
                
            # Build the embed
            embed = discord.Embed(
                title=f"📊 {user.display_name}'s Wordle Stats 📊",
                color=discord.Color.gold()
            )
            
            # Set the user's avatar as the thumbnail
            embed.set_thumbnail(url=user.display_avatar.url)
            
            # Add the fields for each stat
            avg_guesses_display = f"{results['avg_guesses']:,}" if results['avg_guesses'] is not None else "N/A"
            embed.add_field(name="Avg Guess Count", value=f"{avg_guesses_display}", inline=False)
            embed.add_field(name="Wins in 1", value=f"{results['guess_1']:,}", inline=False)
            embed.add_field(name="Wins in 2", value=f"{results['guess_2']:,}", inline=False)
            embed.add_field(name="Wins in 3", value=f"{results['guess_3']:,}", inline=False)
            embed.add_field(name="Wins in 4", value=f"{results['guess_4']:,}", inline=False)
            embed.add_field(name="Wins in 5", value=f"{results['guess_5']:,}", inline=False)
            embed.add_field(name="Wins in 6", value=f"{results['guess_6']:,}", inline=False)
            embed.add_field(name="Fails", value=f"{results['guess_fail']:,}", inline=False)
            
            # Send the embed
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            traceback.print_exc()
            print(f"[WORDLE STATS] Error retrieving stats for user_id: {user_id}. Error: {e}")
            await interaction.response.send_message(f"Error retrieving stats for user_id: {user}. Error: {e}", ephemeral=True)
        
    @app_commands.command(name="test-monthly-champ", description="[DEV] Test the monthly champion process")
    @app_commands.checks.has_permissions(administrator=True)
    async def test_monthly_champ(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            # Get the champion
            champ_id = await self.wordle_service.determine_champ()
            if not champ_id:
                await interaction.followup.send("No champion found (no wordle scores recorded yet)")
                return
            
            # Process the champion role assignment
            success = await self.assign_wordle_champ_role(champ_id)
            if not success:
                await interaction.followup.send("Failed to assign champion role")
                return
            
            # Send the announcement
            champ_embed = await self.monthly_winner_embed(champ_id)
            wordle_channel = self.bot.get_channel(self.wordle_channel)
            await wordle_channel.send(embed=champ_embed)
            
            # Clear points
            await self.wordle_service.clear_all_wordle_pts()
            
            await interaction.followup.send("✅ Monthly champion process completed (test)")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")
            traceback.print_exc()

async def setup(bot, guild_object, wordle_app_id, wordle_channel, economy_service, wordle_service):
    cog = Wordle(bot, guild_object, wordle_app_id, wordle_channel, economy_service, wordle_service)          
    await bot.add_cog(cog) 
    cog.monthly_wordle_champ_process.start()