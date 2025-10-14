class UserService:
    def __init__(self, db_pool, economy_service, game_service):
        self.db_pool = db_pool
        self.economy_service = economy_service
        self.game_service = game_service
    
    # One method to rule them all
    async def get_full_user_game_stats(self, user_id: int):
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow("""
                WITH user_wagers AS (
                    SELECT
                        u.user_id,
                        u.balance,
                        u.wordle_pts,
                        COALESCE(SUM(g.wager), 0) AS total_wagered,
                        COALESCE(SUM(CASE WHEN g.result = 'win' THEN 1 ELSE 0 END), 0) AS wins,
                        COALESCE(SUM(CASE WHEN g.result = 'loss' THEN 1 ELSE 0 END), 0) AS losses,
                        COALESCE(SUM(CASE WHEN g.result = 'draw' THEN 1 ELSE 0 END), 0) AS draws,
                        COALESCE(COUNT(g.*), 0) AS total_games,
                        COALESCE(SUM(g.balance_change), 0) AS net_winnings,
                        COALESCE((
                            SELECT game
                            FROM game_stats
                            WHERE user_id = u.user_id
                            GROUP BY game
                            ORDER BY COUNT(*) DESC
                            LIMIT 1
                        ), 'None') AS most_played_game
                    FROM users u
                    LEFT JOIN game_stats g ON u.user_id = g.user_id
                    WHERE u.user_id = $1
                    GROUP BY u.user_id
                )
                SELECT
                    uw.*,
                    CASE
                        WHEN uw.total_wagered = 0 THEN NULL
                        ELSE DENSE_RANK() OVER (ORDER BY uw.total_wagered DESC)
                    END AS wager_rank,
                    CASE
                        WHEN (uw.wins + uw.losses) = 0 THEN 0
                        ELSE ROUND((uw.wins::numeric / (uw.wins + uw.losses)) * 100, 2)
                    END AS win_ratio
                FROM user_wagers uw;
            """, user_id)

        if not stats:
            # Return default zeros for new users
            return {
                "balance": 0,
                "wordle_pts": 0,
                "total_wagered": 0,
                "wins": 0,
                "losses": 0,
                "draws": 0,
                "total_games": 0,
                "net_winnings": 0,
                "win_ratio": 0,
                "most_played_game": "None",
                "wager_rank": None
            }

        return {
            "balance": stats["balance"] or 0,
            "wordle_pts": stats["wordle_pts"] or 0,
            "total_wagered": stats["total_wagered"] or 0,
            "wins": stats["wins"] or 0,
            "losses": stats["losses"] or 0,
            "draws": stats["draws"] or 0,
            "total_games": stats["total_games"] or 0,
            "net_winnings": stats["net_winnings"] or 0,
            "win_ratio": float(stats["win_ratio"] or 0),
            "most_played_game": stats["most_played_game"] or "None",
            "wager_rank": stats["wager_rank"]
        }