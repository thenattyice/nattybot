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
    
    # One method to rule them all
    async def get_full_user_game_stats(self, user_id: int):
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    u.user_id,
                    COALESCE(SUM(CASE WHEN g.result = 'win' THEN 1 ELSE 0 END), 0) AS wins,
                    COALESCE(SUM(CASE WHEN g.result = 'loss' THEN 1 ELSE 0 END), 0) AS losses,
                    COALESCE(SUM(CASE WHEN g.result = 'draw' THEN 1 ELSE 0 END), 0) AS draws,
                    COALESCE(COUNT(g.*), 0) AS total_games,
                    COALESCE(SUM(g.wager), 0) AS total_wagered,
                    COALESCE(SUM(g.balance_change), 0) AS net_winnings,
                    CASE
                        WHEN SUM(CASE WHEN g.result IN ('win','loss') THEN 1 ELSE 0 END) = 0 THEN 0
                        ELSE ROUND(
                            (SUM(CASE WHEN g.result = 'win' THEN 1 ELSE 0 END)::numeric
                            /
                            SUM(CASE WHEN g.result IN ('win','loss') THEN 1 ELSE 0 END)) * 100, 2
                        )
                    END AS win_ratio,
                    COALESCE((
                        SELECT game
                        FROM game_stats
                        WHERE user_id = u.user_id
                        GROUP BY game
                        ORDER BY COUNT(*) DESC
                        LIMIT 1
                    ), 'None') AS most_played_game,
                    DENSE_RANK() OVER (ORDER BY COALESCE(SUM(g.wager), 0) DESC) AS wager_rank,
                    u.wordle_pts
                FROM users u
                LEFT JOIN game_stats g ON u.user_id = g.user_id
                WHERE u.user_id = $1
                GROUP BY u.user_id, u.wordle_pts;
            """, user_id)

        if not stats:
            return None

        return {
            "wins": stats["wins"],
            "losses": stats["losses"],
            "draws": stats["draws"],
            "total_games": stats["total_games"],
            "total_wagered": stats["total_wagered"],
            "net_winnings": stats["net_winnings"],
            "win_ratio": float(stats["win_ratio"]),
            "most_played_game": stats["most_played_game"],
            "wager_rank": stats["wager_rank"],
            "wordle_pts": stats["wordle_pts"] or 0
        }