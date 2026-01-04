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
                    best_wordle_streak = GREATEST($1, COALESCE(best_wordle_streak, 0))
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
        
    # Method to insert the wordle_pts
    async def add_wordle_pts_to_user(self, target_user_id: int, points: int):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, wordle_pts)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET wordle_pts = users.wordle_pts + $2;
            """, target_user_id, points)
            
    # Function for pulling the wordle points data
    async def championship_pull(self):
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""SELECT 
                                    RANK() OVER (ORDER BY wordle_pts DESC) AS rank,
                                    user_id,
                                    wordle_pts
                                    FROM users LIMIT 5;""")
        
        description = '' # Init the field
        for row in rows:
            user_id = row['user_id']
            points = row['wordle_pts']
            rank = row['rank']
            
            # Mention the user based on id
            display_name = f"<@{user_id}>"
            
            # Add emoji for top 3
            if rank == 1:
                medal = "🥇"
            elif rank == 2:
                medal = "🥈"
            elif rank == 3:
                medal = "🥉"
            else:
                medal = f"#{rank}"
            
            description += f"**{medal}** – {display_name}: {points} points\n" # Formatting for each row in the embed
            
        # Discord embed structure
        championship_embed = discord.Embed(
            title="🏆 Wordle Championship Leaderboard 🏆",
            description=description,
            color=discord.Color.gold()
        )
        
        return championship_embed
    
    # Determine championship winner
    async def determine_champ(self):
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchrow("""WITH ranked AS (
                                            SELECT user_id, wordle_pts,
                                                RANK() OVER (ORDER BY wordle_pts DESC) AS rnk
                                            FROM users
                                        )
                                        SELECT user_id, wordle_pts
                                        FROM ranked
                                        WHERE rnk = 1;""")
        champion = result["user_id"]
        return champion
    
    # Get user's wordle streak
    async def get_user_wordle_streak(self, user_id):
        async with self.db_pool.acquire() as conn:
            current_streak = await conn.fetchval("""
                SELECT wordle_streak
                FROM users
                WHERE user_id = $1
                """, user_id)
        return current_streak
    
    # Method to apply a coin multiplier for Wordle streak
    async def wordle_payout_multiplier(self, reward: int, user_id):
        streak_multipliers = {
            0: 1.0,
            5: 1.2,
            10: 1.5,
            25: 2.0,
            50: 2.5 
        }
        
        current_streak = await self.get_user_wordle_streak(user_id)
        
        # Filter the streak_multipliers as threshholds
        eligible = [s for s in streak_multipliers if s <= current_streak]
        multiplier = streak_multipliers[max(eligible)] if eligible else 1.0
        
        return multiplier
        
        
        