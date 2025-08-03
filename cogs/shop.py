import discord
import traceback
from discord import app_commands, Member
from discord.ext import commands

# Class for the shop buying dropdown UX
class ShopView(discord.ui.View):
    def __init__(self, user: discord.User, parent_cog):
        super().__init__()
        self.parent_cog = parent_cog
        
    async def shop_setup(self):
        items = await self.parent_cog.get_all_shop_items()
        self.clear_items()
        select = ShopSelect(items, self.parent_cog, self)
        self.add_item(select)
        
class ShopSelect(discord.ui.Select):
    def __init__(self, items, parent_cog, parent_view):
        self.parent_cog = parent_cog
        self.view = parent_view
        options = [
            discord.SelectOption(
                label=item['name'],
                description=f"Price: {item['price']} coins",
                value=str(item['id'])  # value must be a string
            )
            for item in items
        ]
        super().__init__(placeholder="Choose an item to buy...", options=options, max_values=1)
    
    async def callback(self, interaction: discord.Interaction):
        try:
            item_id = int(self.values[0])
            user_id = interaction.user.id
            
            # Call the process_transaction method to hndle the purchase from the select
            item_row = await self.parent_cog.get_shop_item_by_id(item_id)
            
            price = item_row['price']
            success = await self.parent_cog.process_transaction(interaction, user_id, item_id, price)
            if success:
                await interaction.response.send_message(f"You bought **{item_row['name']}** for {price}")
            else:
                pass
        except Exception as e:
            print("Error in ShopSelect callback:")
            traceback.print_exc()
            try:
                await interaction.response.send_message("An error occurred during purchase.", ephemeral=True)
            except discord.InteractionResponded:
                await interaction.followup.send("An error occurred during purchase.", ephemeral=True)
# Class for all of the Shop commands
class Shop(commands.Cog):
    def __init__(self, bot, guild_object, allowed_roles, purchase_log_channel):
        self.bot = bot
        self.guild_object = guild_object
        self.allowed_roles = allowed_roles
        self.purchase_log_channel = purchase_log_channel
        
        # Register commands to my specific guild/server
        self.bot.tree.add_command(self.shop_open, guild=self.guild_object)
        self.bot.tree.add_command(self.shop_add_item, guild=self.guild_object)
    
    # Add an item to the shop table for purchase in the shop
    async def add_item_to_shop(self, interaction: discord.Interaction, item_name: str, description: str, price: int):
        async with self.bot.db_pool.acquire() as conn:
            status = await conn.execute("""
                INSERT INTO shop (name, description, price)
                VALUES ($1, $2, $3)
                ON CONFLICT (name) DO NOTHING
            """, item_name, description, price)
            if status.endswith("1"):
                await interaction.response.send_message(f"{item_name} successfully added to the shop!")
            else:
                await interaction.response.send_message(f"{item_name} already exists in the shop.")
        
    # Directly add an item to a user's inventory
    async def add_item_to_user(self, target_user_id: int, item_id: int):
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO inventory (user_id, item_id, quantity)
                VALUES ($1, $2, 1)
                ON CONFLICT (user_id, item_id)
                DO UPDATE SET quantity = inventory.quantity + 1;
            """, target_user_id, item_id)
    
    # Get an item name by the given ID
    async def get_item_name_by_id(self, item_id: int) -> str | None:
        async with self.bot.db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT name FROM shop WHERE id = $1;
            """, item_id)

        return result["name"] if result else None
    
    # Get all items for use in the shop dropdown
    async def get_all_shop_items(self):
        async with self.bot.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, name, price FROM shop;")
        return rows
    
    # Get all details in a row for a specific item
    async def get_shop_item_by_id(self, item_id: int) -> dict | None:
        async with self.bot.db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT * FROM shop WHERE id = $1;
            """, item_id)
        return dict(result) if result else None
        
    # Function to log all of the purchases to DB and text channel
    async def log_item_purchase(self, target_user_id: int, item_id: int):
        async with self.bot.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO purchases (user_id, item_id, quantity)
                VALUES ($1, $2, $3);
            """, target_user_id, item_id, 1)
            
        item_name = await self.get_item_name_by_id(item_id) # Get the item ID
        
        purchase_embed = discord.Embed(
            title="NattyShop Purchase",
            description=f"<@{target_user_id}> purchased {item_name}!",
            color=discord.Color.green()
        )
        
        log_channel = self.guild_object.get_channel(self.purchase_log_channel)
        await log_channel.send(embed=purchase_embed)
    
    async def process_transaction(self, interaction, target_user_id: int, item_id: int, price: int) -> bool:
        economy_cog = self.bot.get_cog("Economy")
        balance = await economy_cog.get_balance(target_user_id)
        
        # Balance check
        if balance < price:
            await interaction.response.send_message("You do not have enough NattyCoins to purchase this item.", ephemeral=True)
            return False
        else:
            await economy_cog.remove_money_from_user(target_user_id, price)
            await self.add_item_to_user(target_user_id, item_id)
            await self.log_item_purchase(target_user_id, item_id)
            return True
            
    # Command for presenting the shop
    @app_commands.command(name="buy", description="Welcome to the NattyShop! Spend your NattyCoins wisely.")
    async def shop_open(self, interaction: discord.Interaction):
        items = await self.get_all_shop_items()

        if not items:
            await interaction.response.send_message("The shop is currently empty.", ephemeral=True)
            return
        
        view = ShopView(interaction.user, self)
        await view.shop_setup()
        await interaction.response.send_message("Select an item to purchase:", view=view, ephemeral=True)
        
    # Command for dding an item to the shop
    @app_commands.command(name="additem", description="Add an item to the NattyShop")
    async def shop_add_item(self, interaction: discord.Interaction, item_name: str, description: str, price: int):
        user_role_ids = [role.id for role in interaction.user.roles]
        if not any(role_id in self.allowed_roles for role_id in user_role_ids):
            await interaction.response.send_message("You do not have permission to run this command.", ephemeral=True)
            return
        try:
            await self.add_item_to_shop(interaction, item_name, description, price)
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send("An error occurred while adding the item.", ephemeral=True)