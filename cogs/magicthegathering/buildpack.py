import aiohttp
import random
import asyncio
import traceback
import discord
from discord import app_commands, Member
from discord.ext import commands

# Class for the shop buying dropdown UX
class OpenPackView(discord.ui.View):
    def __init__(self, user: discord.User, parent_cog, mtg_service):
        super().__init__()
        self.user = user
        self.parent_cog = parent_cog
        self.mtg_service = mtg_service
        
    async def open_pack_setup(self):
        # Get all the shop items
        sets = await self.mtg_service.get_all_sets()
        
        # Builds the dropdown
        self.clear_items()
        select = PackSelect(sets, self.parent_cog, self, self.mtg_service)
        self.add_item(select)
        
class PackSelect(discord.ui.Select):
    def __init__(self, sets, parent_cog, parent_view, mtg_service):
        self.parent_cog = parent_cog
        self.parent_view = parent_view
        self.mtg_service = mtg_service
        options = [
            discord.SelectOption(
                label=set['set_name'],
                description=f"Booster pack for {set['set_name']}",
                value=set['set_code']
            )
            for set in sets
        ]
        super().__init__(placeholder="Choose a set to open...", options=options, max_values=1)
        
    async def callback(self, interaction: discord.Interaction):
        try:
            user_id = interaction.user.id
            
            set_code = self.values[0]
            set_row = await self.mtg_service.get_set_by_code(set_code)
            
            await self.mtg_service.remove_pack_from_user(user_id)
            
            # Disable the dropdown after selection
            self.disabled = True
            self.parent_view.clear_items() # Remove all existing items
            self.parent_view.add_item(self) # Add back the now-disabled version
            
            # Feedback message to replace the dropdown
            content = (f"You are opening a **{set_row['set_name']}** pack!")
            
            await interaction.response.edit_message(view=self.parent_view)
            await interaction.followup.send(content=content, ephemeral=True)
            
            await self.parent_cog.open_pack(interaction, set_code, user_id)
            
        except Exception as e:
            print("Error in PackSelect callback:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("An error occurred during pack selection.", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send("An error occurred during pack selection.", ephemeral=True)

class BuildBoosterPack(commands.Cog):
    def __init__(self, bot, guild_object, allowed_roles, pack_opening_channel, economy_service, mtg_service):
        self.bot = bot
        self.guild_object = guild_object
        self.allowed_roles = allowed_roles
        self.pack_opening_channel = pack_opening_channel
        self.economy_service = economy_service
        self.mtg_service = mtg_service
        
        # Register commands here
        self.bot.tree.add_command(self.add_set, guild=self.guild_object)
        self.bot.tree.add_command(self.rip_a_pack, guild=self.guild_object)
    
    async def open_pack(self, interaction: discord.Interaction, set_code: str, target_user_id: int):
        # Get pack data from service layer
        pack_cards, total_value = await self.mtg_service.open_pack(set_code)
        
        # Build description from card data
        description = ""
        for card in pack_cards:
            foil_tag = " (Foil)✨" if card["foil"] else ""
            description += f"{card['name']}{foil_tag} - ${card['price']}\n"
        
        description += f"***GRAND TOTAL: {total_value}***\n\nPack opened by: <@{target_user_id}>"
        
        # Create pack embed
        embed = discord.Embed(
            title="MTG Booster Pack",
            description=description,
            color=discord.Color.blue()
        )
        
        # Update user balance
        await self.economy_service.add_money_to_user(target_user_id, total_value)
        new_balance = await self.economy_service.get_balance(target_user_id)
        
        # Create money embed
        money_embed = discord.Embed(
            title="",
            description=f"You have been paid **{total_value}** NattyCoins for your pack opening!\n\nNew balance: **{new_balance}** NattyCoins",
            color=discord.Color.gold()
        )
        
        # Send responses
        await interaction.followup.send(embed=embed)
        await interaction.followup.send(embed=money_embed, ephemeral=True)

    # Command for adding an item to the shop
    @app_commands.command(name="addmtgset", description="Add an MTG set for pack openings")
    async def add_set(self, interaction: discord.Interaction,set_code: str):
        user_role_ids = [role.id for role in interaction.user.roles]
        if not any(role_id in self.allowed_roles for role_id in user_role_ids):
            await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
            return

        try:
            await interaction.response.defer(thinking=True, ephemeral=True)
            await self.mtg_service.add_set_to_db(set_code)
        except Exception as e:
            traceback.print_exc()
            await interaction.response.send_message("An error occurred while adding the item.", ephemeral=True)
            
    # Command for opening a pack
    @app_commands.command(name="openpack", description="Earn NattyCoins based on opening a pack!")
    async def rip_a_pack(self, interaction: discord.Interaction):
        try:
            if interaction.channel.id != self.pack_opening_channel:
                await interaction.response.send_message(
                    "You can only use this command in the #pack-openings channel.", ephemeral=True)
                return
            
            user_id = interaction.user.id
            
            users_packs = await self.mtg_service.owns_packs_validation(user_id)
            
            if not users_packs:
                    await interaction.response.send_message("You have no packs to open.", ephemeral=True)
                    return
            
            view = OpenPackView(interaction.user, self, self.mtg_service)
            await view.open_pack_setup()
            await interaction.response.send_message("Select an item to purchase:", view=view, ephemeral=True)
        except Exception:
            traceback.print_exc()

async def setup(bot, guild_object, allowed_roles, pack_opening_channel, economy_service, mtg_service):
    await bot.add_cog(BuildBoosterPack(bot, guild_object, allowed_roles, pack_opening_channel, economy_service, mtg_service))