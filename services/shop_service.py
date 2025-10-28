import traceback

class ShopService():
    def __init__(self, db_pool, economy_service, item_service, inventory_service, handler_registry):
        self.db_pool = db_pool
        self.economy_service = economy_service
        self.item_service = item_service
        self.inventory_service = inventory_service
        self.handler_registry = handler_registry
    
    # Purchase validation
    async def validate_purchase(self, user_id: int, item_id: int) -> bool:
        item = await self.item_service.get_item_by_id(item_id)
        current_balance = await self.economy_service.get_balance(user_id)
        
        if item["price"] <= current_balance:
            return True
        else:
            return False
        
    async def process_transaction(self, user_id: int, item_id: int):
        # 1. Get the item
        item = await self.item_service.get_item_by_id(item_id)
        if not item:
            return {'success': False, 'error': 'Item not found'}
        
        # 2. Get the correct item handler
        handler = self.handler_registry.get_handler(
            item['item_type'],
            economy_service=self.economy_service,
            item_service=self.item_service,
            inventory_service=self.inventory_service
        )  
        
        # 3. Check that user can buy/afford item
        can_afford = await self.validate_purchase(user_id, item_id)
        can_buy = await handler.can_purchase(user_id, item)

        if not can_afford:
            return {'success': False, 'error': 'Insufficient funds'}
        
        if not can_buy:
            return {'success': False, 'error': 'Unable to purchase'} 

        # 5. Process the item via the handler
        try:
            result = await handler.on_purchase(user_id, item)
        except Exception as e:
            # If handler fails, don't take money
            print(f"Purchase handler failed: {e}")
            traceback.print_exc()
            return {'success': False, 'error': 'Purchase failed'}
        
        # 6. Take the money from the user
        await self.economy_service.remove_money_from_user(user_id, item['price'])
             
        # 7. Log the transaction
        await self.log_item_purchase(user_id, item_id, item['price'])
        
        return {"success": True, "result": result}
        
    # Function to log all of the purchases to DB and text channel
    async def log_item_purchase(self, user_id: int, item_id: int, price_paid: int):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO purchases (user_id, item_id, quantity, price_paid)
                VALUES ($1, $2, $3, $4);
            """, user_id, item_id, 1, price_paid)
    
    # Retrieve a user's purchase history
    async def get_purchase_history(self, user_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM purchases
                WHERE user_id = $1
            """, user_id)
        return [dict(row) for row in rows]
    
    # Get items available for this specific user
    async def get_available_items(self, user_id: int) -> list[dict]:
        
        # Get all items
        all_items = await self.item_service.get_all_shop_items()
        
        available = []
        for item in all_items:
            # Skip inactive items
            if not item.get('is_active', True):
                continue
            
            # If it's a business, check if user already owns it
            if item['item_type'] == 'business':
                owns_it = await self.inventory_service.get_item_quantity(user_id, item['id'])
                if owns_it > 0:
                    continue  # Skip - they already own this business
            
            available.append(item)
        
        return available