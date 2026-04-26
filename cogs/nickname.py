import discord
import traceback
from discord import app_commands
from discord.ext import commands
from discord.ui import Modal, TextInput
from better_profanity import profanity

# Nickname entry modal class
class NicknameModal(Modal, title='Enter desired nickname:'):
    def __init__(self, user_id, target_user, token_id, inventory_service):
        super().__init__()
        self.user_id = user_id
        self.target_user = target_user
        self.token_id = token_id
        self.inventory_service = inventory_service
    
    # Modal TextInput field    
    nickname = TextInput(
        label="New Nickname:",
        placeholder="Enter new nickname here",
        required=True,
        max_length=32,
        min_length=1
    )
    
    # Method fires on submission of modal
    async def on_submit(self, interaction: discord.Interaction):
        
        new_nickname = self.nickname.value.strip() # Remove outside whitespace
        
        # Method to check for profanity
        if profanity.contains_profanity(new_nickname):
            await interaction.response.send_message("The nickname cannot contain profanity!", ephemeral=True)
            return
        
        try:
            await self.target_user.edit(nick=new_nickname) # Change the user's guild nickname
            await self.inventory_service.remove_item_from_inventory(self.user_id, self.token_id, 1) # Remove a nickname token from player inventory
            await interaction.response.send_message(f"Changed {self.target_user}'s nickname to {new_nickname}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("No permission to change this user's nickname", ephemeral=True)
        except Exception as e:
            traceback.print_exc()
            print(f"[NICKNAME] Error: {e} ")

# Main Cog class
class NicknameChange(commands.Cog):
    def __init__(self, bot, guild_object, inventory_service, nickname_service):
            self.bot = bot
            self.guild_object = guild_object
            self.inventory_service = inventory_service
            self.nickname_service = nickname_service
            self.token_id = None
            
            # Registered commands
            self.bot.tree.add_command(self.nickname_command, guild=self.guild_object)
    
    # Cache the token ID on bot startup
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            guild = self.bot.get_guild(self.guild_object.id)
            # Make sure guild is ready before starting the cache load
            if guild:
                await self.cache_nickname_token_id()
            else:
                print("⚠️ Guild not found yet when on_ready fired")
        except Exception as e:
            traceback.print_exc()
            print(f"Nickname Cache Error: {e}")
    
    # Cache the token item ID to reduce DB calls
    async def cache_nickname_token_id(self):
        token_id = await self.nickname_service.get_nickname_token_id()
        
        if token_id is not None:
            self.token_id = token_id
            print(f"Nickname Token ID: {token_id}")
        else:
            print('No Nickname Token found in shop, please add the item to the shop')
            
    # Command for /nickname - User picked as args for the new nickname
    @app_commands.command(name="set_nickname", description="Change a user's nickname")
    async def nickname_command(self, interaction: discord.Interaction, member: discord.Member):
        try:
            user_id = interaction.user.id
            
            target_user = member 
            
            has_token = await self.nickname_service.token_validation(user_id)
            
            # Check if the token is cached first
            if not self.token_id:
                await interaction.response.send_message("Nickname system not initialized. Try again later.", ephemeral=True)
                return
            
            # Check if the user has a nickname change token
            if not has_token:
                await interaction.response.send_message('You do not have a nickname change token in your inventory. Please buy one from the /shop to change a nickname', ephemeral=True)
                return
            
            # Start the modal, pass the user ID target, then validate in the modal
            await interaction.response.send_modal(NicknameModal(user_id, target_user, self.token_id, self.inventory_service))
        except Exception as e:
            traceback.print_exc()
            print("Nickname command failed!")
            
# Cog setup function
async def setup(bot, guild_object, inventory_service, nickname_service):
    cog = NicknameChange(bot, guild_object, inventory_service, nickname_service)          
    await bot.add_cog(cog)