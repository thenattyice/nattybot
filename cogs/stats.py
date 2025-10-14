import discord
import traceback
from services.user_service import UserStats
from discord import app_commands, Member
from discord.ext import commands

class Stats(commands.Cog):
    def __init__(self, bot, guild_object, allowed_roles, user_service, game_service):
        self.bot = bot
        self.guild_object = guild_object
        self.allowed_roles = allowed_roles
        self.user_service = user_service
        self.game_service = game_service
    
        # Register commands here
        self.bot.tree.add_command(self.stats_card, guild=self.guild_object)
        self.bot.tree.add_command(self.gamba_leaderboard, guild=self.guild_object)
    
    async def build_leaderboard(self):
        rows = await self.game_service.get_gambling_leaderboard()
        
        description = '' # Init the field
        for row in rows:
            user_id = row['user_id']
            total_wagered = row['total_wagered']
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
            
            description += f"**{medal}** – {display_name}: {total_wagered} NattyCoins\n" # Formatting for each row in the embed
            
        #Discord embed structure
        leaderboard_embed = discord.Embed(
            title="🎰 Gamba Leaderboard 🎰",
            description=description,
            color=discord.Color.gold()
        )
        
        return leaderboard_embed
    
    @app_commands.command(name="stats", description="View the gambling leaderboard!")
    async def gamba_leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            leaderboard_embed = await self.build_leaderboard()
                
            await interaction.followup.send(embed=leaderboard_embed)
            
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send("An error occurred while fetching the leaderboard.", ephemeral=True)
    
    @app_commands.command(name="stats", description="View your stats card!")
    @app_commands.describe(member="The member to view stats for (optional, defaults to you)")
    async def stats_card(self, interaction: discord.Interaction, member: discord.Member = None):
        try:
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
            embed.add_field(name="💰 Balance", value=f"{user_stats.balance:,} NattyCoins", inline=False)
            embed.add_field(name="📝 Wordle Points", value=f"{user_stats.wordle_points:,}", inline=False)
            embed.add_field(name="🎲 Total Wagered", value=f"{user_stats.total_wagered:,}", inline=False)
            embed.add_field(name="🎮 Total Games", value=f"{user_stats.total_games:,}", inline=False)
            embed.add_field(name="⭐ Favorite Game", value=user_stats.favorite_game or "None", inline=False)
            embed.add_field(name="🏆 Win Ratio", value=f"{user_stats.win_ratio:.1%}", inline=False)
            
            # Send the embed
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception:
            traceback.print_exc()
        
async def setup(bot, guild_object, allowed_roles, user_service, game_service):
    await bot.add_cog(Stats(
        bot, 
        guild_object, 
        allowed_roles,
        user_service,
        game_service
    ))