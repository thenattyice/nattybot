import discord
import traceback
from discord import app_commands, Member, TextChannel
from discord.ext import commands, tasks
from datetime import datetime

class Formula1(commands.Cog):
    def __init__(self, bot, guild_object, f1_service):
        self.bot = bot
        self.guild_object = guild_object
        self.f1_service = f1_service
        self.notification_role = None
    
        # Register commands here
        self.bot.tree.add_command(self.f1_command, guild=self.guild_object)
    
    # Run setup when cog is loaded
    async def cog_load(self):
        await self.bot.wait_until_ready()
        await self.setup_notification_role()
        
    async def setup_notification_role(self):
        try:
            guild = self.bot.get_guild(self.guild_object.id)
            
            if not guild:
                print("❌ Guild not found in bot cache")
                return
            
            role = discord.utils.get(guild.roles, name="F1 Notifications")
            
            if not role:
                role = await guild.create_role(
                        name="F1 Notifications",
                        color=discord.Color.red(),
                        mentionable=True,
                        reason="F1 Race Notification Role - Natty Bot"
                    )
                print(f"[F1] F1 Notification role created! ID: {role.id}")
                
                self.notification_role = role
            else:
                print(f"[F1] Found existing F1 Notifications Role! ID: {role.id}")
                
        except discord.Forbidden:
            print("❌ Bot lacks 'Manage Roles' permission to create F1 Notifications role")
        except Exception as e:
            print(f"❌ Error setting up F1 notification role: {e}")
            traceback.print_exc()
            
    # Command to get the next race weekend details
    @app_commands.command(name="f1", description="Utilize the F1 features of the bot!")
    @app_commands.choices(action=[
        app_commands.Choice(name="Next Race Weekend", value="next_race"),
        app_commands.Choice(name="Full Season", value="full_season")
    ])
    async def f1_command(self, interaction: discord.Interaction, action: app_commands.Choice[str]):
        # Logic to get the next race weekend details
        if action.value == 'next_race':
            sessions = await self.f1_service.determine_next_race() 
            
            if not sessions:
                await interaction.response.send_message(
                    "No upcoming races found.", 
                    ephemeral=True
                )
                return
            
            else:
                description = ""
                
                # Convert to unix
                start_date = int(sessions['start'].timestamp())
                end_date = int(sessions['end'].timestamp())
                
                description += f"<t:{start_date}:D> - <t:{end_date}:D>\n\n"
                
                for s in sessions['race_sessions']:
                    session_start = int(s['date_start'].timestamp())

                    description += f"{s['session_name']}: <t:{session_start}:F>\n"
                
                embed = discord.Embed(
                    title=f'**{sessions['race']}**',
                    description=description,
                    color=discord.Color.red()
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)

        # Logic to get the full season calendar
        elif action.value == 'full_season':
            races = await self.f1_service.get_current_season()
            
            description = ""
            
            if not races:
                await interaction.response.send_message(
                    "No races are populated for the current season.", 
                    ephemeral=True
                )
                return
            
            else:
                for race in races:
                    start_date = int(race['date_start'].timestamp())
                    end_date = int(race['date_end'].timestamp())
                    
                    description += f"**Round {race['round']}**\n"
                    description += f"{race['meeting_name']}\n"
                    description += f"<t:{start_date}:D> - <t:{end_date}:D>\n\n"
                    
                embed = discord.Embed(
                    title='**F1 Season**',
                    description=description,
                    color=discord.Color.red()
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)                 
        
async def setup(bot, guild_object, f1_service):
    cog = Formula1(bot, guild_object, f1_service)          
    await bot.add_cog(cog)