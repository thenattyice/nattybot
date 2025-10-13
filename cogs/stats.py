import discord
import traceback
from services.user_service import UserStats
from discord import app_commands, Member
from discord.ext import commands

class Stats(commands.Cog):
    def __init__(self, bot, guild_object, allowed_roles, user_service):
        self.bot = bot
        self.guild_object = guild_object
        self.allowed_roles = allowed_roles
        self.user_service = user_service
    
        # Register commands here
        self.bot.tree.add_command(self.stats_card, guild=self.guild_object)
    
    @app_commands.command(name="stats", description="View your stats card!")
    @app_commands.describe(member="The member to view stats for (optional, defaults to you)")
    async def stats_card(self, interaction: discord.Interaction, member: discord.Member = None):
        user = member or interaction.user
        user_id = user.id
        
        # Get the stats
        user_stats = await self.user_service.build_user_stats(user_id)
        
        # Build the embed
        embed = discord.Embed(
            title=f"📊 {user.display_name}'s Stats 📊",
            color=discord.Color.blue()
        )
        
        # Set the user's avatar as the thumbnail
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Add fields for each stat
        embed.add_field(name="💰 Balance", value=f"{user_stats.balance:,} NattyCoins", inline=True)
        embed.add_field(name="📝 Wordle Points", value=f"{user_stats.wordle_points:,}", inline=True)
        embed.add_field(name="🎲 Total Wagered", value=f"{user_stats.total_wagered:,}", inline=True)
        embed.add_field(name="🎮 Total Games", value=f"{user_stats.total_games:,}", inline=True)
        embed.add_field(name="⭐ Favorite Game", value=user_stats.favorite_game or "None", inline=True)
        embed.add_field(name="🏆 Win Ratio", value=f"{user_stats.win_ratio:.1%}", inline=True)
        
        # Send the embed
        await interaction.response.send_message(embed=embed)
        
async def setup(bot, guild_object, allowed_roles, user_service):
    await bot.add_cog(Stats(
        bot, 
        guild_object, 
        allowed_roles,
        user_service
    ))