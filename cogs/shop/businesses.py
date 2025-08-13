import discord
import traceback
from discord import app_commands, Member
from discord.ext import commands, tasks
import datetime
import pytz

eastern = pytz.timezone("US/Eastern")

business_details = {
        "mr_suds": {
            "shop_id": 4,
            "name":"Mr. Suds' Laundromat",
            "daily_payout": 10
        }
    }

class Businesses(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.shop_payout_lookup = {info["shop_id"]: info["daily_payout"] for info in business_details.values()}
        self.daily_payout.start()

    def cog_unload(self):
        self.daily_payout.cancel()
    
    # Get all of the business licenses per user from the shop
    async def get_businesses_per_user(self):
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch("""
            SELECT user_id, item_id, quantity FROM inventory
            WHERE is_business IS TRUE
            GROUP BY user_id, item_id;
            """)
        return rows
    
    async def per_user_business_calc(self):
        user_business = await self.get_businesses_per_user()
        
        payouts = []
        for row in user_business:
            shop_id = row["item_id"]
            quantity = row["quantity"]
            
            if shop_id in self.shop_payout_lookup:
                payout_amount = quantity * self.shop_payout_lookup[shop_id]
                payouts.append((row["user_id"], payout_amount))
            
        return payouts
            
    async def payout_execution(self):
        economy_cog = self.bot.get_cog('Economy')
        
        payouts = await self.per_user_business_calc()
        
        for user_id, payout in payouts:
            await economy_cog.add_money_to_user(user_id, payout)
            
    @tasks.loop(time=datetime.time(hour=15, minute=0, tzinfo=eastern))
    async def daily_payout(self):
        try:
            await self.payout_execution()
        except:
            traceback.print_exc()
        
    @daily_payout.before_loop
    async def before_daily_payout(self):
        await self.bot.wait_until_ready()
        
async def setup(bot):
    await bot.add_cog(Businesses(bot))