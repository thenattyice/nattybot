class UserService:
    def __init__(self, db_pool, economy_service):
        self.db_pool = db_pool
        self.db_pool = economy_service
    
    async def get_user_stats(self, user_id: int):
        # 1. Get the user's balance
        current_balance = await self.economy_service.get_balance(user_id)
        
        # 2. Get the user's wordle points
        
        # 3. Get the user's gambling total
        
        # 4. Get the user's total game count
        
        # 5. Get the user's favorite game
        
        
                