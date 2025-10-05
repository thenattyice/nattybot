from item_handlers.base_handler import BaseHandler

class ConsumableHandler(BaseHandler):
    def __init__(self, economy_service, item_service, inventory_service):
        self.economy_service = economy_service
        self.item_service = item_service
        self.inventory_service = inventory_service
        
    async def can_purchase(self, user_id, item):
        return True
    
    async def on_purchase(self, user_id: int, item: dict) -> dict:
        await self.inventory_service.add_item_to_inventory(user_id, item['id'], 1)
        return {'success': True}