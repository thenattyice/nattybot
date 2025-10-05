from abc import ABC, abstractmethod

class BaseHandler(ABC):
    def __init__(self, economy_service, item_service, inventory_service):
        self.economy_service = economy_service
        self.item_service = item_service
        self.inventory_service = inventory_service
        
    # Check if user can purchase
    @abstractmethod
    async def can_purchase(self, user_id: int, item: dict) -> bool:
        pass
    
    # Method to add item
    @abstractmethod
    async def on_purchase(self, user_id: int, item: dict) -> dict:
        pass  