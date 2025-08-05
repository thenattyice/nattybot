import discord
import random
import asyncio
import traceback
from discord import app_commands, Member
from discord.ext import commands

# Bet validation method
async def bet_validation(self, interaction, target_user_id: int, bet: int):
    economy_cog = self.bot.get_cog('Economy')
    
    current_balance = await economy_cog.get_balance(target_user_id)
    
    # Bet amount validations
    if bet > current_balance:
        await interaction.response.send_message("You cannot place a bet that is larger than your current balance.", ephemeral=True)
        print("Validation Failure: bet > current_balance")
        return
        
    if bet <= 0:
        await interaction.response.send_message("You must bet at least 1 NattyCoin.", ephemeral=True)
        print("Validation Failure: bet <= 0")
        return
    
    if current_balance <= 0:
        await interaction.response.send_message("You cannot place a bet when you have 0 NattyCoins. Do the Wordle, or do it better... moron.", ephemeral=True)
        print("Validation Failure: current_balance <= 0")
        return
    
    return True