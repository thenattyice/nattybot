import discord
import traceback
from discord import app_commands, Member
from discord.ext import commands, tasks
from zoneinfo import ZoneInfo
from collections import defaultdict
import datetime

eastern = ZoneInfo("America/New_York")

class Businesses(commands.Cog):
    def __init__(self, bot, dailypayout_log_channel, guild_object, business_service):
        self.bot = bot
        self.dailypayout_log_channel = dailypayout_log_channel
        self.guild_object = guild_object
        self.business_service = business_service

    def cog_unload(self):
        self.daily_payout.cancel()
    
    async def payout_execution(self):    
        guild = self.bot.get_guild(self.guild_object.id)
        log_channel = guild.get_channel(self.dailypayout_log_channel)
        
        payout_records = await self.business_service.execute_payouts()
        
        if not payout_records:
            return
        
        # Build the embed description
        description = ""
        for record in payout_records:            
            breakdown_str = ", ".join(f"{name} ({amount})" for name, amount in record["breakdown"])
            description += f"<@{record['user_id']}> was paid {record['total']} NattyCoins for their businesses: {breakdown_str}\n"
        
        embed = discord.Embed(
            title="Daily Business Payout Report",
            description=description,
            color=discord.Color.gold()
        )
        
        await log_channel.send(embed=embed)
    
    #@tasks.loop(time=datetime.time(hour=4, minute=0, tzinfo=eastern))        
    @tasks.loop(time=minutes=4)
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
        
async def setup(bot, dailypayout_log_channel, guild_object, business_service):
    cog = Businesses(bot, dailypayout_log_channel, guild_object, business_service)          
    await bot.add_cog(cog)         
    cog.daily_payout.start()