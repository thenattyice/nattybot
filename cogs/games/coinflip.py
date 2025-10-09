import discord
import random
import asyncio
import traceback
from discord import app_commands, Member
from discord.ext import commands

class CoinFlipView(discord.ui.View):
    def __init__(self, user: discord.User, bet: int, emoji_map, economy_service, timeout=15):
        super().__init__(timeout=timeout)
        self.user = user
        self.bet = bet
        self.emoji_map = emoji_map
        self.economy_service = economy_service
        self.choice = None
        self.result_sent = False
    
    async def coinflip_result_handler(self, interaction: discord.Interaction, user_choice: str):    
        if self.result_sent or interaction.user.id != self.user.id:
                return

        self.result_sent = True
        self.user_choice = user_choice
        bot_choice = random.choice(["heads", "tails"])
        user_id = self.user.id

        # Win conditions
        win = self.user_choice == bot_choice

        if win:
            winnings = self.bet
            await self.economy_service.add_money_to_user(user_id, winnings)
            new_balance = await self.economy_service.get_balance(user_id)
            result = discord.Embed(
                title="🎉 You Win!",
                description=f"The bot flipped... {self.emoji_map[bot_choice]} {bot_choice.capitalize()}!\nYou won **{winnings}** NattyCoins!\nNew balance: **{new_balance}** NattyCoins",
                color=discord.Color.green()
            )
        else:
            await self.economy_service.remove_money_from_user(user_id, self.bet)
            new_balance = await self.economy_service.get_balance(user_id)
            result = discord.Embed(
                title="😢 You Lose!",
                description=f"{self.emoji_map[user_choice]} {user_choice.capitalize()} loses to {self.emoji_map[bot_choice]} {bot_choice.capitalize()}...\nYou lost **{self.bet}** NattyCoins.\nNew balance: **{new_balance}** NattyCoins",
                color=discord.Color.red()
            )

        await interaction.followup.send(embed=result, ephemeral=True)
        self.stop()
        
    # Buttons defined for the UI
    @discord.ui.button(label="Heads", emoji="👤", style=discord.ButtonStyle.primary)
    async def heads_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
            
        await interaction.response.edit_message(view=self)    
        await self.coinflip_result_handler(interaction, "heads")

    @discord.ui.button(label="Tails", emoji="🍑", style=discord.ButtonStyle.success)
    async def tails_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
            
        await interaction.response.edit_message(view=self)
        await self.coinflip_result_handler(interaction, "tails")
        
        
        
class CoinFlip(commands.Cog):
    def __init__(self, bot, guild_object, economy_service):
        self.bot = bot
        self.guild_object = guild_object
        self.economy_service = economy_service
        
        self.bot.tree.add_command(self.coinflip, guild=self.guild_object)
        
    # Coin flip game
    @app_commands.command(name="coinflip", description="Bet on a coin flip with your NattyCoins")
    async def coinflip(self, interaction: discord.Interaction, bet: int):
        
        emoji_map = {
            'heads': '👤',
            'tails': '🍑'
        }
        
        user_id = interaction.user.id
        
        # Bet validation
        if not await self.economy_service.bet_validation(user_id, bet):
            return
            
        # Prompt the user to pick
        prompt_embed = discord.Embed(
            title="🎮 Natty Games: Coin Flip 🎮",
            description="Select Heads or Tails for the flip:",
            color=discord.Color.red()
        )
        
        user = interaction.user
        view = CoinFlipView(user, bet, emoji_map, self.economy_service)
        await interaction.response.send_message(embed=prompt_embed, view=view, ephemeral=True)
        
async def setup(bot, guild_object, economy_service):
    await bot.add_cog(CoinFlip(bot, guild_object, economy_service))