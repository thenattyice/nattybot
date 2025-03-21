import os
import discord
from discord.ext import commands
from discord import app_commands

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        print("successfully finished startup")
        
        try:
            await self.tree.sync()
            print(f'Synced commands globally')
            
            guild = discord.Object(id=412828225144750092)
            synced = await self.tree.sync(guild=guild)
            print(f'Synced {len(synced)} commands to guild {guild.id}')
            
        except Exception as e:
            print(f'Error syncing commands: {e}')
            
    # Event handler for voice state updates
    async def on_voice_state_update(self, member, before, after):
        print(f"Voice state update detected for {member.name}")
        
        if before.channel is None and after.channel is not None and member.id == 280683796020330497:
            print(f'Nate joined the VC')
            try:
                # Fetch your user account (replace with your user ID)
                user = await self.fetch_user(162343822179696640)
                # Send you a DM
                await user.send("Grayson is bad at RL")
                print(f"DM sent to {user.name}")
            except Exception as e:
                print(f"Error sending DM: {e}")

intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True
client = Client(command_prefix="!", intents=intents)

GUILD_ID = discord.Object(id=412828225144750092)
#Test command
@client.tree.command(name="test", description="Nate's test command", guild=GUILD_ID)
async def sayTest(interaction: discord.Interaction):
    await interaction.response.send_message("The test worked!")

#Command to ping the boys for RL
@client.tree.command(name="rl", description="Ping the homies for rocket league", guild=GUILD_ID)
async def rlPing(interaction: discord.Interaction):
    grayson = interaction.guild.get_member(162343822179696640)
    jake = interaction.guild.get_member(277997412583473152)
    nate = interaction.guild.get_member(280683796020330497)
    await interaction.response.send_message(f'Lets go boys, its trio time {grayson.mention} {jake.mention} {nate.mention}')
    
#Command to display the F1 schedule
@client.tree.command(name="f1", description="Show 2025 F1 schedule", guild=GUILD_ID)
async def f1Schedule(interaction: discord.Interaction):
    schedule_2025 = {
        "race1": {
            "name": "Australian GP",
            "date": "3/16/2025",
            "time": "12am"
        },
        "race2": {
            "name": "Chinese GP",
            "date": "3/23/2025",
            "time": "3am"
        },
        "race3": {
            "name": "Japanese GP",
            "date": "4/6/2025",
            "time": "1am"
        },
        "race4": {
            "name": "Bharain GP",
            "date": "4/13/2025",
            "time": "11am"
        },
        "race5": {
            "name": "Saudi Arabian GP",
            "date": "4/20/2025",
            "time": "1pm"
        },
        "race6": {
            "name": "Miami GP",
            "date": "5/4/2025",
            "time": "4pm"
        },
        "race7": {
            "name": "Emilia Romagna (Imola) GP",
            "date": "5/18/2025",
            "time": "9am"
        },
        "race8": {
            "name": "Monaco GP",
            "date": "5/25/2025",
            "time": "9am"
        },
        "race9": {
            "name": "Spanish GP",
            "date": "6/1/2025",
            "time": "9am"
        },
        "race10": {
            "name": "Canadian GP",
            "date": "6/15/2025",
            "time": "2pm"
        },
        "race11": {
            "name": "Austrian GP",
            "date": "6/29/2025",
            "time": "9am"
        },
        "race12": {
            "name": "British GP",
            "date": "7/6/2025",
            "time": "10am"
        },
        "race13": {
            "name": "Belgian GP",
            "date": "7/27/2025",
            "time": "9am"
        },
        "race14": {
            "name": "Hungarian GP",
            "date": "8/3/2025",
            "time": "9am"
        },
        "race15": {
            "name": "Dutch GP",
            "date": "8/31/2025",
            "time": "9am"
        },
        "race16": {
            "name": "Italian GP",
            "date": "9/7/2025",
            "time": "9am"
        },
        "race17": {
            "name": "Azerbaijan GP",
            "date": "9/21/2025",
            "time": "7am"
        },
        "race18": {
            "name": "Singapore GP",
            "date": "8/5/2025",
            "time": "8am"
        },
        "race19": {
            "name": "United States GP",
            "date": "10/19/2025",
            "time": "3pm"
        },
        "race20": {
            "name": "Mexican GP",
            "date": "10/26/2025",
            "time": "4pm"
        },
        "race21": {
            "name": "Brazilian GP",
            "date": "11/9/2025",
            "time": "12pm"
        },
        "race22": {
            "name": "Las Vegas GP",
            "date": "11/22/2025",
            "time": "11pm"
        },
        "race23": {
            "name": "Qatar GP",
            "date": "11/30/2025",
            "time": "11am"
        },
        "race24": {
            "name": "Abu Dhabi GP",
            "date": "12/7/2025",
            "time": "8am"
        }
    }
    
    # Format all races into a single message
    message = "**2025 Formula 1 Race Schedule**\n\n"
    
    for race_num, race_info in schedule_2025.items():
        message += f"**{race_info['name']}**\n"
        message += f"Date: {race_info['date']}\n"
        message += f"Time: {race_info['time']} EST\n\n"
    
    await interaction.response.send_message(message)
    
client.run('ENTER TOKEN HERE')
