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
    
    # Gambling leaderboard
    async def get_gambling_leaderboard(self) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
            SELECT
                user_id,
                SUM(wager) AS total_wagered,
                RANK() OVER (ORDER BY SUM(wager) DESC) AS rank
            FROM game_stats
            GROUP BY user_id
            ORDER BY total_wagered DESC;""")
        return [dict(row) for row in rows]
    
