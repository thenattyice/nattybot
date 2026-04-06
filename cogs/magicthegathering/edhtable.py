import discord
import traceback
import asyncio
from discord import app_commands, Member
from discord.ext import commands
from discord.ui import Modal, TextInput
from datetime import datetime
from zoneinfo import ZoneInfo

eastern = ZoneInfo("America/New_York")

class RSVPButton(discord.ui.View):
    def __init__(self, start_time: datetime, discord_timestamp: str):
        super().__init__(timeout=None)
        self.start_time = start_time
        self.discord_timestamp = discord_timestamp
        self.max_players = 4
        self.attending = []
        self.not_attending = []
        self.message = None
        self.embed = discord.Embed(title='MTG Commander Table', color=discord.Color.green())
        self.embed.description = "Game Time: " + discord_timestamp
    
    # Method to start the countdown    
    async def start_timer(self):
        
        now = datetime.now(eastern)
        seconds_until_start = (self.start_time - now).total_seconds() # Calculate how many seconds until start_time
        
        # If the time is in the future, sleep until then
        if seconds_until_start > 0:
            await asyncio.sleep(seconds_until_start)
            # Once sleep is done, call close_rsvp with an appropriate reason
            await self.close_rsvp("Event signup is now closed!")

    async def close_rsvp(self, reason: str):
        # Loop through all items in self.children and disable each one
        for item in self.children:
            item.disabled = True
            
        # Build a closed embed showing the final attending/not attending lists
        closed_embed = discord.Embed(
            title='MTG Commander Table',
            description=f'Game Time: {self.discord_timestamp}',
            color=discord.Color.green()
        )
        
        closed_embed.add_field(name="Player 1", value=self.attending[0].display_name if len(self.attending) > 0 else "Empty", inline=True)
        closed_embed.add_field(name="Player 2", value=self.attending[1].display_name if len(self.attending) > 1 else "Empty", inline=True)
        closed_embed.add_field(name="Player 3", value=self.attending[2].display_name if len(self.attending) > 2 else "Empty", inline=True)
        closed_embed.add_field(name="Player 4", value=self.attending[3].display_name if len(self.attending) > 3 else "Empty", inline=True)
        
        # Call self.stop() to stop listening for interactions
        self.stop()
        
        await self.message.edit(embed=closed_embed, view=self)
        
        mention_string = ', '.join([user.mention for user in self.attending])
        
        # Send a message pinging the RSVP'd players
        await self.message.channel.send(f"ITs MAGIC TIME! {mention_string}")

    @discord.ui.button(label="✅ Attending", style=discord.ButtonStyle.green)
    async def attending_btn(self, interaction, button):
        try:
            user = interaction.user # Get the user object of whoever clicks
            
            # If they are already in attending, send an ephemeral "already RSVP'd" message and return
            if user in self.attending:
                await interaction.response.send_message('You are already attending!', ephemeral=True)
                return
            
            if user in self.not_attending:
                self.not_attending.remove(user)
                self.attending.append(user)
                await interaction.response.send_message("You are now registered for tonight's shenanigans", ephemeral=True)
                
            elif user not in self.attending and user not in self.not_attending:
                self.attending.append(user)
                await interaction.response.send_message("You are now registered for tonight's shenanigans", ephemeral=True)
                
            if len(self.attending) >= self.max_players:
                await self.close_rsvp()
                
            else:
                await self.update_embed()
        
        except Exception as e:
            traceback.print_exc()
            print(f"[EDHTable] Attending Error: {e}")

    @discord.ui.button(label="❌ Not Attending", style=discord.ButtonStyle.red)
    async def not_attending_btn(self, interaction, button):
        try:
            user = interaction.user # Get the user object of whoever clicks
            
            # If they are already in attending, send an ephemeral "already RSVP'd" message and return
            if user in self.not_attending:
                await interaction.response.send_message("You are already RSVP'd!", ephemeral=True)
                return
            
            if user in self.attending:
                self.attending.remove(user)
                self.not_attending.append(user)
                await interaction.response.send_message("You are now unregistered. Shame on you.", ephemeral=True)
                
            elif user not in self.attending and user not in self.not_attending:
                self.not_attending.append(user)
                await interaction.response.send_message("You're missing out, loser", ephemeral=True)
                
            if len(self.attending) >= self.max_players:
                await self.close_rsvp()
                
            else:
                await self.update_embed()
        except Exception as e:
            traceback.print_exc()
            print(f"[EDHTable] Not-attending Error: {e}")

    async def update_embed(self):
        self.embed.clear_fields() # Clear all fields each time, then repopulate with changes below
        
        self.embed.add_field(name="Player 1", value=self.attending[0].display_name if len(self.attending) > 0 else "Empty", inline=True)
        self.embed.add_field(name="Player 2", value=self.attending[1].display_name if len(self.attending) > 1 else "Empty", inline=True)
        self.embed.add_field(name="Player 3", value=self.attending[2].display_name if len(self.attending) > 2 else "Empty", inline=True)
        self.embed.add_field(name="Player 4", value=self.attending[3].display_name if len(self.attending) > 3 else "Empty", inline=True)

        await self.message.edit(embed=self.embed, view=self)

# Modal class that displays to the user and prompts for the start time of MTG games
class StartTimeModal(Modal, title="Set Start Time"):
    start_time = TextInput(
        label="Start Time",
        placeholder="e.g. 14:30 or 2:30 PM",
        required=True,
        max_length=20
    )
    
    # Executes on submission of the Modal
    async def on_submit(self, interaction: discord.Interaction):
        raw_text = self.start_time.value.strip() # Get the raw text input
        
        parsed_time = None
        for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p"):
            try:
                parsed_time = datetime.strptime(raw_text.upper(), fmt)
                break
            except ValueError:
                continue
            
        if parsed_time is None:
            await interaction.response.send_message("Invalid time submitted. Please use 14:30 or 2:30 PM", ephemeral=True)
            return
        
        # Format the time to utilize it
        today = datetime.now(eastern)
        self.parsed_time = parsed_time.replace(year=today.year, month=today.month, day=today.day, tzinfo=eastern)
        unix_timestamp = int(self.parsed_time.timestamp())
        discord_timestamp = f"<t:{unix_timestamp}:F>"
        self.discord_timestamp = discord_timestamp
        
        view = RSVPButton(self.parsed_time, self.discord_timestamp) # Initialize the button view
        
        # Send the button embed to the channel
        await interaction.response.send_message(embed=view.embed, view=view)
        
        # Store the message on the button view
        view.message = await interaction.original_response()
        
        # Kick off the timer async task
        asyncio.create_task(view.start_timer())
        
class EDHTable(commands.Cog):
    def __init__(self, bot, guild_object, game_roles):
        self.bot = bot
        self.guild_object = guild_object
        self.game_roles = game_roles
        
        # Registered commands
        self.bot.tree.add_command(self.mtg_table, guild=self.guild_object)
        
    # Command to open up a table 
    @app_commands.command(name="table", description="Get an MTG Commander table booked!")
    async def mtg_table(self, interaction: discord.Interaction):
        # Prompts for start time
        try:
            user = interaction.user
            
            mtg_role_id = self.game_roles["mtg"]
            mtg_role = interaction.guild.get_role(mtg_role_id)
            
            await interaction.response.send_message(f"{user.mention} want to play some Commander tonight! RSVP below for an open slot\n{mtg_role.mention}")
            
            await interaction.response.send_modal(StartTimeModal())
            
        except Exception as e:
            print(f"MTG TABLE ERROR: {e}")
            traceback.print_exc()
            
async def setup(bot, guild_object, game_roles):
    cog = EDHTable(bot, guild_object, game_roles)          
    await bot.add_cog(cog)