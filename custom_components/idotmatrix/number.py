"""Number platform for iDotMatrix."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import EntityCategory

from .const import DOMAIN
from .entity import IDotMatrixEntity

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the iDotMatrix number platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        IDotMatrixTextSpeed(coordinator, entry),
        IDotMatrixTextSpacing(coordinator, entry),
        IDotMatrixTextSpacingVertical(coordinator, entry),
        IDotMatrixTextBlur(coordinator, entry),
        IDotMatrixTextFontSize(coordinator, entry),
    ])

class IDotMatrixTextFontSize(IDotMatrixEntity, NumberEntity):
    """Representation of the Text Font Size control."""

    _attr_icon = "mdi:format-size"
    _attr_name = "Text Font Size"
    _attr_native_min_value = 6
    _attr_native_max_value = 64
    _attr_native_step = 1
    _attr_entity_category = EntityCategory.CONFIG
    
    @property
    def unique_id(self) -> str:
        return f"{self._mac}_text_font_size"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.text_settings.get("font_size", 10)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self.coordinator.text_settings["font_size"] = int(value)
        await self.coordinator.async_update_device()
        self.async_write_ha_state()

class IDotMatrixTextBlur(IDotMatrixEntity, NumberEntity):
    """Representation of the Text Blur control."""

    _attr_icon = "mdi:blur"
    _attr_name = "Text Sharpness/Blur"
    _attr_native_min_value = 0
    _attr_native_max_value = 5
    _attr_native_step = 1
    _attr_entity_category = EntityCategory.CONFIG
    
    @property
    def unique_id(self) -> str:
        return f"{self._mac}_text_blur"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.text_settings.get("blur", 5)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self.coordinator.text_settings["blur"] = int(value)
        await self.coordinator.async_update_device()
        self.async_write_ha_state()

class IDotMatrixTextSpeed(IDotMatrixEntity, NumberEntity):
    """Representation of the Text Speed number."""

    _attr_icon = "mdi:speedometer"
    _attr_name = "Text Speed"
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_entity_category = EntityCategory.CONFIG
    
    @property
    def unique_id(self) -> str:
        return f"{self._mac}_text_speed"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.coordinator.text_settings.get("speed", 80)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self.coordinator.text_settings["speed"] = int(value)
        await self.coordinator.async_update_device()
        self.async_write_ha_state()

class IDotMatrixTextSpacing(IDotMatrixEntity, NumberEntity):
    """Representation of the Text Horizontal Spacing number."""

    _attr_icon = "mdi:arrow-expand-horizontal"
    _attr_name = "Text Horizontal Spacing"
    _attr_native_min_value = -8
    _attr_native_max_value = 20
    _attr_native_step = 1
    _attr_entity_category = EntityCategory.CONFIG
    
    @property
    def unique_id(self) -> str:
        return f"{self._mac}_text_spacing"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.coordinator.text_settings.get("spacing", 1)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self.coordinator.text_settings["spacing"] = int(value)
        await self.coordinator.async_update_device()
        self.async_write_ha_state()

class IDotMatrixTextSpacingVertical(IDotMatrixEntity, NumberEntity):
    """Representation of the Text Vertical Spacing number."""

    _attr_icon = "mdi:arrow-expand-vertical"
    _attr_name = "Text Vertical Spacing"
    _attr_native_min_value = -8
    _attr_native_max_value = 20
    _attr_native_step = 1
    _attr_entity_category = EntityCategory.CONFIG
    
    @property
    def unique_id(self) -> str:
        return f"{self._mac}_text_spacing_y"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.text_settings.get("spacing_y", 1)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        self.coordinator.text_settings["spacing_y"] = int(value)
        await self.coordinator.async_update_device()
        self.async_write_ha_state()
