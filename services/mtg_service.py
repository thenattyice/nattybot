import aiohttp
import asyncio
import random
import traceback
import json
from typing import Tuple, List, Dict

class MtgService:
    def __init__(self, db_pool, inventory_service, item_service):
        self.db_pool = db_pool
        self.inventory_service = inventory_service
        self.item_service = item_service
    
    # Get all cards from a set
    async def get_cards_from_set(self, set_code: str):
        url = f"https://api.scryfall.com/cards/search?q=set:{set_code}"
        cards = []
        async with aiohttp.ClientSession() as session:
            while url:
                async with session.get(url) as response:
                    data = await response.json()
                    cards.extend(data.get("data", []))
                    url = data.get("next_page") if data.get("has_more") else None
        return cards
    
    # Add a set to the DB table
    async def add_set_to_db(self, set_code: str, pack_price: int, box_price: int):
        try:
            # Fetch set info from Scryfall
            url = f"https://api.scryfall.com/sets/{set_code}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    set_data = await response.json()

            set_name = set_data["name"]

            async with self.db_pool.acquire() as conn:
                async with conn.transaction():  # All DB ops happen in one transaction

                    # Insert into mtg_sets and get the id
                    set_id = await conn.fetchval("""
                        INSERT INTO mtg_sets (set_code, set_name, pack_price, box_price)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (set_code) DO NOTHING
                        RETURNING id;
                    """, set_code, set_name, pack_price, box_price)

                    if not set_id:
                        return {'success': False, 'error': f"Set `{set_name}` ({set_code}) already exists."}

                    # Create the pack shop item
                    await conn.execute("""
                        INSERT INTO shop_items (name, description, price, item_type, metadata, is_active)
                        VALUES ($1, $2, $3, 'collectible', $4, TRUE)
                    """,
                        f"{set_name} - Pack",
                        f"Single booster pack from {set_name}",
                        pack_price,
                        json.dumps({
                            "set_id": set_id,
                            "set_code": set_code,
                            "product_type": "pack",
                            "quantity": 1
                        })
                    )

                    # Create the box shop item
                    await conn.execute("""
                        INSERT INTO shop_items (name, description, price, item_type, metadata, is_active)
                        VALUES ($1, $2, $3, 'collectible', $4, TRUE)
                    """,
                        f"{set_name} - Box",
                        f"Sealed booster box from {set_name} (30 packs)",
                        box_price,
                        json.dumps({
                            "set_id": set_id,
                            "set_code": set_code,
                            "product_type": "box",
                            "quantity": 30
                        })
                    )

            return {'success': True, 'message': 'Set successfully added!'}

        except Exception:
            traceback.print_exc()
            return {'success': False, 'error': 'Unable to add set'}
    
    # Get all MTG sets    
    async def get_all_sets(self):
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, set_name, set_code, pack_price, box_price FROM mtg_sets;")
        return [dict(row) for row in rows]  # Convert to list of dicts
    
    # Get specific set by code
    async def get_set_by_code(self, set_code: str):
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT set_name FROM mtg_sets WHERE set_code = $1;", set_code)
        return dict(row) if row else None
    
    # Get price of cards 
    def get_card_price(self, card):  # Not async - no await needed
        is_foil = random.random() < (1/6)  # 1 in 6 chance for a foil card
        
        def parse_price(price_str):
            float_price = float(price_str)
            if float_price < 0.50:
                return 1
            elif float_price >= 0.50 and float_price < 1.0:
                return 1
            else:
                return float_price

        usd = parse_price(card["prices"]["usd"]) if card["prices"]["usd"] else 1.0
        usd_foil = parse_price(card["prices"]["usd_foil"]) if card["prices"]["usd_foil"] else 1.0

        if is_foil and usd_foil > 0:
            return round(usd_foil), True
        else:
            return round(usd), False
    
    # Validate that user owns packs for the set
    async def user_owns_set_packs(self, user_id: int, set_code: str, requested_open_count: int):
        async with self.db_pool.acquire() as conn:
            owns_packs = await conn.fetchrow("""
                SELECT i.quantity
                FROM inventory i
                JOIN shop_items si ON si.id = i.item_id
                WHERE i.user_id = $1
                AND i.quantity >= $2
                AND si.metadata->>'set_code' = $3
            """, user_id, requested_open_count, set_code)
        return owns_packs is not None
    
    # Get all packs and sets owned by user
    async def get_user_mtg_packs(self, user_id):
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    inventory.item_id,
                    SUM(inventory.quantity) as total_quantity,
                    shop_items.metadata->>'set_code' as set_code,
                    shop_items.name as set_name
                FROM inventory
                JOIN shop_items ON inventory.item_id = shop_items.id
                WHERE inventory.user_id = $1
                AND shop_items.item_type = 'collectible'
                AND shop_items.metadata ? 'set_code'
                GROUP BY shop_items.metadata->>'set_code', shop_items.name, inventory.item_id
                HAVING SUM(inventory.quantity) > 0
            """, user_id)
        return [dict(row) for row in rows]
    
    # Get item_id by set_code
    
    # Open a pack and pay the user    
    async def open_pack(self, set_code: str) -> Tuple[List[Dict], float]:
        cards = await self.get_cards_from_set(set_code)
        
        commons = [card for card in cards if card["rarity"] == "common"]
        uncommons = [card for card in cards if card["rarity"] == "uncommon"]
        mythics_rares = [card for card in cards if card["rarity"] in ["rare", "mythic"]]
        
        pack = []
        
        pack.extend(random.sample(commons, 9))
        pack.extend(random.sample(uncommons, 3))
        pack.extend(random.sample(mythics_rares, 2))
        
        total = 0
        pack_with_prices = []
        
        for card in pack:
            price, foil = self.get_card_price(card)  # No await - it's not async
            card_info = {
                "name": card["name"],
                "price": price,
                "foil": foil,
                "rarity": card["rarity"]
            }
            pack_with_prices.append(card_info)
            total += price
        
        return pack_with_prices, total