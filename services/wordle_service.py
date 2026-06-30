import discord
from datetime import datetime, date, timedelta

class WordleService():
    def __init__(self, db_pool, user_service):
        self.db_pool = db_pool
        self.user_service = user_service
        
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
        
        # Initial check
        streaks = await self.check_wordle_streaks(wordle_players)
        
        existing_players = {row['user_id'] for row in streaks}
        new_players = [uid for uid in wordle_players if uid not in existing_players]
        
        # New player check
        if new_players:
            for uid in new_players:
                result = await self.user_service.add_user(uid)
                
                rows_inserted = int(result.split()[-1])
                if rows_inserted > 0:
                    print(f"[WORDLE STREAK] New user inserted: {uid}")
                    streaks.append({
                        'user_id': uid,
                        'wordle_streak': 0,
                        'last_wordle_date': None,
                        'best_wordle_streak': None
                    })
                else:
                    print(f"[WORDLE STREAK] User {uid} already existed, skipping.")
        
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
                print(f'[WORDLE STREAK] Continuing streak for {user_id}. New streak value: {new_wordle_streak}')
                
            elif days_between_last_wordle > 1:
                # Reset the current wordle streak to 1 and check if its their best streak
                new_wordle_streak = 1
                await self.update_wordle_details(user_id, yesterday, new_wordle_streak)
                print(f'[WORDLE STREAK] Resetting streak for {user_id}. New streak value: {new_wordle_streak}')
            
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
                                    FROM users
                                    WHERE wordle_pts > 0
                                    LIMIT 5;""")
        
        description = '' # Init the field
        
        if rows:
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
        else:
            description = 'No users with Wordle points!'
            
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
        if result is None:
            return None
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
            5: 1.25,
            10: 1.5,
            25: 2.0,
            50: 2.5,
            100: 3.0,
            150: 3.5,
            200: 4.0,
            250: 4.5,
            300: 5.0 
        }
        
        current_streak = await self.get_user_wordle_streak(user_id)
        
        # Filter the streak_multipliers as thresholds
        eligible = [s for s in streak_multipliers if s <= current_streak]
        multiplier = streak_multipliers[max(eligible)] if eligible else 1.0
        
        return multiplier
        
    # Method to clear current wordle pts in user table
    async def clear_all_wordle_pts(self):
        async with self.db_pool.acquire() as conn:
                    rows = await conn.execute("""
                        WITH users_with_pts AS (
                            SELECT user_id FROM users
                            WHERE wordle_pts > 0
                        )
                        UPDATE users
                        SET wordle_pts = 0
                        FROM users_with_pts uwp
                        WHERE users.user_id = uwp.user_id
                    """)
                    
    # Log daily wordle results to the wordle_results table
    async def log_wordle_results(self, wordle_results: dict):
        today = date.today()
        game_date =  today - timedelta(days=1) # Yesterday
        
        records = [(user_id, score, game_date) for user_id, score in wordle_results.items()]
        
        async with self.db_pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO wordle_results (user_id, guesses, game_date)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, game_date) DO NOTHING
            """, records)
    
    # Get all wordle guess data for a specific month
    async def get_month_wordle_results(self, month_name: str  | None , year: int | None):
        # Set the month number properly for the query
        if not month_name:
            month_num = datetime.now().month
        else:
            # Convert the month text to num for SQL query
            month_num = datetime.strptime(month_name, "%B").month
            
        # Default the year to current year
        if year is None:
            year = date.today().year
            
        # SQL query to get the data
        async with self.db_pool.acquire() as conn:
            return await conn.fetch("""
                SELECT user_id, guesses, game_date
                FROM wordle_results
                WHERE EXTRACT(MONTH FROM game_date) = $1
                AND EXTRACT(YEAR FROM game_date) = $2
                ORDER BY game_date ASC
            """, month_num, year)
    
    # Summarize a player's wordle performance in a month by: Dates played, count per guess (0-6), avg wordle guess count
    async def user_wordle_summary(self, user_id: int, month: int, year: int):
        async with self.db_pool.acquire() as conn:
            return await conn.fetchrow("""
                SELECT
                    user_id,
                    COUNT(*) FILTER (WHERE guesses = 1) AS guess_1,
                    COUNT(*) FILTER (WHERE guesses = 2) AS guess_2,
                    COUNT(*) FILTER (WHERE guesses = 3) AS guess_3,
                    COUNT(*) FILTER (WHERE guesses = 4) AS guess_4,
                    COUNT(*) FILTER (WHERE guesses = 5) AS guess_5,
                    COUNT(*) FILTER (WHERE guesses = 6) AS guess_6,
                    COUNT(*) FILTER (WHERE guesses = 0) AS guess_fail,
                    COUNT(*) AS total_games,
                    ROUND(AVG(guesses) FILTER (WHERE guesses != 0), 2) AS avg_guesses
                FROM wordle_results
                WHERE user_id = $1
                    AND EXTRACT(MONTH FROM game_date) = $2
                    AND EXTRACT(YEAR FROM game_date) = $3
                GROUP BY user_id
            """, user_id, month, year)
            