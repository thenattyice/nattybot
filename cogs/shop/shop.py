import discord
import traceback
from discord import app_commands, Member
from discord.ext import commands

# Class for the shop buying dropdown UX
class ShopView(discord.ui.View):
    def __init__(self, user: discord.User, shop_service, bot, purchase_log_channel):
        super().__init__()
        self.user = user
        self.shop_service = shop_service
        self.bot = bot
        self.purchase_log_channel = purchase_log_channel
        
    async def shop_setup(self):
        # Get available items for this user
        items = await self.shop_service.get_available_items(self.user.id)
        
        # Build dropdown
        self.clear_items()
        select = ShopSelect(items, self.shop_service, self, self.bot, self.purchase_log_channel)
        self.add_item(select)

class ShopSelect(discord.ui.Select):
    def __init__(self, items, shop_service, parent_view, bot, purchase_log_channel):
        self.shop_service = shop_service
        self.parent_view = parent_view
        self.bot = bot
        self.purchase_log_channel = purchase_log_channel
        
        options = [
            discord.SelectOption(
                label=item['name'],
                description=f"Price: {item['price']} coins",
                value=str(item['id'])
            )
            for item in items
        ]
        super().__init__(placeholder="Choose an item to buy...", options=options, max_values=1)
        
    async def callback(self, interaction: discord.Interaction):
        try:
            item_id = int(self.values[0])
            user_id = interaction.user.id
            
            # Call shop service directly
            result = await self.shop_service.process_transaction(user_id, item_id)
            
            # Disable dropdown
            self.disabled = True
            self.parent_view.clear_items()
            self.parent_view.add_item(self)
            
            # Send response
            await interaction.response.edit_message(view=self.parent_view)
            
            if result['success']:
                # Get item details for logging
                item = await self.shop_service.item_service.get_item_by_id(item_id)
                
                log_embed = discord.Embed(
                    title=f"📦 **NattyShop Purchase**\n",
                    description=f"User: <@{user_id}>\nUser: <@{user_id}>\nPrice: {item['price']} NattyCoins",
                    color=discord.Color.green()
                )
                
                # Log to Discord channel
                log_channel = self.bot.get_channel(self.purchase_log_channel)
                if log_channel:
                    await log_channel.send(embed=log_embed)
                
                await interaction.followup.send("Purchase successful!", ephemeral=True)
            else:
                await interaction.followup.send(result['error'], ephemeral=True)
            
        except Exception as e:
            print("Error in ShopSelect callback:")
            traceback.print_exc()
            try:
                await interaction.response.send_message(
                    "An error occurred during purchase.", ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    "An error occurred during purchase.", ephemeral=True
                )

class Shop(commands.Cog):
    def __init__(self, bot, guild_object, allowed_roles, purchase_log_channel, shop_service, inventory_service, item_service):
        self.bot = bot
        self.guild_object = guild_object
        self.allowed_roles = allowed_roles
        self.purchase_log_channel = purchase_log_channel
        self.shop_service = shop_service
        self.inventory_service = inventory_service
        self.item_service = item_service
        
        self.bot.tree.add_command(self.shop_open, guild=self.guild_object)
        self.bot.tree.add_command(self.shop_add_item, guild=self.guild_object)
        self.bot.tree.add_command(self.show_inventory, guild=self.guild_object)
    
    @app_commands.command(name="shop", description="Welcome to the NattyShop!")
    async def shop_open(self, interaction: discord.Interaction):
        try:
            # Get available items first to check if shop is empty
            items = await self.shop_service.get_available_items(interaction.user.id)
            
            # Check if shop is empty
            if not items:
                await interaction.response.send_message(
                    "The shop is currently empty. Check back later!", 
                    ephemeral=True
                )
                return
            
            # Create view with shop_service, bot, and log channel
            view = ShopView(interaction.user, self.shop_service, self.bot, self.purchase_log_channel)
            await view.shop_setup()
            
            await interaction.response.send_message(
                "Select an item to purchase:", view=view, ephemeral=True
            )
        except Exception:
            traceback.print_exc()
            await interaction.response.send_message(
                "Something went wrong.", ephemeral=True
            )
        
    @app_commands.command(name="additem", description="Add an item to the shop")
    @app_commands.choices(item_type=[
        app_commands.Choice(name="Consumable", value="consumable"),
        app_commands.Choice(name="Bundle", value="bundle"),
        app_commands.Choice(name="Business", value="business")
    ])
    async def shop_add_item(self,
                            interaction: discord.Interaction,
                            name: str,
                            description: str,
                            price: int,
                            item_type: str,
                            is_active: bool = True,
                            metadata: str = "{}"):  # JSON string
        # Check permissions
        user_role_ids = [role.id for role in interaction.user.roles]
        if not any(role_id in self.allowed_roles for role_id in user_role_ids):
            await interaction.response.send_message(
                "You don't have permission.", ephemeral=True
            )
            return
        
        try:
            import json
            metadata_dict = json.loads(metadata)
            
            await self.item_service.add_shop_item(
                name, description, price, item_type, is_active, metadata_dict
            )
            
            await interaction.response.send_message(
                f"Added {name} to the shop!", ephemeral=True
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.response.send_message(
                "An error occurred while adding the item.", ephemeral=True
            )
            
    @app_commands.command(name="inventory", description="View your inventory")
    async def show_inventory(self, interaction: discord.Interaction):
        try:
            user_id = interaction.user.id
            inventory_list = await self.inventory_service.get_user_inventory(user_id)
            
            if not inventory_list:
                await interaction.response.send_message(
                    "Your inventory is empty.", ephemeral=True
                )
                return
            
            description = '\n'.join(
                f"{row['name']}: {row['quantity']}" for row in inventory_list
            )
            
            embed = discord.Embed(
                title="Your Inventory",
                description=description,
                color=discord.Color.blue()
            )
            
            await interaction.response.send_message(embed=embed)
        except Exception:
            traceback.print_exc()

async def setup(bot, guild_object, allowed_roles, purchase_log_channel, shop_service, inventory_service, item_service):
    await bot.add_cog(Shop(
        bot, 
        guild_object, 
        allowed_roles,
        purchase_log_channel,
        shop_service,
        inventory_service,
        item_service
    ))