import discord
import random
import asyncio
from discord import app_commands, Member
from discord.ext import commands

class Games(commands.Cog):
    def __init__(self, bot, guild_object, allowed_roles):
        self.bot = bot
        self.guild_object = guild_object
        self.allowed_roles = allowed_roles
        
        # Register commands to my specific guild/server
        self.bot.tree.add_command(self.rock_paper_scissors, guild=self.guild_object)
    
    # Rock/Paper/Scissors game
    @app_commands.command(name="rps", description="Play Rock, Paper, Scissors with your NattyCoins")
    async def rock_paper_scissors(self, interaction: discord.Interaction, bet: int):
        
        economy_cog = self.bot.get_cog('Economy') # Connect to the Economy Cog to use economy functions: get_balance and add_money_to_user
        
        wins_against = {
        'rock': 'scissors',
        'scissors': 'paper',
        'paper': 'rock'
        }
        
        emoji_map = {
        'rock': '🪨',
        'paper': '📄',
        'scissors': '✂️'
        }
        
        # Prompt the user to pick
        await interaction.response.send_message("React with your choice to play Rock-Paper-Scissors:\n🪨 Rock\n📄 Paper\n✂️ Scissors")
        
        # Get the message we just sent
        prompt_msg = await interaction.original_response()

        # Add the 3 emoji reactions
        for emoji in emoji_map.keys():
            await prompt_msg.add_reaction(emoji)

        # Check for valid reaction to prompt
        def check(reaction: discord.Reaction, user: discord.User):
            return (
                user.id == interaction.user.id
                and reaction.message.id == prompt_msg.id
                and str(reaction.emoji) in emoji_map
            )
        
        # Does this if chocie isnt timed out
        try:
            user_id = interaction.user.id # Identify and store the user who ran the command

            current_balance = await economy_cog.get_balance(user_id)
            
            # Check that the bet is not larger than the user's total balance
            if bet > current_balance:
                    await interaction.followup.send("You cannot place a bet that is larger than your current balance.")
                    return
                
            if bet <= 0:
                await interaction.followup.send("You must bet at least 1 NattyCoin.")
                return
            
            # Check the user's balance is > 0 for a bet
            if current_balance <= 0:
                await interaction.followup.send("You cannot place a bet when you have 0 NattyCoins. Do the Wordle, or do it better... moron.")
                return
            
            reaction, user = await self.bot.wait_for("reaction_add", timeout=15.0, check=check)
            
            # Map the choices to emojis as vars for use in messaging
            reverse_emoji_map = {v: k for k, v in emoji_map.items()}
            user_choice = reverse_emoji_map[str(reaction.emoji)]
            bot_choice = random.choice(list(wins_against.keys())) # Also randomly makes a choice for the bot
        
            # Scenarios for winning/losing
            if user_choice == bot_choice:
                await interaction.followup.send("It's a draw! You keep your NattyCoins.")
                return
            
            description = ''
            
            # Winner format
            winner_embed = discord.Embed(
                title=f"{emoji_map['rock']}Rock, {emoji_map['paper']}Paper, {emoji_map['scissors']}Scissors",
                description=description,
                color=discord.Color.gold()
            )
            
            # Loser format
            loser_embed = discord.Embed(
                title=f"{emoji_map['rock']}Rock, {emoji_map['paper']}Paper, {emoji_map['scissors']}Scissors",
                description=description,
                color=discord.Color.red()
            )
            
            if wins_against[user_choice] == bot_choice:
                amount = bet * 2
                description += f"{emoji_map[user_choice]} {user_choice.capitalize()} beats {emoji_map[bot_choice]} {bot_choice.capitalize()}!\nYou won! **{amount}** NattyCoins..."
                winner_embed.set_description(description)
                await economy_cog.add_money_to_user(user_id, amount)
                await interaction.followup.send(embed=winner_embed)
                return
            else:
                description += f"{emoji_map[user_choice]} {user_choice.capitalize()} loses against {emoji_map[bot_choice]} {bot_choice.capitalize()}...\n **{bet}** NattyCoins have been taken from your balance"
                loser_embed.set_description(description)
                await economy_cog.remove_money_from_user(user_id, bet)
                await interaction.followup.send(embed=loser_embed)
        except asyncio.TimeoutError:
            await interaction.followup.send("You took too long to respond! Try again.")
            
        
        
        
            
        
