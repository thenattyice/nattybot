class GameService:
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    # Logs game result data to the DB    
    async def log_game_result(self, user_id: int, game: str, result: str, wager: int, balance_change: int):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO item_usage (user_id, game, result, wager, balance_change)
                VALUES ($1, $2, $3, 1, $4, $5)
            """, user_id, game, result, wager, balance_change)