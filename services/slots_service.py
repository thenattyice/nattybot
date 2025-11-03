import random
import discord
import traceback

class SlotsService():
    def __init__(self, db_pool, economy_service, game_service):
        self.db_pool = db_pool
        self.economy_service = economy_service
        self.game_service = game_service
        
    symbols = {
        'cherries': {'emoji': '🍒', 'weight': 20, 'payout': 3},
        'lemon': {'emoji': '🍋', 'weight': 20, 'payout': 3},
        'orange': {'emoji': '🍊', 'weight': 20, 'payout': 3},
        'bell': {'emoji': '🔔', 'weight': 8, 'payout': 5},
        'star': {'emoji': '⭐', 'weight': 9, 'payout': 5},
        'grapes': {'emoji': '🍇', 'weight': 8, 'payout': 6},
        'diamond': {'emoji': '💎', 'weight': 6, 'payout': 12},
        'coin': {'emoji': '🪙', 'weight': 6, 'payout': 15},
        'seven': {'emoji': '7️⃣', 'weight': 2, 'payout': 50},
        'moneybag': {'emoji': '💰', 'weight': 1, 'payout': 100}
    }
    
    async def determine_slot_results(self):
        # Determine the 3 results, 1 per wheel
        emojis = [data['emoji'] for data in self.symbols.values()]
        weights = [data['weight'] for data in self.symbols.values()]
        
        spin_result = random.choices(emojis, weights=weights, k=3)
        
        return spin_result
    
    async def slots_result_handler(self, spin_result: list, bet: int, user_id: int):
        game = "Slots"
        
        # Assign each wheel result to a var for use
        wheel1, wheel2, wheel3 = spin_result
        
        # Build a simple dict with the emojis and their names for easy use
        emoji_lookup = {v['emoji']: k for k, v in self.symbols.items()}
        
        # Initialize win variables
        win = False
        winnings = 0
        
        # WIN CONDITIONS
        # Determine the payout multiplier based on each emoji from the above result
        if wheel1 == wheel2 == wheel3:  # All 3 wheels match
            winning_emoji = wheel1
            symbol_key = emoji_lookup[winning_emoji]
            multiplier = self.symbols[symbol_key]['payout']
            
            winnings = bet * multiplier
            win = True
            
        elif (wheel1 == wheel2) and (wheel1 != wheel3):  # Left 2 wheels match
            winning_emoji = wheel1
            symbol_key = emoji_lookup[winning_emoji]
            multiplier = self.symbols[symbol_key]['payout']
            
            winnings = bet * multiplier
            win = True
            
        elif (wheel2 == wheel3) and (wheel1 != wheel2):  # Right 2 wheels match
            winning_emoji = wheel2
            symbol_key = emoji_lookup[winning_emoji]
            multiplier = self.symbols[symbol_key]['payout']
            
            winnings = bet * multiplier
            win = True
            
        # Process the results
        if win:
            await self.economy_service.add_money_to_user(user_id, winnings)
            await self.game_service.log_game_result(user_id, game, 'win', bet, winnings)
            new_balance = await self.economy_service.get_balance(user_id)
            
            result = discord.Embed(
                title="🎉 You Win!",
                description=f"You won **{winnings}** NattyCoins!\nNew balance: **{new_balance}** NattyCoins",
                color=discord.Color.green()
            )
        else:
            new_balance = await self.economy_service.get_balance(user_id)
            
            # Log the game results
            try:
                await self.game_service.log_game_result(user_id, game, 'loss', bet, -bet)
            except Exception as e:
                print(f"[Slots] Error logging loss: {e}")
                traceback.print_exc()
            
            result = discord.Embed(
                title="😢 You Lose!",
                description=f"You lost **{bet}** NattyCoins.\nNew balance: **{new_balance}** NattyCoins",
                color=discord.Color.red()
            )
        
        return result