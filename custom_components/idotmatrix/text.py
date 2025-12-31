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
        IDotMatrixFunText(coordinator, entry),
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

class IDotMatrixFunText(IDotMatrixEntity, TextEntity):
    """Representation of the Fun Text input (Animates words with random colors)."""

    _attr_icon = "mdi:party-popper"
    _attr_name = "Fun Text"
    
    @property
    def unique_id(self) -> str:
        return f"{self._mac}_fun_text"

    @property
    def native_value(self) -> str | None:
        """Return the value reported by the text entity."""
        # We allow this to read back the main text, or maybe separate?
        # For simplicity, let's share the same reading source so it stays in sync.
        return self.coordinator.text_settings.get("current_text", "")

    async def async_set_value(self, value: str) -> None:
        """Change the text value with animation."""
        # Use simple default text if empty, similar to user script logic
        input_text = value if value else "How did I end up here?"
        
        # Spawn the animation task
        self.hass.async_create_task(self._animate_text(input_text))

    async def _animate_text(self, text: str):
        """Run the animation loop."""
        import asyncio
        import random
        
        words = text.split()
        palette = [
            [255, 0, 0],
            [0, 255, 0],
            [0, 120, 255],
            [160, 0, 255],
            [255, 255, 255],
            [255, 120, 0],
            [255, 0, 170],
            [0, 255, 220]
        ]
        
        for word in words:
            color = random.choice(palette)
            
            # Update Settings
            self.coordinator.text_settings["color"] = color
            self.coordinator.text_settings["current_text"] = word
            
            # Send to Device
            await self.coordinator.async_update_device()
            
            # Delay (Adjustable, Default 400ms)
            delay = self.coordinator.text_settings.get("fun_text_delay", 0.4)
            await asyncio.sleep(delay)
            
        # Final update to ensure state is consistent (optional config choice)
        # Maybe show the full sentence at the end? Or leave the last word?
        # User script leaves the last word. We'll stick to that "exactly same thing".

