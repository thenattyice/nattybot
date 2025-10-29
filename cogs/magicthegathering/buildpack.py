import aiohttp
import random
import asyncio
import traceback
import discord
from discord import app_commands, Member
from discord.ext import commands
from typing import Optional

# Class for the pack opening dropdown UX
class OpenPackView(discord.ui.View):
    def __init__(self, user: discord.User, parent_cog, mtg_service, inventory_service, pack_count: int = 1):
        super().__init__()
        self.user = user
        self.parent_cog = parent_cog
        self.mtg_service = mtg_service
        self.inventory_service = inventory_service
        self.pack_count = pack_count
        
    async def open_pack_setup(self):
        # Get the user's owned pack sets
        sets = await self.mtg_service.get_user_mtg_packs(self.user.id)
        
        # Builds the dropdown
        self.clear_items()
        select = PackSelect(sets, self.parent_cog, self, self.mtg_service, self.inventory_service)
        self.add_item(select)
        
class PackSelect(discord.ui.Select):
    def __init__(self, sets, parent_cog, parent_view, mtg_service, inventory_service):
        self.parent_cog = parent_cog
        self.parent_view = parent_view
        self.mtg_service = mtg_service
        self.inventory_service = inventory_service
        
        options = [
            discord.SelectOption(
                label=set['set_name'],
                description=f"You own {set['total_quantity']} pack{'s' if set['total_quantity'] != 1 else ''}",
                value=set['set_code']
            )
            for set in sets
        ]
        super().__init__(placeholder="Choose a set to open...", options=options, max_values=1)
        
    async def callback(self, interaction: discord.Interaction):
        try:
            user_id = interaction.user.id
            set_code = self.values[0]
            pack_count = self.parent_view.pack_count
            
            # Get set info
            set_info = await self.mtg_service.get_set_by_code(set_code)
            
            # Get the item_id for this set from user's inventory
            item_id = await self.inventory_service.get_item_id_by_set_code(user_id, set_code)
            
            if not item_id:
                await interaction.response.send_message(
                    "Error: Could not find packs in inventory.", 
                    ephemeral=True
                )
                return
            
            # Check if user has enough packs
            current_quantity = await self.inventory_service.get_item_quantity(user_id, item_id)
            if current_quantity < pack_count:
                await interaction.response.send_message(
                    f"You only have {current_quantity} pack{'s' if current_quantity != 1 else ''}, but tried to open {pack_count}!",
                    ephemeral=True
                )
                return
            
            # Remove the appropriate number of packs
            await self.inventory_service.remove_item_from_inventory(user_id, item_id, pack_count)
            
            # Disable the dropdown after selection
            self.disabled = True
            self.parent_view.clear_items()
            self.parent_view.add_item(self)
            
            # Feedback message
            pack_text = "pack" if pack_count == 1 else f"{pack_count} packs"
            content = f"You are opening {pack_text} from **{set_info['set_name']}**!"
            
            await interaction.response.edit_message(view=self.parent_view)
            await interaction.followup.send(content=content, ephemeral=True)
            
            # Call the appropriate method based on pack count
            if pack_count == 1:
                await self.parent_cog.open_pack(interaction, set_code, user_id)
            else:
                await self.parent_cog.open_multiple_packs(interaction, set_code, user_id, pack_count)
            
        except Exception as e:
            print("Error in PackSelect callback:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("An error occurred during pack selection.", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send("An error occurred during pack selection.", ephemeral=True)

class BuildBoosterPack(commands.Cog):
    def __init__(self, bot, guild_object, allowed_roles, pack_opening_channel, economy_service, mtg_service, inventory_service):
        self.bot = bot
        self.guild_object = guild_object
        self.allowed_roles = allowed_roles
        self.pack_opening_channel = pack_opening_channel
        self.economy_service = economy_service
        self.mtg_service = mtg_service
        self.inventory_service = inventory_service
        
        # Register commands here
        self.bot.tree.add_command(self.add_set, guild=self.guild_object)
        self.bot.tree.add_command(self.rip_a_pack, guild=self.guild_object)
        self.bot.tree.add_command(self.rip_packs, guild=self.guild_object)
        self.bot.tree.add_command(self.update_set_pricing, guild=self.guild_object)
    
    async def open_pack(self, interaction: discord.Interaction, set_code: str, target_user_id: int):
        # Get pack data from service layer
        pack_cards, total_value = await self.mtg_service.open_pack(set_code)
        
        # Build description from card data
        description = ""
        for card in pack_cards:
            foil_tag = " (Foil)✨" if card["foil"] else ""
            description += f"{card['name']}{foil_tag} - ${card['price']}\n"
        
        description += f"***GRAND TOTAL: ${total_value}***\n\nPack opened by: <@{target_user_id}>"
        
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
            description=f"You have been paid **${total_value}** NattyCoins for your pack opening!\n\nNew balance: **${new_balance}** NattyCoins",
            color=discord.Color.gold()
        )
        
        # Send responses
        await interaction.followup.send(embed=embed)
        await interaction.followup.send(embed=money_embed, ephemeral=True)
        
    async def open_multiple_packs(self, interaction: discord.Interaction, set_code: str, target_user_id: int, pack_count: int):
        total_earnings = 0
        all_pack_results = []
        
        # Open each pack and collect results
        for i in range(pack_count):
            pack_cards, pack_value = await self.mtg_service.open_pack(set_code)
            total_earnings += pack_value
            all_pack_results.append((pack_cards, pack_value))
        
        # Build descriptions, splitting into multiple embeds if needed
        embeds = []
        current_description = f"Opening {pack_count} packs!\n\n"
        packs_in_current_embed = 0
        CHAR_LIMIT = 3500  # Leave room for footer
        
        for i, (pack_cards, pack_value) in enumerate(all_pack_results, 1):
            pack_text = f"**Pack {i}** (${pack_value}):\n"
            for card in pack_cards:
                foil_tag = " ✨" if card["foil"] else ""
                pack_text += f"  • {card['name']}{foil_tag} - ${card['price']}\n"
            pack_text += "\n"
            
            # Check if adding this pack would exceed the limit
            if len(current_description + pack_text) > CHAR_LIMIT:
                # Save current embed and start a new one
                embeds.append(current_description)
                current_description = pack_text
                packs_in_current_embed = 1
            else:
                current_description += pack_text
                packs_in_current_embed += 1
        
        # Add the final embed
        if current_description:
            embeds.append(current_description)
        
        # Add grand total to the last embed
        embeds[-1] += f"***GRAND TOTAL: ${total_earnings}***\n\nPacks opened by: <@{target_user_id}>"
        
        # Send all embeds
        for idx, desc in enumerate(embeds):
            embed = discord.Embed(
                title=f"MTG Booster Packs x{pack_count}" + (f" (Part {idx+1}/{len(embeds)})" if len(embeds) > 1 else ""),
                description=desc,
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed)
        
        # Update user balance
        await self.economy_service.add_money_to_user(target_user_id, total_earnings)
        new_balance = await self.economy_service.get_balance(target_user_id)
        
        # Create money embed
        money_embed = discord.Embed(
            title="",
            description=f"You have been paid **${total_earnings}** NattyCoins for opening {pack_count} packs!\n\nNew balance: **${new_balance}** NattyCoins",
            color=discord.Color.gold()
        )
        
        # Send final summary
        await interaction.followup.send(embed=money_embed, ephemeral=True)

    # Command for adding a set to the shop
    @app_commands.command(name="addmtgset", description="Add an MTG set for pack openings")
    async def add_set(self, interaction: discord.Interaction, set_code: str, pack_price: int, box_price: int):
        user_role_ids = [role.id for role in interaction.user.roles]
        if not any(role_id in self.allowed_roles for role_id in user_role_ids):
            await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
            return

        try:
            await interaction.response.defer(thinking=True, ephemeral=True)
            result = await self.mtg_service.add_set_to_db(set_code, pack_price, box_price)

            if result['success']:
                await interaction.followup.send(result['message'], ephemeral=True)
            else:
                await interaction.followup.send(result['error'], ephemeral=True)
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send("An error occurred while adding the set.", ephemeral=True)
            
    # Command for opening a pack
    @app_commands.command(name="openpack", description="Earn NattyCoins based on opening a pack!")
    async def rip_a_pack(self, interaction: discord.Interaction):
        try:
            if interaction.channel.id != self.pack_opening_channel:
                await interaction.response.send_message(
                    "You can only use this command in the #pack-openings channel.", ephemeral=True)
                return
            
            user_id = interaction.user.id
            
            # Get user's MTG packs
            user_packs = await self.mtg_service.get_user_mtg_packs(user_id)
            
            if not user_packs:
                await interaction.response.send_message(
                    "You don't own any MTG packs! Buy some from `/cardshop` first.", 
                    ephemeral=True
                )
                return
            
            view = OpenPackView(interaction.user, self, self.mtg_service, self.inventory_service, pack_count=1)
            await view.open_pack_setup()
            await interaction.response.send_message("Select a set to open:", view=view, ephemeral=True)
        except Exception:
            traceback.print_exc()
            await interaction.response.send_message("An error occurred.", ephemeral=True)
            
    # Command for opening multiple packs
    @app_commands.command(name="openpacks", description="Earn NattyCoins based on opening multiple packs all at once!")
    async def rip_packs(self, interaction: discord.Interaction, requested_open_count: int):
        try:
            if interaction.channel.id != self.pack_opening_channel:
                await interaction.response.send_message(
                    "You can only use this command in the #pack-openings channel.", ephemeral=True)
                return
            
            if requested_open_count < 1:
                await interaction.response.send_message(
                    "Please enter a valid number of packs to open (at least 1).", 
                    ephemeral=True
                )
                return
            
            user_id = interaction.user.id
            
            # Get user's MTG packs
            user_packs = await self.mtg_service.get_user_mtg_packs(user_id)
            
            if not user_packs:
                await interaction.response.send_message(
                    "You don't own any MTG packs! Buy some from `/cardshop` first.", 
                    ephemeral=True
                )
                return
            
            view = OpenPackView(interaction.user, self, self.mtg_service, self.inventory_service, pack_count=requested_open_count)
            await view.open_pack_setup()
            await interaction.response.send_message(
                f"Select a set to open {requested_open_count} packs from:", 
                view=view, 
                ephemeral=True
            )
        except Exception:
            traceback.print_exc()
            await interaction.response.send_message("An error occurred.", ephemeral=True)
            
    # Command for updating set prices
    @app_commands.command(name="updatesetprice", description="Update pack/box prices for an MTG set")
    async def update_set_pricing(self, interaction: discord.Interaction, set_code: str, new_pack_price: Optional[int] = None, new_box_price: Optional[int] = None):
        user_role_ids = [role.id for role in interaction.user.roles]
        if not any(role_id in self.allowed_roles for role_id in user_role_ids):
            await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
            return
        
        # Validate that at least on of the price args is populated
        if not pack_price and not box_price:
            await interaction.response.send_message("At least one price must be populated", ephemeral=True)
            return
        
        # Update the values in mtg_sets via the code specified
        try:
            if new_pack_price:
                await self.mtg_service.update_set_pack_price(set_code, new_pack_price)
                
            if new_box_price:
                await self.mtg_service.update_set_box_price(set_code, new_box_price)
            
            await interaction.response.send_message("Set prices updated!", ephemeral=True)
        except Exception:
            traceback.print_exc()
            await interaction.response.send_message("An error occurred.", ephemeral=True)
        
async def setup(bot, guild_object, allowed_roles, pack_opening_channel, economy_service, mtg_service, inventory_service):
    await bot.add_cog(BuildBoosterPack(bot, guild_object, allowed_roles, pack_opening_channel, economy_service, mtg_service, inventory_service))