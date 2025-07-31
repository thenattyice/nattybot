import discord
import traceback
from discord import app_commands, Member
from discord.ext import commands

class LFG(commands.Cog):
    def __init__(self, bot, guild_object, game_roles):
        self.bot = bot
        self.guild_object = guild_object
        self.game_roles = game_roles
        
        # Registrations of commands
        self.bot.tree.add_command(self.rl, guild=self.guild_object)
        
    @app_commands.command(name="rl", description="Tag all user's with the Rocket League role to get some games going!")
    async def rl(self, interaction: discord.Interaction):
        role_id = self.bot.game_roles["rocket league"]
        role = interaction.guild.get_role(role_id)
        
        if role is None:
            await interaction.response.send_message("Role not found!", ephemeral=True)
            return
        
        await interaction.response.send_message(f"{role.mention}")