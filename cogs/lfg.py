import discord
import traceback
from discord import app_commands, Member
from discord.ext import commands

class LookingForGroup(commands.Cog):
    def __init__(self, bot, guild_object, game_roles):
        self.bot = bot
        self.guild_object = guild_object
        self.game_roles = game_roles
        
        # Registrations of commands
        self.bot.tree.add_command(self.rl, guild=self.guild_object)
        self.bot.tree.add_command(self.rematch, guild=self.guild_object)
        self.bot.tree.add_command(self.mtg, guild=self.guild_object)
        
    # Rocket league
    @app_commands.command(name="rl", description="Tag all user's with the Rocket League role to get some games going!")
    async def rl(self, interaction: discord.Interaction):
        try:
            role_id = self.bot.game_roles["rocket league"]
            role = interaction.guild.get_role(role_id)
            
            if role is None:
                await interaction.response.send_message("Role not found!", ephemeral=True)
                return
            
            await interaction.response.send_message(f"{role.mention} Time for some games!",allowed_mentions=discord.AllowedMentions(roles=True))
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send("An error occurred while running the game.", ephemeral=True)
        
    # Rematch
    @app_commands.command(name="rematch", description="Tag all user's with the Rematch role to get some games going!")
    async def rematch(self, interaction: discord.Interaction):
        role_id = self.bot.game_roles["rematch"]
        role = interaction.guild.get_role(role_id)
        
        if role is None:
            await interaction.response.send_message("Role not found!", ephemeral=True)
            return
        
        await interaction.response.send_message(f"{role.mention} Time for some matches!",allowed_mentions=discord.AllowedMentions(roles=True))
        
    # MTG
    @app_commands.command(name="mtg", description="Tag all user's with the Magic Nerd role to get some games going!")
    async def mtg(self, interaction: discord.Interaction):
        role_id = self.bot.game_roles["mtg"]
        role = interaction.guild.get_role(role_id)
        
        if role is None:
            await interaction.response.send_message("Role not found!", ephemeral=True)
            return
        
        await interaction.response.send_message(f"{role.mention} Time for some commander!",allowed_mentions=discord.AllowedMentions(roles=True))