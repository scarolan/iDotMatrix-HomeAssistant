"""Text platform for iDotMatrix."""
from __future__ import annotations

import logging

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import IDotMatrixEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the iDotMatrix text."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        IDotMatrixText(coordinator, entry),
    ])

class IDotMatrixText(IDotMatrixEntity, TextEntity):
    """Representation of the Text input."""

    _attr_icon = "mdi:form-textbox"
    _attr_name = "Display Text"
    
    @property
    def unique_id(self) -> str:
        return f"{self._mac}_display_text"

    @property
    def native_value(self) -> str | None:
        """Return the value reported by the text entity."""
        return self.coordinator.text_settings.get("current_text", "")

    async def async_set_value(self, value: str) -> None:
        """Change the text value."""
        self.coordinator.text_settings["current_text"] = value
        
        # Trigger update (sends command to device)
        await self.coordinator.async_update_device()
        
        self.async_write_ha_state() # Update HA state immediately
