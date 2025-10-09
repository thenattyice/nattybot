class EconomyService:
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    # Method for setting a users money in DB
    async def set_user_money(self, target_user_id: int, amount: int):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, balance)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET balance = $2;
            """, target_user_id, amount)
    
    # Method for adding money to users in DB
    async def add_money_to_user(self, target_user_id: int, amount: int):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (user_id, balance)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET balance = users.balance + $2;
            """, target_user_id, amount)
        
        current_balance = await self.get_balance(target_user_id)
        
        if current_balance < 0:
            await self.set_user_money(target_user_id, 0)
            
    # Method for removing money from users in DB
    async def remove_money_from_user(self, target_user_id: int, amount: int):
        await self.add_money_to_user(target_user_id, -amount)
            
    # Method to check user balance
    async def get_balance(self, user_id: int):
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchrow("SELECT balance FROM users WHERE user_id = $1", user_id)
            return result['balance'] if result else 0
        
    # Method for pulling the leaderboard data
    async def get_leaderboard(self) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT RANK() OVER (ORDER BY balance DESC)
                AS rank, user_id, balance
                FROM users;""")
        return [dict(row) for row in rows]
    
    # Bet validation method
    async def bet_validation(target_user_id: int, bet: int) -> bool:
        current_balance = await self.get_balance(target_user_id)
        
        # Bet amount validations
        if bet > current_balance:
            print("Validation Failure: bet > current_balance")
            return False
            
        if bet <= 0:
            print("Validation Failure: bet <= 0")
            return False
        
        if current_balance <= 0:
            print("Validation Failure: current_balance <= 0")
            return False
        
        return True