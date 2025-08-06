import discord
import random
import asyncio
import traceback
from discord import app_commands, Member
from discord.ext import commands
from .utils import bet_validation

class BlackjackView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=300)  # 5 min timeout
        self.bot = bot
        self.user_id = user_id
        
    # Only allow the player who started the game to use the buttons
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            cog = self.bot.get_cog("Blackjack")
            session = cog.sessions.get(self.user_id)
            if not session:
                await interaction.response.send_message("Session expired or not found.", ephemeral=True)
                return

            # Draw a card for player
            card = session['deck'].pop()
            session['player_hand'].append(card)

            value = Blackjack.calculate_hand_value(session['player_hand'])
            if value > 21:
                # Player busts, disable buttons
                for item in self.children:
                    item.disabled = True
                    
                bust_embed = discord.Embed(
                    title="Blackjack",
                    description=f"You drew {card}. Bust! Your hand: {session['player_hand']} ({value})",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=bust_embed, view=self)
                del cog.sessions[self.user_id]  # End game
            else:
                hit_embed = discord.Embed(
                    title="Blackjack",
                    description=f"You drew {card}. Your hand: {session['player_hand']} ({value})",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=hit_embed, view=self)
        except Exception as e:
            traceback.print_exc()

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            cog = self.bot.get_cog("Blackjack")
            session = cog.sessions.get(self.user_id)
            if not session:
                await interaction.response.send_message("Session expired or not found.", ephemeral=True)
                return

            session['stand'] = True
            # Disable the buttons
            for item in self.children:
                item.disabled = True

            dealer_hand = session['dealer_hand']
            deck = session['deck']
            
            initial_stand_embed = discord.Embed(
                title="Blackjack",
                description=(
                    f"**Your hand:** {', '.join(session['player_hand'])} ({Blackjack.calculate_hand_value(session['player_hand'])})\n"
                    f"**Dealer’s visible card:** {dealer_hand[0]} ({Blackjack.calculate_hand_value(session['dealer_hand'])})\n"
                    f"Dealer reveals their hole card..."
                ),
                color=discord.Color.red()
                )
            
            await interaction.response.edit_message(embed=initial_stand_embed, view=self)
            await asyncio.sleep(1.5)

            # Dealer hits until 17+
            while Blackjack.calculate_hand_value(dealer_hand) < 17:
                drawn_card = deck.pop()
                dealer_hand.append(drawn_card)
                
                updated_stand_embed = discord.Embed(
                title="Blackjack",
                description=(
                    f"**Your hand:** {', '.join(session['player_hand'])} ({Blackjack.calculate_hand_value(session['player_hand'])})\n"
                    f"**Dealer draws...** {drawn_card}"
                    f"**Dealer’s hand:** {', '.join(dealer_hand)} ({Blackjack.calculate_hand_value(session['dealer_hand'])})\n"
                ),
                color=discord.Color.red()
                )
                
                await interaction.edit_original_response(embed=updated_stand_embed, view=self)
                await asyncio.sleep(1.5)

            player_value = Blackjack.calculate_hand_value(session['player_hand'])
            dealer_value = Blackjack.calculate_hand_value(dealer_hand)

            # Decide winner
            if dealer_value > 21 or player_value > dealer_value:
                result = "You win!"
            elif dealer_value == player_value:
                result = "It's a tie!"
            else:
                result = "Dealer wins!"

            final_stand_embed = discord.Embed(
                title="Blackjack",
                description=(
                    f"**Your hand:** {', '.join(session['player_hand'])} ({player_value})\n"
                    f"**Dealer’s visible card:** {', '.join(['dealer_hand'])} ({dealer_value})\n"
                    f"**Result** {result}"
                ),
                color=discord.Color.green() if "win" in result.lower() else discord.Color.red()
                )
            
            await interaction.response.edit_message(embed=final_stand_embed, view=self)
            
            del cog.sessions[self.user_id]  # End the game by deleting the session
        except Exception as e:
            traceback.print_exc()

class Blackjack(commands.Cog):
    def __init__(self, bot, guild_object):
        self.bot = bot
        self.guild_object = guild_object
        
        self.sessions = {}
        
        # Blackjack slash command here
        self.bot.tree.add_command(self.blackjack, guild=self.guild_object)
        
    def create_new_game(self, user_id):
        deck = self.create_shoe()
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        self.sessions[user_id] = {
            'deck': deck,
            'player_hand': player_hand,
            'dealer_hand': dealer_hand,
            'stand': False,
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
    async def blackjack(self, interaction: discord.Interaction):
        try:
            user_id = interaction.user.id
            self.create_new_game(user_id)
            session = self.sessions[user_id]

            player_hand = session['player_hand']
            dealer_hand = session['dealer_hand']

            view = BlackjackView(self.bot, user_id)
            
            player_hand_value = self.calculate_hand_value(player_hand)

            gamestart_embed = discord.Embed(
                title="🎮 Natty Games: Blackjack 🎮",
                description=(
                    f"Game started!\n"
                    f"**Your hand:** {', '.join(player_hand)} ({player_hand_value})\n"
                    f"**Dealer’s visible card:** {dealer_hand[0]}"
                ),
                color=discord.Color.red()
            )
            
            await interaction.response.send_message(
                embed=gamestart_embed,
                view=view
            )
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send("An error occurred while running the game.", ephemeral=True)
        
async def setup(bot, guild_object):
    await bot.add_cog(Blackjack(bot, guild_object))