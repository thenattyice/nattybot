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
    
    async def get_current_jackpot(self):
        # Get current total in the jackpot
        async with self.db_pool.acquire() as conn:
            total = await conn.fetchval("""
                SELECT total
                FROM jackpot
            """)
        return total
    
    async def get_jackpot_details(self):
        # Get current total in the jackpot
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT total, last_winner_id, last_winner_date
                FROM jackpot
            """)
            
            total = row['total']
            last_winner = row['last_winner_id']
            last_winner_date = row['last_winner_date']
            
        return total, last_winner, last_winner_date
        
        
    async def add_to_jackpot(self, bet: int):
        add_to_jackpot = round(bet / 2)
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE jackpot
                SET total = total + $1
            """, add_to_jackpot)
        
    async def claim_jackpot(self, user_id: int):
        jackpot_total = await self.get_current_jackpot()
        
        # Reset the jackpot to 1000 and stamp the winning user and date
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE jackpot
                SET total = 1000,
                last_winner_id = $1,
                last_winner_date = CURRENT_DATE
            """, user_id)
            
        return jackpot_total
    
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
        
        # Initialize jackpot variables
        jackpot = False
        jackpot_value = 0
        
        # WIN CONDITIONS
        # Determine the payout multiplier based on each emoji from the above result
        if wheel1 == wheel2 == wheel3:  # All 3 wheels match
            winning_emoji = wheel1
            symbol_key = emoji_lookup[winning_emoji]
            multiplier = self.symbols[symbol_key]['payout']
            
            # Check if it's a jackpot (all moneybags)
            if symbol_key == 'moneybag':
                jackpot = True
                jackpot_value = await self.claim_jackpot(user_id)
            
            winnings = (bet * multiplier) + jackpot_value
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
        if jackpot and win:
            await self.economy_service.add_money_to_user(user_id, winnings)
            await self.game_service.log_game_result(user_id, game, 'win', bet, winnings)
            new_balance = await self.economy_service.get_balance(user_id)
            
            result = discord.Embed(
                title="🎉 JACKPOT!!! You Win!",
                description=f"You won **{bet * multiplier}** NattyCoins plus the jackpot of **{jackpot_value}** NattyCoins for a total of **{winnings}** NattyCoins!\nNew balance: **{new_balance}** NattyCoins",
                color=discord.Color.green()
            )
        
        elif win:
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