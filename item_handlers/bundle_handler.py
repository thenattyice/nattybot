from item_handlers.base_handler import BaseHandler

class BundleHandler(BaseHandler):
    def __init__(self, economy_service, item_service, inventory_service):
        self.economy_service = economy_service
        self.item_service = item_service
        self.inventory_service = inventory_service
        
    async def can_purchase(self, user_id: int, item: dict) -> bool:
        return True
    
    async def on_purchase(self, user_id: int, item: dict) -> dict:
        # Get the bundle contents
        metadata = item.get('metadata', {})
        contents = metadata.get('bundle_contents', [])
        
        if not contents:
            return {
                'success': False,
                'error': 'Bundle config is missing'
            }
        
        added_items = []
        
        for content in contents:
            item_name = content.get('item_name')
            quantity = content.get('quantity', 1)
            
            if not item_name:
                continue
            
            target_item = await self.item_service.get_item_by_name(item_name)
            
            if not target_item:
                continue
            
            await self.inventory_service.add_item_to_inventory(user_id, target_item['id'], quantity)
            
            added_items.append(f"{quantity}x {item_name}")
            
        if not added_items:
            return {
                'success': False,
                'error': 'No valid items found in bundle'
            }
        
        # Build success message
        items_text = ", ".join(added_items)
        
        return {
            'success': True, 
            'message': f"Bundle opened! Added to inventory: {items_text}"
        }