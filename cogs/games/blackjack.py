import discord
import random
import asyncio
import traceback
from discord import app_commands, Member
from discord.ext import commands
from .utils import bet_validation

class BlackjackView(discord.ui.View):
    def __init__(self, cog, bot, user_id, bet: int, economy_cog):
        super().__init__(timeout=300)  # 5 min timeout
        self.cog = cog
        self.bot = cog.bot
        self.user_id = user_id
        self.bet = bet
        self.economy_cog = economy_cog
        
    # Only allow the player who started the game to use the buttons
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    async def bet_handler(self, interaction: discord.Interaction, outcome: str):
        user_id = self.user_id
        session = self.cog.sessions.get(user_id)
        if not session:
            return
        
        bet = session['current_bet']
        
        if outcome == "win":
            winnings = bet * 2
            await self.economy_cog.add_money_to_user(user_id, winnings)
            new_balance = await self.economy_cog.get_balance(user_id)
            result = discord.Embed(
                title="🎉 You Win!",
                description=f"You won **{winnings}** NattyCoins!\nNew balance: **{new_balance}** NattyCoins",
                color=discord.Color.green()
            )
        elif outcome == "push":
            winnings = bet
            await self.economy_cog.add_money_to_user(user_id, winnings)
            new_balance = await self.economy_cog.get_balance(user_id)
            result = discord.Embed(
                title="You Tied",
                description=f"You get your bet back.\nBalance: **{new_balance}** NattyCoins",
                color=discord.Color.red()
            )
        elif outcome == "loss":
            new_balance = await self.economy_cog.get_balance(user_id)
            result = discord.Embed(
                title="😢 You Lose!",
                description=f"You lost **{self.bet}** NattyCoins.\nNew balance: **{new_balance}** NattyCoins",
                color=discord.Color.red()
            )
        await interaction.followup.send(embed=result, ephemeral=True)
        self.stop()

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            session = self.cog.sessions.get(self.user_id)
            if not session:
                await interaction.response.send_message("Session expired or not found.", ephemeral=True)
                return

            # Draw a card for player
            card = session['deck'].pop()
            session['player_hand'].append(card)
            
            title = self.cog.blackjack_title

            value = Blackjack.calculate_hand_value(session['player_hand'])
            
            description = f"You drew {card}. Your hand: {', '.join(session['player_hand'])} ({value})"
            
            if value > 21:
                description += "\nBust!"
                color = discord.Color.red()
                # Player busts, disable buttons
                for item in self.children:
                    item.disabled = True
                    
                outcome = "loss"
                
                bust_embed = discord.Embed(title=title,description=description,color=color)
                
                await interaction.response.edit_message(embed=bust_embed, view=self)
                await self.bet_handler(interaction, outcome)
                del self.cog.sessions[self.user_id]  # End game
            else:
                color = discord.Color.green()
                hit_embed = discord.Embed(title=title,description=description,color=color)
                await interaction.response.edit_message(embed=hit_embed, view=self)
        except Exception as e:
            traceback.print_exc()

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            session = self.cog.sessions.get(self.user_id)
            if not session:
                await interaction.response.send_message("Session expired or not found.", ephemeral=True)
                return

            session['stand'] = True

            # Disable the buttons
            for item in self.children:
                item.disabled = True

            dealer_hand = session['dealer_hand']
            deck = session['deck']
            
            title = self.cog.blackjack_title

            # First update: dealer reveals hole card
            initial_stand_embed = discord.Embed(
                title=title,
                description=(
                    f"**Your hand:** {', '.join(session['player_hand'])} "
                    f"({Blackjack.calculate_hand_value(session['player_hand'])})\n"
                    f"**Dealer’s hand:** {', '.join(dealer_hand)} "
                    f"({Blackjack.calculate_hand_value(dealer_hand)})\n"
                    f"Dealer reveals their hole card..."
                ),
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=initial_stand_embed, view=self)
            await asyncio.sleep(2)

            # Dealer draws until at least 17
            while Blackjack.calculate_hand_value(dealer_hand) < 17:
                drawn_card = deck.pop()
                dealer_hand.append(drawn_card)

                updated_stand_embed = discord.Embed(
                    title=title,
                    description=(
                        f"**Your hand:** {', '.join(session['player_hand'])} "
                        f"({Blackjack.calculate_hand_value(session['player_hand'])})\n"
                        f"**Dealer draws:** {drawn_card}\n"
                        f"**Dealer’s hand:** {', '.join(dealer_hand)} "
                        f"({Blackjack.calculate_hand_value(dealer_hand)})"
                    ),
                    color=discord.Color.red()
                )

                await interaction.edit_original_response(embed=updated_stand_embed, view=self)
                await asyncio.sleep(2)

            # Decide winner
            player_value = Blackjack.calculate_hand_value(session['player_hand'])
            dealer_value = Blackjack.calculate_hand_value(dealer_hand)

            if dealer_value > 21 or player_value > dealer_value:
                result = "You win!"
                color = discord.Color.green()
                outcome = "win"
            elif dealer_value == player_value:
                result = "It's a tie!"
                color = discord.Color.orange()
                outcome = "push"
            else:
                result = "Dealer wins!"
                color = discord.Color.red()
                outcome = "loss"

            final_stand_embed = discord.Embed(
                title=title,
                description=(
                    f"**Your hand:** {', '.join(session['player_hand'])} ({player_value})\n"
                    f"**Dealer’s hand:** {', '.join(dealer_hand)} ({dealer_value})\n"
                    f"**Result:** {result}"
                ),
                color=color
            )

            await interaction.edit_original_response(embed=final_stand_embed, view=self)
            await self.bet_handler(interaction, outcome)

            # End game session
            del self.cog.sessions[self.user_id]

        except Exception as e:
            traceback.print_exc()
            
    async def on_timeout(self):
        # Remove the session when the view times out to prevent stale sessions
        self.cog.sessions.pop(self.user_id, None)
        
        # Disable buttons visually to show the game ended due to timeout
        for item in self.children:
            item.disabled = True
            
class Blackjack(commands.Cog):
    
    blackjack_title = "🎮 Natty Games: Blackjack 🎮"
    
    def __init__(self, bot, guild_object):
        self.bot = bot
        self.guild_object = guild_object
        
        self.sessions = {}
        
        # Blackjack slash command here
        self.bot.tree.add_command(self.blackjack, guild=self.guild_object)
        
    def create_new_game(self, user_id, bet):
        deck = self.create_shoe()
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        self.sessions[user_id] = {
            'deck': deck,
            'player_hand': player_hand,
            'dealer_hand': dealer_hand,
            'stand': False,
            'original_bet': bet,
            'current_bet': bet,
        }
        
    def create_shoe(self, num_decks=6):
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        suits = ['♠', '♥', '♦', '♣']
        single_deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
        shoe = single_deck * num_decks
        random.shuffle(shoe)
        return shoe
    
    # Define the values for each card
    @staticmethod
    def get_card_value(card):
        rank = card[:-1] # Strip the suit from the card
        if rank in ['J', 'Q', 'K']:
            return 10
        elif rank =='A':
            return 11 # Handling 1 or 11 later down the line in calculate_hand_value
        else:
            return int(rank)
    
    @staticmethod    
    def calculate_hand_value(hand):
        value = sum(Blackjack.get_card_value(card) for card in hand)
        # Handling Ace if value is over 21
        aces = sum(1 for card in hand if card[:-1] == 'A')
        while value > 21 and aces:
            value -= 10 # Counts Ace as 1 instead of 10
            aces -= 1
        return value
    
    # Blackjack game
    @app_commands.command(name="blackjack", description="Bet on a game of blackjack with your NattyCoins")
    async def blackjack(self, interaction: discord.Interaction, bet: int):
        try:
            economy_cog = self.bot.get_cog('Economy') # Connect to the Economy Cog to use economy functions: get_balance and add_money_to_user
            user_id = interaction.user.id
            
            # Bet validation
            if not await bet_validation(interaction, economy_cog, user_id, bet):
                return
            
            # Validate that user isn't already in a session
            if user_id in self.sessions:
                await interaction.response.send_message("You are already in a game!", ephemeral=True)
                print("Validation Failure: user already in a session")
                return
            
            # Create a new game session instance
            self.create_new_game(user_id, bet)
            session = self.sessions[user_id]
            
            try:
                await economy_cog.remove_money_from_user(user_id, bet)
            except:
                del self.sessions[user_id]
                raise

            player_hand = session['player_hand']
            dealer_hand = session['dealer_hand']

            view = BlackjackView(self, self.bot, user_id, bet, economy_cog)
            
            player_hand_value = self.calculate_hand_value(player_hand)
            
            title = self.blackjack_title

            gamestart_embed = discord.Embed(
                title=title,
                description=(
                    f"Game started!\n"
                    f"**Your hand:** {', '.join(player_hand)} ({player_hand_value})\n"
                    f"**Dealer’s visible card:** {dealer_hand[0]}"
                ),
                color=discord.Color.red()
            )
            
            await interaction.response.send_message(
                embed=gamestart_embed,
                view=view,
                ephemeral=True
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send("An error occurred while running the game.", ephemeral=True)
        
async def setup(bot, guild_object):
    await bot.add_cog(Blackjack(bot, guild_object))