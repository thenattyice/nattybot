import discord
import random
import asyncio
import traceback
from discord import app_commands, Member
from discord.ext import commands
from .utils import bet_validation

class RPSView(discord.ui.View):
    def __init__(self, user: discord.User, bet: int, economy_cog, emoji_map, wins_against, timeout=15):
        super().__init__(timeout=timeout)
        self.user = user
        self.bet = bet
        self.economy_cog = economy_cog
        self.emoji_map = emoji_map
        self.wins_against = wins_against
        self.choice = None
        self.result_sent = False
        
    async def rps_result_handler(self, interaction: discord.Interaction, user_choice: str):
        if self.result_sent or interaction.user.id != self.user.id:
            return

        self.result_sent = True
        self.user_choice = user_choice
        bot_choice = random.choice(list(self.wins_against.keys()))
        user_id = self.user.id

        # Win conditions
        if user_choice == bot_choice:
            await interaction.response.send_message(f"It's a draw! Both picked {self.emoji_map[user_choice]} {user_choice}. You keep your {self.bet} NattyCoins.", ephemeral=True)
            return

        win = self.wins_against[user_choice] == bot_choice

        if win:
            winnings = self.bet
            await self.economy_cog.add_money_to_user(user_id, winnings)
            result = discord.Embed(
                title="🎉 You Win!",
                description=f"{self.emoji_map[user_choice]} {user_choice.capitalize()} beats {self.emoji_map[bot_choice]} {bot_choice.capitalize()}!\nYou won **{winnings}** NattyCoins!",
                color=discord.Color.green()
            )
        else:
            await self.economy_cog.remove_money_from_user(user_id, self.bet)
            result = discord.Embed(
                title="😢 You Lose!",
                description=f"{self.emoji_map[user_choice]} {user_choice.capitalize()} loses to {self.emoji_map[bot_choice]} {bot_choice.capitalize()}...\nYou lost **{self.bet}** NattyCoins.",
                color=discord.Color.red()
            )

        await interaction.response.send_message(embed=result, ephemeral=True)
        self.stop()

    # Buttons defined for the UI
    @discord.ui.button(label="Rock", emoji="🪨", style=discord.ButtonStyle.primary)
    async def rock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.rps_result_handler(interaction, "rock")

    @discord.ui.button(label="Paper", emoji="📄", style=discord.ButtonStyle.success)
    async def paper_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.rps_result_handler(interaction, "paper")

    @discord.ui.button(label="Scissors", emoji="✂️", style=discord.ButtonStyle.danger)
    async def scissors_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.rps_result_handler(interaction, "scissors")

# Class for all of the Games commands
class RockPaperScissors(commands.Cog):
    def __init__(self, bot, guild_object, allowed_roles):
        self.bot = bot
        self.guild_object = guild_object
        self.allowed_roles = allowed_roles
        
        # Register commands to my specific guild/server
        self.bot.tree.add_command(self.rock_paper_scissors, guild=self.guild_object)
    
    # Rock/Paper/Scissors game
    @app_commands.command(name="rps", description="Play Rock, Paper, Scissors with your NattyCoins")
    async def rock_paper_scissors(self, interaction: discord.Interaction, bet: int):
        
        economy_cog = self.bot.get_cog('Economy') # Connect to the Economy Cog to use economy functions: get_balance and add_money_to_user
        
        wins_against = {
        'rock': 'scissors',
        'scissors': 'paper',
        'paper': 'rock'
        }
        
        emoji_map = {
        'rock': '🪨',
        'paper': '📄',
        'scissors': '✂️'
        }
        
        user_id = interaction.user.id # Identify and store the user who ran the command
        try:
            if not await bet_validation(interaction, economy_cog, user_id, bet):
                return
            
            # Prompt the user to pick
            prompt_embed = discord.Embed(
                title="🎮 Natty Games: RPS 🎮",
                description="Select your choice to play Rock-Paper-Scissors:",
                color=discord.Color.red()
            )
            
            user = interaction.user
            view = RPSView(user, bet, economy_cog, emoji_map, wins_against)
            await interaction.response.send_message(embed=prompt_embed, view=view, ephemeral=True)
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send("An error occurred while running the game.", ephemeral=True)
            
async def setup(bot, guild_object, allowed_roles):
    await bot.add_cog(RockPaperScissors(bot, guild_object, allowed_roles))