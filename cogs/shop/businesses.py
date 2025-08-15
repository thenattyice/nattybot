import discord
import traceback
from discord import app_commands, Member
from discord.ext import commands, tasks
from zoneinfo import ZoneInfo
from collections import defaultdict
import datetime

eastern = ZoneInfo("America/New_York")

class Businesses(commands.Cog):
    def __init__(self, bot, dailypayout_log_channel, guild_object):
        self.bot = bot
        self.dailypayout_log_channel = dailypayout_log_channel
        self.guild_object = guild_object

    def cog_unload(self):
        self.daily_payout.cancel()
    
    # Gat all businesses for a specified user
    async def get_specific_users_businesses(self, target_user_id: int):
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch("""
            SELECT s.id AS item_id, s.name
            FROM inventory i
            JOIN shop s ON s.id = i.item_id 
            WHERE i.user_id = $1
            AND i.is_business IS TRUE
            """, target_user_id)
        return rows
    
    # Get all of the business licenses per user from the shop
    async def get_businesses_per_user(self):
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch("""
            SELECT i.user_id, s.name, s.daily_payout
            FROM inventory i
            JOIN shop s ON s.id = i.item_id 
            WHERE s.is_business IS TRUE AND s.daily_payout > 0
            """)
        return rows
    
    async def per_user_business_calc(self):
        rows = await self.get_businesses_per_user()
        
        payouts = []
        for row in rows:
            user_id = row["user_id"]
            biz_name = row["name"]
            daily_payout = row["daily_payout"]
            
            payouts_dict = defaultdict(lambda: {"total": 0, "breakdown": []})
            
            payouts_dict[user_id]["total"] += daily_payout
            payouts_dict[user_id]["breakdown"].append((biz_name, daily_payout))
            
        return payouts_dict
            
    async def payout_execution(self):
        economy_cog = self.bot.get_cog('Economy')
        
        payouts = await self.per_user_business_calc()
        
        guild = self.bot.get_guild(self.guild_object.id)
        log_channel = guild.get_channel(self.dailypayout_log_channel)
        
        description = ""
        for user_id, payout in payouts:
            total = data["total"]
            breakdown = data["breakdown"]
            
            await economy_cog.add_money_to_user(user_id, total)
            
            breakdown_str = ", ".join(f"{name} ({amount})" for name, amount in breakdown)
            description += f"<@{user_id}> was paid {payout} NattyCoins for their businesses: {breakdown_str}\n"
        
        embed = discord.Embed(
            title="Daily Business Payout Report",
            description=description,
            color=discord.Color.gold()
        )
        
        await log_channel.send(embed=embed)
            
    @tasks.loop(time=datetime.time(hour=20, minute=20, tzinfo=eastern))
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
        
async def setup(bot, dailypayout_log_channel, guild_object):
    cog = Businesses(bot, dailypayout_log_channel, guild_object)          
    await bot.add_cog(cog)         
    cog.daily_payout.start()