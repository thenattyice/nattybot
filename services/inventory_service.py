import json

class InventoryService:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        
    # Get an item quantity for a specifc user by item_id
    async def get_item_quantity(self, user_id: int, item_id: int) -> int:
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT quantity FROM inventory
                WHERE user_id = $1
                AND item_id = $2;
                """, user_id, item_id)
        return result['quantity'] if result else 0  # Fixed: extract the quantity value

    # Direct update to set inventory count
    async def set_inventory_quantity(self, user_id: int, item_id: int, quantity: int):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO inventory (user_id, item_id, quantity)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, item_id)
                DO UPDATE SET quantity = $3;
            """, user_id, item_id, quantity)
            
    # Add item to inventory quantity. Handles quantity becoming zero for use in remove quantity method
    async def add_item_to_inventory(self, user_id: int, item_id: int, quantity: int, metadata: dict | None):
        async with self.db_pool.acquire() as conn:
            # Check if the item exists in inventory
            result = await conn.fetchrow("""
                SELECT quantity FROM inventory
                WHERE user_id = $1 AND item_id = $2
            """, user_id, item_id)
            
            current_quantity = result['quantity'] if result else 0
            new_quantity = current_quantity + quantity
            
            if new_quantity <= 0:
                # Delete if quantity would be zero or negative
                await conn.execute("""
                    DELETE FROM inventory
                    WHERE user_id = $1 AND item_id = $2 
                """, user_id, item_id)
            elif result:
                # Update existing record
                await conn.execute("""
                    UPDATE inventory
                    SET quantity = quantity + $3
                    WHERE user_id = $1 AND item_id = $2
                """, user_id, item_id, quantity)
            else:
                # Insert new record (only if quantity is positive)
                if quantity > 0:
                    await conn.execute("""
                        INSERT INTO inventory (user_id, item_id, quantity, metadata)
                        VALUES ($1, $2, $3, $4)
                    """, user_id, item_id, quantity, json.dumps(metadata or {}))
            
    # Remove item from inventory quantity
    async def remove_item_from_inventory(self, user_id: int, item_id: int, quantity: int):
        await self.add_item_to_inventory(user_id, item_id, -quantity)
    
    # Update metadata for inventory item
    async def update_item_metadata(self, user_id: int, item_id: int, metadata: dict):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE inventory
                SET metadata = $3
                WHERE user_id = $1 AND item_id = $2
            """, user_id, item_id, json.dumps(metadata))  # Convert dict to JSON string
            
    # Get all items in user's inventory
    async def get_user_inventory(self, user_id: int) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT shop_items.name, inventory.quantity
                FROM inventory
                JOIN shop_items ON inventory.item_id = shop_items.id
                WHERE inventory.user_id = $1
                ORDER BY shop_items.name;
            """, user_id)
        return [dict(row) for row in rows]
    
    # Get item by metadata set_code
    async def get_item_id_by_set_code(self, user_id: int, set_code: str) -> int:
        async with self.db_pool.acquire() as conn:
            set_code = await conn.fetchval("""
                SELECT item_id FROM inventory
                WHERE user_id = $1
                AND metadata->>'set_code' = $2
            """, user_id, set_code)
        return set_code