import json

class NicknameService:
    def __init__(self, db_pool, inventory_service, item_service):
        self.db_pool = db_pool
        self.inventory_service = inventory_service
        self.item_service = item_service
        
    # Check if user has a nickname token
    async def token_validation(self, user_id) -> bool:
        user_inventory = await self.inventory_service.get_user_inventory(user_id)
        
        if "Nickname Token" in user_inventory:
            return True
        
        else:
            return False
        
    # Get nickname token item ID
    async def get_nickname_token_id(self):
        token = await self.item_service.get_item_by_name("Nickname Token")
        
        return token['id'] if token else None
    