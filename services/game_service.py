class GameService:
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    # Logs game result data to the DB    
    async def log_game_result(self, user_id: int, game: str, result: str, wager: int, balance_change: int):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO game_stats (user_id, game, result, wager, balance_change)
                VALUES ($1, $2, $3, $4, $5)
            """, user_id, game, result, wager, balance_change)
            
    # Total user's wins
    async def get_total_wins(self, user_id: int):
        async with self.db_pool.acquire() as conn:
            win_count = await conn.fetch("""
                SELECT count(user_id) FROM game_stats
                WHERE user_id = $1
                AND result = 'win';
                """, user_id)
        return win_count
    
    # Total user's losses
    async def get_total_losses(self, user_id: int):
        async with self.db_pool.acquire() as conn:
            loss_count = await conn.fetch("""
                SELECT count(user_id) FROM game_stats
                WHERE user_id = $1
                AND result = 'loss';
                """, user_id)
        return loss_count
    
    # Calculate win ratio
    async def calc_win_ratio(self, user_id: int):
        win_count = int(self.get_total_wins)
        loss_count = int(self.get_total_losses)
        
        games_played = win_count + loss_count
        
        win_percentage = win_count / games_played
        
        return win_percentage
    
    # Total user's amount wagered
    async def get_amount_wagered(self, user_id: int):
        async with self.db_pool.acquire() as conn:
            total_wagered = await conn.fetch("""
                SELECT sum(wager) FROM game_stats
                WHERE user_id = $1
                """, user_id)
        return total_wagered
    
    # Get user's wordle stats
    async def get_user_wordle_stats(self, user_id: int) -> int:
        async with self.db_pool.acquire() as conn:
            wordle_pts = await conn.fetch("""
                SELECT wordle_pts FROM users
                WHERE user_id = $1;
                """, user_id)
        return wordle_pts
    
    # Get user's total games played
    async def get_total_games(self, user_id: int) -> int:
        async with self.db_pool.acquire() as conn:
            total_games = await conn.fetch("""
                SELECT count(user_id) FROM game_stats
                WHERE user_id = $1;
                """, user_id)
        return total_games
    
    # Get user's fav game
    async def get_fav_game(self, user_id: int):
        async with self.db_pool.acquire() as conn:
            fav_game = await conn.fetch("""
                SELECT game, COUNT(*) as play_count
                FROM game_stats
                WHERE user_id = $1
                GROUP BY game
                ORDER BY play_count DESC
                LIMIT 1;
                """, user_id)
        return fav_game