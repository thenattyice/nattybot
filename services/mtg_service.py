import aiohttp
import asyncio
import random
import traceback
from typing import Tuple, List, Dict

class MtgService:
    def __init__(self, db_pool, inventory_service, item_service):
        self.db_pool = db_pool
        self.inventory_service = inventory_service
        self.item_service = item_service
    
    # Get all cards from a set
    async def get_cards_from_set(self, set_code: str):
        url = f"https://api.scryfall.com/cards/search?q=set:{set_code}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                return data["data"]
    
    # Add a set to the DB table
    async def add_set_to_db(self, set_code: str):
        try:
            url = f"https://api.scryfall.com/sets/{set_code}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    set_data = await response.json()
            
            set_name = set_data["name"]

            async with self.db_pool.acquire() as conn:
                status = await conn.execute("""
                    INSERT INTO mtg_sets (set_code, set_name)
                    VALUES ($1, $2)
                    ON CONFLICT (set_code) DO NOTHING;
                """, set_code, set_name)
            
            # status will look like "INSERT 0 1" or "INSERT 0 0"
            if status.endswith("1"):
                return {'success': True, 'message': f"Set `{set_name}` ({set_code}) added successfully!"}
            else:
                return {'success': False, 'error': f"Set `{set_name}` ({set_code}) already exists."}
        except Exception:
            traceback.print_exc()
            return {'success': False, 'error': 'Unable to add set'}
    
    # Get all MTG sets    
    async def get_all_sets(self):
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, set_name, set_code FROM mtg_sets;")
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
    
    # Validate that user owns a pack
    async def owns_packs_validation(self, user_id: int) -> bool:
        async with self.db_pool.acquire() as conn:
            owns_packs = await conn.fetchrow("""
                SELECT s.name
                FROM inventory i
                JOIN shop_items s ON s.id = i.item_id
                WHERE i.user_id = $1
                AND s.name = 'MTG Booster Pack'
                AND i.quantity > 0;
            """, user_id)
        return owns_packs is not None
    
    # Remove the pack from user
    async def remove_pack_from_user(self, target_user_id: int):
        item = await self.item_service.get_item_by_name("MTG Booster Pack")
        
        pack_item_id = item['id']
        
        await self.inventory_service.remove_item_from_inventory(target_user_id, pack_item_id, 1)
    
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