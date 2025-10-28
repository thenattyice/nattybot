import json

class MTGCollectibleHandler:
    def __init__(self, economy_service, item_service, inventory_service, mtg_service):
        self.economy_service = economy_service
        self.item_service = item_service
        self.inventory_service = inventory_service
        self.mtg_service = mtg_service
    
    async def can_purchase(self, user_id: int, item: dict) -> bool:
        # MTG items can always be purchased (no ownership restrictions)
        return True
    
    async def on_purchase(self, user_id: int, item: dict) -> dict:
        # Extract metadata
        metadata = item['metadata']
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        
        set_code = metadata['set_code']
        quantity = metadata['quantity']  # 1 for pack, 30 for box
        
        # Add to inventory with set_code in metadata
        await self.inventory_service.add_item_to_inventory(
            user_id, 
            item['id'], 
            quantity,
            metadata={'set_code': set_code}
        )
        
        return {
            'set_code': set_code,
            'quantity': quantity
        }