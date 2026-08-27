import traceback
import discord

class GameService:
    def __init__(self, db_pool, economy_service):
        self.db_pool = db_pool
        self.economy_service = economy_service
    
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
    
    # Houses the embed templates and selects the right one based on provided logic
    async def embed_factory(self, game: str, embed_type: str, bet: int):
        # Embed types: Win, Loss, Game Start
        if embed_type == "start":
            embed = discord.Embed(
                title=f"🎮 Natty Games: {game} 🎮",
                description=f"",
                color=discord.Color.green()
            )
        
        result_embed = ()
    
    # Process all game results. Handles logging and economy
    async def game_result_handler(self, win: bool, user_id, bet: int, game: str):
        if win:
            balance_change = bet
            game_result = "win"

        else:
            balance_change = -bet
            game_result = "loss"
            
        await self.economy_service.add_money_to_user(user_id, balance_change)
        new_balance = await self.economy_service.get_balance(user_id)
        
        # Log the game results
        try:
            await self.log_game_result(user_id, game, game_result, bet, balance_change)
        except Exception as e:
            print(f"[NattyGames] {game} - Error logging {game_result}: {e}")
            traceback.print_exc()
            
        return new_balance