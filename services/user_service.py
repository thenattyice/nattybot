from dataclasses import dataclass

@dataclass
class UserStats:
    balance: int
    wordle_points: int
    total_wagered: int
    total_games: int
    favorite_game: str
    win_ratio: float

class UserService:
    def __init__(self, db_pool, economy_service, game_service):
        self.db_pool = db_pool
        self.economy_service = economy_service
        self.game_service = game_service
    
    async def build_user_stats(self, user_id: int) -> UserStats:
        # 1. Get the user's balance
        current_balance = await self.economy_service.get_balance(user_id)
        
        # 2. Get the user's wordle points
        wordle_pts = await self.game_service.get_user_wordle_stats(user_id)
        
        # 3. Get the user's gambling total
        gamba_total = await self.game_service.get_amount_wagered(user_id)
        
        # 4. Get the user's total game count
        total_games = await self.game_service.get_total_games(user_id)
        
        # 5. Get the user's favorite game
        fav_game = await self.game_service.get_fav_game(user_id)
        
        # 6. Get the user's game win ratio
        win_ratio = await self.game_service.calc_win_ratio(user_id)
        
        return UserStats(
        balance=current_balance,
        wordle_points=wordle_pts,
        total_wagered=gamba_total,
        total_games=total_games,
        favorite_game=fav_game,
        win_ratio=win_ratio
        )    