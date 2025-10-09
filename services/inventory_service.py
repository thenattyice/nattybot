class InventoryService:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        
    # Get an item quantity for a specifc user by item_id
    async def get_item_quantity(self, user_id: int, item_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT quantity FROM inventory
                WHERE user_id = $1
                AND item_id = $2;
                """, user_id, item_id)
        return result if result else 0

    # Direct update to set inventory count
    async def set_inventory_quantity(self, user_id: int, item_id: int, quantity: int):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO inventory (user_id, item_id, quantity)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, item_id)
                DO UPDATE SET quantity = $3;
            """, user_id, item_id, quantity)
            
    # Add item to inventory quantity. Handles quantity becomig zero for use in remove quantity method
    async def add_item_to_inventory(self, user_id: int, item_id: int, quantity: int):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO inventory (user_id, item_id, quantity)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, item_id)
                DO UPDATE SET quantity = inventory.quantity + $3;
            """, user_id, item_id, quantity)
            
        current_quantity = await self.get_item_quantity(user_id, item_id)
        
        if current_quantity <= 0:
            await conn.execute("""
                DELETE FROM inventory
                WHERE user_id = $1
                AND item_id = $2 
            """, user_id, item_id)
            
    # Remove item from invetory quantity
    async def remove_item_from_inventory(self, user_id: int, item_id: int, quantity: int):
        await self.add_item_to_inventory(user_id, item_id, -quantity)
    
    # Update metadata for inventory item
    async def update_item_metadata(self, user_id: int, item_id: int, metadata: dict):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE inventory
                SET metadata = $3
                WHERE user_id = $1 AND item_id = $2
            """, user_id, item_id, metadata)
            
    # Get all items in user's inventory
    async def get_user_inventory(self, user_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT items.name, inventory.quantity
                FROM inventory
                JOIN items ON inventory.item_id = items.item_id
                WHERE inventory.user_id = $1
                ORDER BY items.name;
            """, user_id)
        return [dict(row) for row in rows]