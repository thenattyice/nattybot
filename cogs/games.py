import discord
import traceback
from discord import app_commands
from discord.ext import commands

class Games(commands.Cog):
    def __init__(self, bot, guild_object, economy_service, game_service, roulette):
        self.bot = bot
        self.guild_object = guild_object
        self.economy_service = economy_service
        self.game_service = game_service
        self.roulette = roulette
        
    # Roulette game   
    @app_commands.command(name="roulette", description="Bet on a roulette wheel/table with your NattyCoins")
    @app_commands.choices(bet_type=[
            app_commands.Choice(name="Red", value="red"),
            app_commands.Choice(name="Black", value="black"),
            app_commands.Choice(name="Odd", value="odd"),
            app_commands.Choice(name="Even", value="even"),
        ]) 
    async def play_roulette(self, interaction: discord.Interaction, bet: int, bet_type: app_commands.Choice[str]):
        # Run bet validation
        user_id = interaction.user.id
        
        game = "Roulette"
        
        try:        
            # Bet validation
            if not await self.economy_service.bet_validation(user_id, bet):
                await interaction.response.send_message("Please bet a valid amount", ephemeral=True)
                return
            
            await interaction.response.defer(ephemeral=True)
            
            # Game logic execution
            winner, number, color = await self.roulette.play_game(bet_type.value)
            
            # Call the game_result_handler to take care of user winnings/losses and game logging. Returns new balance
            new_balance = await self.game_service.game_result_handler(winner, user_id, bet, game)
            
            # Show number and emoji for color with result (winner/loser) via templatized embed
            if winner:
                result = discord.Embed(
                            title="🎉 You Win!",
                            description=f"You won **{bet}** NattyCoins!\nNew balance: **{new_balance}** NattyCoins",
                            color=discord.Color.green()
                        )
            
            # If winner = False    
            else:
                result = discord.Embed(
                            title="❌ You Lose!",
                            description=f"You rolled {color} {number}.\nYou lost **{bet}** NattyCoins.\nNew balance: **{new_balance}** NattyCoins",
                            color=discord.Color.red()
                        )
            
            # Send the result embed
            await interaction.followup.send(embed=result, ephemeral=True)
        except Exception as e:
            error_msg = "There was an error with the game. Please tell Natty."
            if interaction.response.is_done():
                await interaction.followup.send(error_msg, ephemeral=True)
            else:
                await interaction.response.send_message(error_msg, ephemeral=True)
            print(f"[ERROR] - {game} - {e}")
            traceback.print_exc()

# Register the cog at bot startup
async def setup(bot, guild_object, economy_service, game_service, roulette):
    await bot.add_cog(Games(bot, guild_object, economy_service, game_service, roulette),
                      guild=guild_object)