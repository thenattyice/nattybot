import discord
import random
import asyncio
import traceback
from zoneinfo import ZoneInfo
import datetime
from discord import app_commands, Member
from discord.ext import commands, tasks

eastern = ZoneInfo("America/New_York")

class FreeDailySpin(commands.Cog):
    def __init__(self, bot, guild_object):
        self.bot = bot
        self.guild_object = guild_object
        
        self.bot.tree.add_command(self.daily_spin, guild=self.guild_object) # Command reg
    
    async def daily_spin_check(self, user_id: int):
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                                WITH ins AS (
                                    INSERT INTO users (user_id, daily_spin)
                                    VALUES ($1, false)
                                    ON CONFLICT (user_id) DO NOTHING
                                    RETURNING daily_spin
                                )
                                SELECT daily_spin FROM ins
                                UNION ALL
                                SELECT daily_spin FROM users WHERE user_id = $1
                                LIMIT 1
                            """, user_id)
            
            daily_spin_status = row["daily_spin"]
            
        return daily_spin_status
    
    @tasks.loop(time=datetime.time(hour=4, minute=0, tzinfo=eastern))
    async def nightly_spin_status_reset(self):
        try:
            async with self.bot.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                                    WITH users_who_spun AS (
                                        SELECT user_id FROM users
                                        WHERE daily_spin = TRUE
                                    )
                                    UPDATE users
                                    SET daily_spin = FALSE
                                    FROM users_who_spun uws
                                    WHERE users.user_id = uws.user_id
                                """)
            print("[TASK] Nightly free wheel spin reset completed!")
        except:
            traceback.print_exc()
            print("[ERROR] Nightly free wheel spin reset FAILED!")
        
    # Wheel spin game command 
    @app_commands.command(name="dailyspin", description="Take 1 free spin on the Natty Wheel for a random amount of NattyCoins between 1 and 20")
    async def daily_spin(self, interaction: discord.Interaction):
        economy_cog = self.bot.get_cog('Economy') # Connect to the Economy Cog to use economy functions: get_balance and add_money_to_user
        
        user_id = interaction.user.id
        
        daily_spin_status = await self.daily_spin_check(user_id)
        
        description = ""
        
        embed = discord.Embed(
                title="🎡Daily Free Wheel Spin🎡",
                description=description,
                color=discord.Color.gold()
            )
        
        if daily_spin_status is True:
            embed.description = "You have already spun today!"
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        elif daily_spin_status is False:
            wheel_values = list(range(1,21)) # 20 slots on the wheel
            result = random.choice(wheel_values) # Winning num picked randomly
            
            current_index = random.randint(0, len(wheel_values) - 1)
            
            total_ticks = 30 # Number of ticks before landing
            
            cycles = 2 # Number of full spins before stopping
            final_index = wheel_values.index(result)
            
            # Calculate total ticks to land exactly on result
            total_ticks = cycles * len(wheel_values) + ((final_index - current_index) % len(wheel_values))
            
            embed.description = "Spinning the wheel..."
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            msg = await interaction.original_response()
            
            # Simulate the spin with a slow down through a for loop
            for i in range(total_ticks): 
                # During animation, just show random numbers
                num = wheel_values[current_index]
                embed.description = f"The wheel shows: **{num}**"
                await msg.edit(embed=embed)
                
                # Slows down as loop iterates
                await asyncio.sleep(0.1 + (i * 0.03)) 
                
                # Move forward one slot to land on the actual result
                current_index = (current_index + 1) % len(wheel_values)
            
            # Award coins and check new balance
            await economy_cog.add_money_to_user(user_id, result)
            new_balance = await economy_cog.get_balance(user_id)
                
            embed.description = f"🎉The wheel lands on: **{result}**\nYou won **{result}** NattyCoins!\nNew balance: **{new_balance}** NattyCoins"
            embed.color = discord.Color.green()
            await msg.edit(embed=embed)
            
            try:
                # Mark a user as having spun today
                async with self.bot.db_pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE users SET daily_spin = TRUE WHERE user_id = $1",
                        user_id
                    )
                print(f"[DEBUG] {user_id} - daily_spin is now TRUE")
            except:
                traceback.print_exc()
                
# Cog setup method
async def setup(bot, guild_object):
    await bot.add_cog(FreeDailySpin(bot, guild_object))