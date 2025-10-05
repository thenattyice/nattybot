from item_handlers.base_handler import BaseItemHandler
from item_handlers.consumable_handler import ConsumableHandler
from item_handlers.business_handler import BusinessHandler
from item_handlers.bundle_handler import BundleHandler

class ItemHandlerRegistry:
    def __init__(self):
        self.handlers = {}
    
    def register_handler(self, item_type: str, handler):
        # Register a handler for an item type
        self.handlers[item_type] = handler
    
    def get_handler(self, item_type: str):
        # Get the handler for an item type
        if item_type not in self.handlers:
            raise ValueError(f"No handler registered for item type: {item_type}")
        return self.handlers[item_type]
    
    def is_supported(self, item_type: str) -> bool:
        # Check if an item type has a registered handler
        return item_type in self.handlers
    
    def list_supported_types(self) -> list[str]:
        # Get all registered item types
        return list(self.handlers.keys())

# -----------------------------
# Default global registry
# -----------------------------
_default_registry = ItemHandlerRegistry()

def get_default_registry() -> ItemHandlerRegistry:
    return _default_registry


# Pre-register your handlers
_default_registry.register_handler("consumable", ConsumableHandler())
_default_registry.register_handler("business", BusinessHandler())
_default_registry.register_handler("bundle", BundleHandler())