import discord
import traceback
from discord import app_commands, Member
from discord.ext import commands

# Class for the shop buying dropdown UX
class CardShopView(discord.ui.View):
    def __init__(self, user: discord.User, shop_service, item_service, bot, purchase_log_channel, mtg_service):
        super().__init__()
        self.user = user
        self.shop_service = shop_service
        self.item_service = item_service
        self.bot = bot
        self.purchase_log_channel = purchase_log_channel,
        self.mtg_service = mtg_service
        
    async def setup(self):
        # Get all sets
        sets = await self.mtg_service.get_all_sets()
        
        # Build dropdown
        self.clear_items()
        select = CardShopSelect(sets, self.shop_service, self.item_service, self, self.bot, self.purchase_log_channel)
        self.add_item(select)

class CardShopSelect(discord.ui.Select):
    def __init__(self, sets, shop_service, item_service, parent_view, bot, purchase_log_channel):
        self.shop_service = shop_service
        self.item_service = item_service
        self.parent_view = parent_view
        self.bot = bot
        self.purchase_log_channel = purchase_log_channel
        
        options = [
            discord.SelectOption(
                label=set['set_name'],
                description=f"Single Pack: {set['pack_price']} | Booster Box: {set['box_price']}",
                value=str(set['set_code'])
            )
            for set in sets
        ]
        super().__init__(placeholder="Choose a product to buy...", options=options, max_values=1)
        
    async def callback(self, interaction: discord.Interaction):
        try:
            set_code = self.values[0]
            user_id = interaction.user.id
            
            items = await self.item_service.get_items_by_set_code(set_code)
        
            if not items['pack'] or not items['box']:
                await interaction.response.send_message("Error: Set items not found in shop", ephemeral=True)
                return
            
            # Disable dropdown
            self.disabled = True
            self.parent_view.clear_items()
            self.parent_view.add_item(self)
            
            # Show Pack/Box buttons
            button_view = PackOrBoxView(
                items['pack'], 
                items['box'], 
                self.shop_service, 
                self.bot, 
                self.purchase_log_channel,
                interaction.user
            )
            
            await interaction.response.edit_message(
                content=f"Select pack or box for {items['pack']['name'].replace(' - Pack', '')}:",
                view=button_view
            )
            
        except Exception as e:
            print("Error in CardShopSelect callback:")
            traceback.print_exc()
            try:
                await interaction.response.send_message(
                    "An error occurred during purchase.", ephemeral=True
                )
            except discord.InteractionResponded:
                await interaction.followup.send(
                    "An error occurred during purchase.", ephemeral=True
                )

class PackOrBoxView(discord.ui.View):
    def __init__(self, pack_item, box_item, shop_service, bot, log_channel, user):
        super().__init__()
        self.pack_item = pack_item
        self.box_item = box_item
        self.shop_service = shop_service
        self.bot = bot
        self.log_channel = log_channel
        self.user = user
        
        # Create buttons with dynamic labels
        pack_button = discord.ui.Button(
            label=f"Buy Pack ({set_info['pack_price']} NattyCoins)",
            style=discord.ButtonStyle.green,
            custom_id="buy_pack"
        )
        pack_button.callback = self.buy_pack
        
        box_button = discord.ui.Button(
            label=f"Buy Box - 30 packs ({set_info['box_price']} NattyCoins)",
            style=discord.ButtonStyle.blurple,
            custom_id="buy_box"
        )
        box_button.callback = self.buy_box
        
        self.add_item(pack_button)
        self.add_item(box_button)
        
        async def buy_pack(self, interaction: discord.Interaction):
            try:
                user_id = interaction.user.id
                
                # Use shop service to process transaction
                result = await self.shop_service.process_transaction(user_id, self.pack_item['id'])
                
                # Disable buttons
                for item in self.children:
                    item.disabled = True
                await interaction.response.edit_message(view=self)
                
                if result['success']:
                    # Log purchase
                    log_embed = discord.Embed(
                        title="MTG Card Shop Purchase",
                        description=f"User: <@{user_id}>\n"
                                    f"Item: {self.pack_item['name']}\n"
                                    f"Price: {self.pack_item['price']} NattyCoins",
                        color=discord.Color.green()
                    )
                    
                    log_channel = self.bot.get_channel(self.log_channel)
                    if log_channel:
                        await log_channel.send(embed=log_embed)
                    
                    await interaction.followup.send(
                        f"✅ Purchased 1 pack of {self.pack_item['name']}!",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"❌ {result['error']}",
                        ephemeral=True
                    )
                    
            except Exception as e:
                print("Error in buy_pack:")
                traceback.print_exc()
                try:
                    await interaction.followup.send(
                        "An error occurred during purchase.", ephemeral=True
                    )
                except:
                    pass
    
    async def buy_box(self, interaction: discord.Interaction):
        try:
            user_id = interaction.user.id
            
            # Use shop service to process transaction
            result = await self.shop_service.process_transaction(user_id, self.box_item['id'])
            
            # Disable buttons
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)
            
            if result['success']:
                # Log purchase
                log_embed = discord.Embed(
                    title="MTG Card Shop Purchase",
                    description=f"User: <@{user_id}>\n"
                                f"Item: {self.box_item['name']}\n"
                                f"Price: {self.box_item['price']} NattyCoins",
                    color=discord.Color.green()
                )
                
                log_channel = self.bot.get_channel(self.log_channel)
                if log_channel:
                    await log_channel.send(embed=log_embed)
                
                await interaction.followup.send(
                    f"✅ Purchased 1 box of {self.box_item['name']} (30 packs)!",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ {result['error']}",
                    ephemeral=True
                )
                
        except Exception as e:
            print("Error in buy_box:")
            traceback.print_exc()
            try:
                await interaction.followup.send(
                    "An error occurred during purchase.", ephemeral=True
                )
            except:
                pass

class CardShop(commands.Cog):
    def __init__(self, bot, guild_object, allowed_roles, purchase_log_channel, shop_service, inventory_service, item_service, mtg_service):
        self.bot = bot
        self.guild_object = guild_object
        self.allowed_roles = allowed_roles
        self.purchase_log_channel = purchase_log_channel
        self.shop_service = shop_service
        self.inventory_service = inventory_service
        self.item_service = item_service
        self.mtg_service = mtg_service
        
        self.bot.tree.add_command(self.card_shop_open, guild=self.guild_object)
    
    @app_commands.command(name="cardshop", description="Buy MTG booster packs and boxes!")
    async def card_shop_open(self, interaction: discord.Interaction):
        try:
            # Get available sets
            sets = await self.mtg_service.get_all_sets()
            
            # Check if any sets available
            if not sets:
                await interaction.response.send_message(
                    "No MTG sets are currently available. Check back later!", 
                    ephemeral=True
                )
                return
            
            # Create view with all dependencies
            view = CardShopView(
                interaction.user, 
                self.shop_service, 
                self.item_service,
                self.bot, 
                self.purchase_log_channel,
                self.mtg_service
            )
            await view.setup()
            
            await interaction.response.send_message(
                "Select a set to purchase from:", view=view, ephemeral=True
            )
        except Exception:
            traceback.print_exc()
            await interaction.response.send_message(
                "Something went wrong.", ephemeral=True
            )

async def setup(bot, guild_object, allowed_roles, purchase_log_channel, shop_service, inventory_service, item_service, mtg_service):
    await bot.add_cog(CardShop(
        bot, 
        guild_object, 
        allowed_roles,
        purchase_log_channel,
        shop_service,
        inventory_service,
        item_service,
        mtg_service
    ))