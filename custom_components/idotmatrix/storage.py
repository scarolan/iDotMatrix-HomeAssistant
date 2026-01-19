from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from typing import Dict, Any, Optional
import logging

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY = "idotmatrix_designs"

class DesignStorage:
    def __init__(self, hass: HomeAssistant):
        self._hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: Optional[Dict[str, Any]] = None

    async def async_load(self):
        """Load data from storage."""
        data = await self._store.async_load()
        if data is None:
            self._data = {"designs": {}}
        else:
            self._data = data

    @callback
    def _async_schedule_save(self):
        """Schedule saving the data."""
        self._store.async_delay_save(self._data_to_save, 1.0)

    @callback
    def _data_to_save(self):
        """Return data to save."""
        return self._data

    def get_designs(self) -> Dict[str, Any]:
        """Return all saved designs."""
        return self._data.get("designs", {})

    def get_design(self, name: str) -> Optional[Dict[str, Any]]:
        """Return a specific design by name."""
        return self._data.get("designs", {}).get(name)

    def save_design(self, name: str, layers: list) -> None:
        """Save a design."""
        if self._data is None:
            self._data = {"designs": {}}
            
        self._data["designs"][name] = {
            "name": name,
            "layers": layers,
            "updated_at": None # Could add timestamp if needed
        }
        self._async_schedule_save()

    def delete_design(self, name: str) -> bool:
        """Delete a design."""
        if self._data is None or name not in self._data.get("designs", {}):
            return False
            
        del self._data["designs"][name]
        self._async_schedule_save()
        return True
