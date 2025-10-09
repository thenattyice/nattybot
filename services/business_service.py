from collections import defaultdict

class BusinessService():
    def __init__(self, db_pool, economy_service):
        self.db_pool = db_pool
        self.economy_service = economy_service
    
    # Get all businesses for a specified user
    async def get_specific_users_businesses(self, target_user_id: int):
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
            SELECT s.id AS item_id, s.name
            FROM inventory i
            JOIN item_shop s ON s.id = i.item_id 
            WHERE i.user_id = $1
            AND s.item_type = 'business';
            """, target_user_id)
        return rows
    
    # Get all of the businesses per user from the shop
    async def get_businesses_per_user(self):
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
            SELECT i.user_id, s.name, (s.metadata->>'daily_payout')::int AS daily_payout
            FROM inventory i
            JOIN shop_items s ON s.id = i.item_id 
            WHERE s.item_type = 'business'
            AND s.metadata->>'daily_payout' IS NOT NULL
            AND (s.metadata->>'daily_payout')::int > 0
            """)
        return rows
    
    async def calculate_user_payouts(self):
        rows = await self.get_businesses_per_user()
        
        payouts_dict = defaultdict(lambda: {"total": 0, "breakdown": []})
        
        for row in rows:
            user_id = row["user_id"]
            biz_name = row["name"]
            daily_payout = row["daily_payout"]
            
            payouts_dict[user_id]["total"] += daily_payout
            payouts_dict[user_id]["breakdown"].append((biz_name, daily_payout))
            
        return dict(payouts_dict)
            
    async def execute_payouts(self):
        payouts = await self.calculate_user_payouts()
        
        if not payouts:
            return None
        
        payout_records = []
        
        for user_id, data in payouts.items():
            total = data["total"]
            breakdown = data["breakdown"]
            
            await self.economy_service.add_money_to_user(user_id, total)
            
            payout_records.append({
                "user_id": user_id,
                "total": total,
                "breakdown": breakdown
            })
            
        return payout_records