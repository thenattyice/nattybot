import json

# Item Service Layer
class ItemService:
    def __init__(self, db_pool):
        self.db_pool = db_pool
        
    # Get all details in a row for a specific item via ID
    async def get_item_by_id(self, item_id: int) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM shop_items WHERE id = $1;",
                item_id)
        return dict(row) if row else None
    
    # Get item by name
    async def get_item_by_name(self, name: str) -> dict | None:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM shop_items WHERE name = $1;",
                name)
        return dict(row) if row else None
    
    # Get all items in the shop - active only
    async def get_all_active_items(self) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM shop_items WHERE is_Active = TRUE;")
        return [dict(row) for row in rows]
    
    # Get all items in the shop - no filters
    async def get_all_items(self) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM shop_items;")
        return [dict(row) for row in rows]
    
    # Get collectble items (MTG packs) - active only
    async def get_all_collectible_items(self) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM shop_items WHERE is_Active = TRUE AND item_type = 'collectible';")
        return [dict(row) for row in rows]
    
    # Get all non-collectble items - active only
    async def get_all_shop_items(self) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM shop_items WHERE is_Active = TRUE AND item_type != 'collectible';")
        return [dict(row) for row in rows]
    
    # Add an item to the shop table for purchase in the shop
    async def add_shop_item(self, name: str, description: str, price: int, item_type: str, is_active: bool, metadata: dict | None = None) -> dict:
        if price <= 0:
            raise ValueError("Price must be positive")
        
        if metadata is None:
            metadata = {}
        
        async with self.db_pool.acquire() as conn:
            # Convert dict to JSON string
            metadata_json = json.dumps(metadata)
            
            row = await conn.fetchrow("""
                INSERT INTO shop_items (name, description, price, item_type, is_active, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (name) DO NOTHING
                RETURNING *;
            """, name, description, price, item_type, is_active, metadata_json)
            
            # Return the row as a dict, or empty dict if conflict occurred
            return dict(row) if row else {}
        
    # Log items as they're used
    async def log_item_usage(self, user_id: int, item_id: int, usage_type: str, result_data: dict | None = None):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO item_usage (user_id, item_id, usage_type, quantity, result_data)
                VALUES ($1, $2, $3, 1, $4)
            """, user_id, item_id, usage_type, result_data)
            
    # Update item name
    async def update_item_name(self, item_id: int, name: str):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE shop_items
                SET name = $2
                WHERE id = $1
            """, item_id, name)
        
    # Remove item from shop
    async def remove_item(self, item_id: int):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM shop_items
                WHERE id = $1
            """, item_id)
            
    # Get item by metadata set_code
    async def get_item_by_set_code(self, set_code: str) -> dict:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
            SELECT id, name, price, metadata
            FROM shop_items
            WHERE item_type = 'collectible'
            AND metadata->>'set_code' = $1
            AND is_active = TRUE
        """, set_code)
        return dict(row) if row else None