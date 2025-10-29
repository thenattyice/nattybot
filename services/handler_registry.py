import inspect

from item_handlers.consumable_handler import ConsumableHandler
from item_handlers.business_handler import BusinessHandler
from item_handlers.bundle_handler import BundleHandler
from item_handlers.mtg_collectible_handler import MTGCollectibleHandler

class ItemHandlerRegistry:
    def __init__(self):
        self.handler_factories = {}
        self._handler_cache = {}

    #Register a factory function for an item type
    def register_handler(self, item_type: str, factory):
        
        self.handler_factories[item_type] = factory
        # Clear cache if re-registering
        if item_type in self._handler_cache:
            del self._handler_cache[item_type]
    
    #Return a cached handler instance, or create it if missing
    def get_handler(self, item_type: str, **kwargs):
        if item_type in self._handler_cache:
            return self._handler_cache[item_type]

        if item_type not in self.handler_factories:
            raise ValueError(f"No handler registered for item type: {item_type}")

        factory = self.handler_factories[item_type]

        # Filter kwargs to only what the factory expects
        sig = inspect.signature(factory)
        filtered_kwargs = {
            k: v for k, v in kwargs.items() if k in sig.parameters
        }

        handler = factory(**filtered_kwargs)
        self._handler_cache[item_type] = handler
        return handler

    def is_supported(self, item_type: str) -> bool:
        return item_type in self.handler_factories

    def list_supported_types(self) -> list[str]:
        return list(self.handler_factories.keys())

# ------------------------------------
# Default global registry setup
# ------------------------------------
_default_registry = ItemHandlerRegistry()

def get_default_registry() -> ItemHandlerRegistry:
    return _default_registry

# Register handler factories (not instances)
_default_registry.register_handler(
    "consumable",
    lambda economy_service, item_service, inventory_service: ConsumableHandler(
        economy_service, item_service, inventory_service
    )
)
_default_registry.register_handler(
    "business",
    lambda economy_service, item_service, inventory_service: BusinessHandler(
        economy_service, item_service, inventory_service
    )
)
_default_registry.register_handler(
    "bundle",
    lambda economy_service, item_service, inventory_service: BundleHandler(
        economy_service, item_service, inventory_service
    )
)
_default_registry.register_handler(
    "collectible",
    lambda economy_service, item_service, inventory_service, mtg_service: MTGCollectibleHandler(
        economy_service, item_service, inventory_service, mtg_service
    )
)