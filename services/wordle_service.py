import discord
import traceback
from datetime import date, timedelta

class WordleService():
    def __init__(self, db_pool):
        self.db_pool = db_pool
        
    # Get the current wordle streak details
    async def check_wordle_streaks(self, wordle_players: list):
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, wordle_streak, last_wordle_date, best_wordle_streak
                FROM users
                WHERE user_id = ANY($1)
                """, wordle_players)
        return rows
    
    # Update user Wordle details
    async def update_wordle_details(self, user_id: int, last_wordle_date: date, wordle_streak: int):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE users
                SET wordle_streak = $1,
                    last_wordle_date = $2,
                    best_wordle_streak = CASE
                        WHEN $1 > best_wordle_streak THEN $1
                        ELSE best_wordle_streak
                    END
                WHERE user_id = $3
                """, wordle_streak, last_wordle_date, user_id)
            
    # Update best wordle streak
    async def update_best_wordle_streak(self, user_id: int, best_wordle_streak: int):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE users
                SET best_wordle_streak = $1
                WHERE user_id = $2
                """, best_wordle_streak, user_id)
            
    # Reset all users where wordle_streak > 0 AND last_wordle_date < yesterday
    async def wordle_streak_cleanup(self, yesterday):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE users
                SET wordle_streak = 0
                WHERE wordle_streak > 0 
                AND last_wordle_date < $1
                """, yesterday)
    
    # Determine if latest wordle result players have streak
    async def wordle_streak_process(self, wordle_players: list):
        today = date.today()
        yesterday =  today - timedelta(days=1)
        
        streaks = await self.check_wordle_streaks(wordle_players)
        
        for row in streaks:
            user_id = row['user_id']
            wordle_streak = row['wordle_streak']
            last_wordle_date = row['last_wordle_date']
            
            # Handle first-time players (no previous wordle date)
            if last_wordle_date is None:
                # This is their first wordle, start streak at 1
                await self.update_wordle_details(user_id, yesterday, 1)
                continue
            
            days_between_last_wordle = (yesterday - last_wordle_date).days
            
            if days_between_last_wordle == 1:
                # Update the user's current streak to continue it
                new_wordle_streak = wordle_streak + 1
                await self.update_wordle_details(user_id, yesterday, new_wordle_streak)
                
            elif days_between_last_wordle > 1:
                # Reset the current wordle streak to 1 and check if its their best streak
                new_wordle_streak = 1
                await self.update_wordle_details(user_id, yesterday, new_wordle_streak)
            
        # Catch all for users not in the summary
        await self.wordle_streak_cleanup(yesterday)