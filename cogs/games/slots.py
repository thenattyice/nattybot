import discord
import random
import asyncio
import traceback
from discord import app_commands, Member
from discord.ext import commands

class SlotMachine(commands.Cog):
    def __init__(self, bot, guild_object, economy_service, game_service, slots_service):
        self.bot = bot
        self.guild_object = guild_object
        self.economy_service = economy_service
        self.game_service = game_service
        self.slots_service = slots_service
        
        # Commands registered here
        self.bot.tree.add_command(self.slots, guild=self.guild_object)
        # Also need a command with slot info on each multipler and weight for the wheel emojis
        
    # SlotMachine game
    @app_commands.command(name="slots", description="Pull the lever on the Slot Machine!")
    async def slots(self, interaction: discord.Interaction, bet: int):
        user_id = interaction.user.id
        
        # Run the bet validation
        if not await self.economy_service.bet_validation(user_id, bet):
            await interaction.response.send_message("Please bet a valid amount", ephemeral=True)
            return
        
        # Deduct the bet
        await self.economy_service.remove_money_from_user(user_id, bet)
        
        spin_result = await self.slots_service.determine_slot_results()
        wheel1, wheel2, wheel3 = spin_result
        
        # Show the results
        embed = discord.Embed(
            title="🎮 Natty Games: Slots 🎮",
            description=f"| {wheel1} | {wheel2} | {wheel3} |",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        result = await self.slots_service.slots_result_handler(spin_result, bet, user_id)
        
        await interaction.followup.send(embed=result, ephemeral=True)
        
    # Command to show the details about each wheel item
    @app_commands.command(name="slotinfo", description="See the Slot machine details")
    async def slotinfo(self, interaction: discord.Interaction):
        symbols = self.slots_service.symbols
        
        description = ''
        
        for symbol in symbols:
            emoji = [data['emoji'] for data in symbols.values()]
            weight = [data['weight'] for data in symbols.values()]
            multiplier = [data['payout'] for data in symbols.values()]
            
            description += f"{emoji} | Weight: {weight} | Multiplier: {multiplier}\n"
            
        embed = disc.Embed(
            title="🎮 Natty Games: Slots 🎮",
            description=description,
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
            
async def setup(bot, guild_object, economy_service, game_service, slots_service):
    await bot.add_cog(SlotMachine(bot, guild_object, economy_service, game_service, slots_service))