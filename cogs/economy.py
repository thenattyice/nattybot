import discord
import traceback
from discord import app_commands, Member
from discord.ext import commands

class Economy(commands.Cog):
    def __init__(self, bot, guild_object, allowed_roles, economy_service):
        self.bot = bot
        self.guild_object = guild_object
        self.allowed_roles = allowed_roles
        self.economy_service = economy_service
        
        # Register commands to my specific guild/server
        self.bot.tree.add_command(self.balance_check, guild=self.guild_object)
        self.bot.tree.add_command(self.add_money, guild=self.guild_object)
        self.bot.tree.add_command(self.remove_money, guild=self.guild_object)
        self.bot.tree.add_command(self.leaderboard, guild=self.guild_object)
    
    
    async def build_leaderboard(self):
        rows = await self.economy_service.get_leaderboard()
        
        description = '' # Init the field
        for row in rows:
            user_id = row['user_id']
            balance = row['balance']
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
            
            description += f"**{medal}** – {display_name}: {balance} coins\n" # Formatting for each row in the embed
            
        #Discord embed structure
        leaderboard_embed = discord.Embed(
            title="🏆 NattyCoin Leaderboard 🏆",
            description=description,
            color=discord.Color.gold()
        )
        
        return leaderboard_embed
        
    # Balance check command
    @app_commands.command(name="balance", description="Check your balance")
    async def balance_check(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        balance = await self.economy_service.get_balance(user_id)
        
        await interaction.response.send_message(f"Your balance is {balance} NattyCoins.", ephemeral=True)
        
    # Add money command
    @app_commands.command(name="addmoney", description="Add currency to a user's balance")
    async def add_money(self, interaction: discord.Interaction, user: Member, amount: int):
        user_role_ids = [role.id for role in interaction.user.roles]
        if not any(role_id in self.allowed_roles for role_id in user_role_ids):
            await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("The balance addition cannot be negative.", ephemeral=True)
            return

        target_user_id = user.id
        
        await self.economy_service.add_money_to_user(target_user_id, amount)

        await interaction.response.send_message(f"Added {amount} coins to {user.mention}'s balance.", ephemeral=True)
        
    # Remove money command
    @app_commands.command(name="removemoney", description="Remove currency from a user's balance")
    async def remove_money(self, interaction: discord.Interaction, user: Member, amount: int):
        user_role_ids = [role.id for role in interaction.user.roles]
        if not any(role_id in self.allowed_roles for role_id in user_role_ids):
            await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("The balance edit cannot be negative.", ephemeral=True)
            return

        target_user_id = user.id
        
        result = await self.economy_service.get_balance(target_user_id)
        current_balance = result["balance"] if result else 0
        
        if current_balance < amount:
            await interaction.response.send_message(f"The balance removal cannot be larger than the user's current balance. {user.mention}'s current balance: {current_balance} NattyCoins.", ephemeral=True)
            return

        await self.economy_service.remove_money_from_user(target_user_id, amount)

        await interaction.response.send_message(f"Removed {amount} coins from {user.mention}'s balance.", ephemeral=True)
        
    # Leaderboard command
    @app_commands.command(name="leaderboard", description="Displays a leaderboard based on NattyCoin balance among users")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            leaderboard_embed = await self.build_leaderboard()
                
            await interaction.followup.send(embed=leaderboard_embed)
            
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send("An error occurred while fetching the leaderboard.", ephemeral=True)
            
async def setup(bot, guild_object, allowed_roles, economy_service):
    await bot.add_cog(Economy(bot, guild_object, allowed_roles, economy_service))