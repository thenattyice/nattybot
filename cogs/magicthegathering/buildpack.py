import aiohttp
import random
import asyncio
import traceback
import discord
from discord import app_commands, Member
from discord.ext import commands

# Class for the shop buying dropdown UX
class OpenPackView(discord.ui.View):
    def __init__(self, user: discord.User, parent_cog):
        super().__init__()
        self.user = user
        self.parent_cog = parent_cog
        
    async def open_pack_setup(self):
        # Get all the shop items
        sets = await self.parent_cog.get_all_sets()
        
        # Builds the dropdown
        self.clear_items()
        select = PackSelect(sets, self.parent_cog, self)
        self.add_item(select)
        
class PackSelect(discord.ui.Select):
    def __init__(self, sets, parent_cog, parent_view):
        self.parent_cog = parent_cog
        self.parent_view = parent_view
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
            set_row = await self.parent_cog.get_set_by_code(set_code)
            
            await self.parent_cog.remove_pack_from_user_inventory(user_id)
            
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
    def __init__(self, bot, guild_object, allowed_roles, pack_opening_channel):
        self.bot = bot
        self.guild_object = guild_object
        self.allowed_roles = allowed_roles
        self.pack_opening_channel = pack_opening_channel
        
        # Register commands here
        self.bot.tree.add_command(self.add_set, guild=self.guild_object)
        self.bot.tree.add_command(self.rip_a_pack, guild=self.guild_object)
    
    async def get_cards_from_set(self, set_code: str):
        url= f"https://api.scryfall.com/cards/search?q=set:{set_code}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return data["data"]
    
    async def open_pack(self, interaction: discord.Interaction, set_code: str, target_user_id: int):
        economy_cog = self.bot.get_cog('Economy') # Connect to the Economy Cog to use economy functions: get_balance and add_money_to_user
        cards = await self.get_cards_from_set(set_code)
        
        commons = [card for card in cards if card["rarity"] == "common"]
        uncommons = [card for card in cards if card["rarity"] == "uncommon"]
        mythics_rares = [card for card in cards if card["rarity"] in ["rare","mythic"]]
        
        pack= []
        
        pack.extend(random.sample(commons, 9))
        pack.extend(random.sample(uncommons, 3))
        pack.extend(random.sample(mythics_rares, 2))
        
        description=""
        
        embed = discord.Embed(
            title="MTG Booster Pack",
            description=description,
            color=discord.Color.blue()
        )
        
        total = 0
        
        for card in pack:
            price, foil = self.get_card_price(card)
            foil_tag = " (Foil)✨" if foil else ""
            description += f"{card['name']}{foil_tag} - ${price}\n"
            total += price
            
        description += f"***GRAND TOTAL: {total}***\n\nPacked opened by: <@{target_user_id}>"
        
        embed.description = description
        
        await economy_cog.add_money_to_user(target_user_id, total)
        new_balance = await economy_cog.get_balance(target_user_id)
        
        money_embed = discord.Embed(
            title="",
            description=f"You have been paid **{total}** NattyCoins for your pack opening!\n\nNew balance: **{new_balance}** NattyCoins",
            color=discord.Color.gold()
        )
        
        await interaction.followup.send(embed=embed)
        await interaction.followup.send(embed=money_embed, ephemeral=True)

    def get_card_price(self, card):
        is_foil = random.random() < (1/6) # 1 in 6 chance for a foil card
        
        def parse_price(price_str):
            float_price = float(price_str)
            if float_price < 0.50:
                return 1
            elif float_price >= 0.50 and float_price < 1.0:
                return 1
            else:
                return float_price

        usd = parse_price(card["prices"]["usd"]) if card["prices"]["usd"] else 1.0
        usd_foil = parse_price(card["prices"]["usd_foil"]) if card["prices"]["usd_foil"] else 1.0

        if is_foil and usd_foil > 0:
            return round(usd_foil), True
        else:
            return round(usd), False
        
    async def add_set_to_db(self, interaction: discord.Interaction, set_code: str):
        try:
            url = f"https://api.scryfall.com/sets/{set_code}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    set_data = await response.json()
            
            set_name = set_data["name"]

            async with self.bot.db_pool.acquire() as conn:
                status = await conn.execute("""
                    INSERT INTO mtg_sets (set_code, set_name)
                    VALUES ($1, $2)
                    ON CONFLICT (set_code) DO NOTHING;
                """, set_code, set_name)
                
            if status.endswith("1"):
                await interaction.followup.send(f"{set_name} set successfully added!")
            else:
                await interaction.followup.send(f"{set_name} already exists.")
        except:
            traceback.print_exc()
            
    async def get_all_sets(self):
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, set_name, set_code FROM mtg_sets;")
        return rows
    
    async def get_set_by_code(self, set_code):
        async with self.bot.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT set_name FROM mtg_sets WHERE set_code = $1;", set_code)
        return row
    
    async def owns_packs_validation(self, target_user_id: int):
        async with self.bot.db_pool.acquire() as conn:
            owns_packs = await conn.fetchrow("""
                                            SELECT s.name
                                            FROM inventory i
                                            JOIN shop s ON s.id = i.item_id
                                            WHERE i.user_id = $1
                                            AND s.name = 'MTG Booster Pack'
                                            AND i.quantity > 0;
                                             """, target_user_id)
        return owns_packs is not None
        
    async def remove_pack_from_user_inventory(self, target_user_id: int):
        async with self.bot.db_pool.acquire() as conn:
                await conn.execute("""
                                    WITH get_pack_id AS (
                                        SELECT id FROM shop
                                        WHERE name = 'MTG Booster Pack'
                                    )
                                    UPDATE inventory
                                    SET quantity = inventory.quantity - 1
                                    FROM get_pack_id gpi
                                    WHERE user_id = $1
                                    AND item_id = gpi.id
                                    """, target_user_id)

    # Command for adding an item to the shop
    @app_commands.command(name="addmtgset", description="Add an MTG set for pack openings")
    async def add_set(self, interaction: discord.Interaction,set_code: str):
        user_role_ids = [role.id for role in interaction.user.roles]
        if not any(role_id in self.allowed_roles for role_id in user_role_ids):
            await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
            return

        try:
            await interaction.response.defer(thinking=True, ephemeral=True)
            await self.add_set_to_db(interaction, set_code)
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
            
            users_packs = await self.owns_packs_validation(user_id)
            
            if not users_packs:
                    await interaction.response.send_message("You have no packs to open.", ephemeral=True)
                    return
            
            view = OpenPackView(interaction.user, self)
            await view.open_pack_setup()
            await interaction.response.send_message("Select an item to purchase:", view=view, ephemeral=True)
        except Exception:
            traceback.print_exc()

async def setup(bot, guild_object, allowed_roles, pack_opening_channel):
    await bot.add_cog(BuildBoosterPack(bot, guild_object, allowed_roles, pack_opening_channel))