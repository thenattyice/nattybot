import discord
import traceback
from discord import app_commands, Member
from discord.ext import commands, tasks
import datetime
import pytz

eastern = pytz.timezone("US/Eastern")

class Businesses(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_payout.start()

    def cog_unload(self):
        self.daily_payout.cancel()
    
    # Get all of the business licenses per user from the shop
    async def get_businesses_per_user(self):
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch("""
            SELECT i.user_id, i.quantity, s.daily_payout FROM inventory i
            JOIN shop s ON s.item_id = i.item_id 
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
        
        for user_id, payout in payouts:
            await economy_cog.add_money_to_user(user_id, payout)
            
    @tasks.loop(time=datetime.time(hour=13, minute=0, tzinfo=eastern))
    async def daily_payout(self):
        try:
            await self.payout_execution()
        except:
            traceback.print_exc()
        
    @daily_payout.before_loop
    async def before_daily_payout(self):
        await self.bot.wait_until_ready()
        
async def setup(bot):
    try:
        await bot.add_cog(Businesses(bot))
        print("Businesses cog loaded successfully!")
    except:
        traceback.print_exc()