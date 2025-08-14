import discord
import traceback
from discord import app_commands, Member
from discord.ext import commands, tasks
from zoneinfo import ZoneInfo
import datetime

eastern = ZoneInfo("America/New_York")

class Businesses(commands.Cog):
    def __init__(self, bot, dailypayout_log_channel):
        self.bot = bot
        self.dailypayout_log_channel = dailypayout_log_channel

    def cog_unload(self):
        self.daily_payout.cancel()
    
    # Get all of the business licenses per user from the shop
    async def get_businesses_per_user(self):
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch("""
            SELECT i.user_id, i.quantity, s.daily_payout FROM inventory i
            JOIN shop s ON s.id = i.item_id 
            WHERE s.is_business IS TRUE AND s.daily_payout > 0
            ORDER BY i.user_id;
            """)
        return rows
    
    async def per_user_business_calc(self):
        rows = await self.get_businesses_per_user()
        
        payouts = []
        for row in rows:
            user_id = row["user_id"]
            quantity = row["quantity"]
            daily_payout = row["daily_payout"]
            
            payout_amount = quantity * daily_payout
            payouts.append((row["user_id"], payout_amount))
            
        return payouts
            
    async def payout_execution(self):
        economy_cog = self.bot.get_cog('Economy')
        
        payouts = await self.per_user_business_calc()
        
        guild = self.bot.get_guild(self.guild_object.id)
        log_channel = guild.get_channel(self.dailypayout_log_channel)
        
        description = ""
        for user_id, payout in payouts:
            await economy_cog.add_money_to_user(user_id, payout)
            description += f"{user_id} was paid {payout} NattyCoins for their owned businesses!\n"
        
        embed = discord.Embed(
            title="Daily Business Payout Report",
            description=description,
            color=discord.Color.gold()
        )
        
        await log_channel.send(embed=embed)
            
    @tasks.loop(time=datetime.time(hour=16, minute=28, tzinfo=eastern))
    async def daily_payout(self):
        try:
            print(f"[DEBUG] daily_payout triggered at {datetime.datetime.now(eastern)}")
            await self.payout_execution()
        except:
            traceback.print_exc()
        
    @daily_payout.before_loop
    async def before_daily_payout(self):
        await self.bot.wait_until_ready()
        print("[DEBUG] daily_payout loop starting")
        
async def setup(bot, dailypayout_log_channel):
    cog = Businesses(bot, dailypayout_log_channel)          
    await bot.add_cog(cog)         
    cog.daily_payout.start()