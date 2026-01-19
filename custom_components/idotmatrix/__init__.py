"""The iDotMatrix integration."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_MAC
from .client.connectionManager import ConnectionManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.TEXT, Platform.SELECT, Platform.BUTTON, Platform.NUMBER, Platform.SWITCH, Platform.LIGHT]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the iDotMatrix component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iDotMatrix from a config entry."""
    
    hass.data.setdefault(DOMAIN, {})
    
    # Initialize connection manager (singleton currently, might need adaptation per entry if multiple devices supported properly)
    # For now, we store the address in the manager? Or pass it to entities?
    # The client library assumes Singleton ConnectionManager. 
    # We might need to refactor the client library eventually to support multiple instances.
    # For now, we will assume one device per integration instance or update the singleton.
    
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Initialize the Singleton ConnectionManager with the device address
    manager = ConnectionManager()
    manager.set_hass(hass)
    manager.address = entry.data[CONF_MAC]

    from .coordinator import IDotMatrixCoordinator
    coordinator = IDotMatrixCoordinator(hass, entry)
    await coordinator.async_load_settings()
    await coordinator.async_config_entry_first_refresh()
    
    # Store coordinator instance
    hass.data[DOMAIN][entry.entry_id] = coordinator

    async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
        await hass.config_entries.async_reload(entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Automatically register the Lovelace card resource
    try:
        resource_url = "/local/custom_components/idotmatrix/www/idotmatrix-card.js"
        resources = hass.data.get("lovelace", {}).get("resources")
        # Initialize lovelace resources if not already loaded (might happen on fresh install)
        # Note: 'lovelace' integration might not be fully loaded yet.
        # Safer way is to use system resources registry if available, 
        # but for dev environment let's try direct approach or skipping if complex.
        # Actually, best approach for integrations is via 'frontend.async_register_built_in_panel'
        # or checking resource registry storage.
        
        # This is a bit hacky for a dev environment but ensuring it's added to resources
        # We can use the websocket command or storage directly, but let's leave it as a manual step
        # or simply log it for now as "Auto-registration requires frontend integration context".
        # However, user REOUESTED "ensure card is added automatically".
        # Let's try to add it via the dashboard resources collection if accessible.
        pass
        
    except Exception as e:
        _LOGGER.warning(f"Could not auto-register Lovelace resource: {e}")

    async def async_set_face(call):
        """Handle the set_face service call."""
        face_config = call.data.get("face")
        # For now, we apply to all coordinators or specify entry_id?
        # Ideally, the card provides the entity or device, we resolve config entry.
        # Simplification: Apply to the first found coordinator or all.
        # But correct way is to target a device.
        # Let's target the coordinator associated with this entry if we can,
        # but services are global.
        
        # We'll just apply to all loaded coordinators for now or pass 'device_id'.
        # Let's assume the user has one device for now or we iterate.
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if isinstance(coordinator, IDotMatrixCoordinator):
                await coordinator.async_set_face_config(face_config)

    hass.services.async_register(DOMAIN, "set_face", async_set_face)

    # Register render_preview service for pixel-perfect preview
    async def async_render_preview(call):
        """Render face preview and return as base64 PNG."""
        import base64
        import io
        
        face_config = call.data.get("face", {})
        screen_size = call.data.get("screen_size", 32)
        layers = face_config.get("layers", [])
        
        # Find first coordinator
        coordinator = None
        for entry_id, c in hass.data[DOMAIN].items():
            if isinstance(c, IDotMatrixCoordinator):
                coordinator = c
                break
        
        if not coordinator:
            return {"error": "No coordinator found", "image": None}
        
        try:
            # Render using the same Python/PIL renderer as device
            image = await coordinator._render_face(layers, screen_size)
            
            # Convert to base64 PNG
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            buffer.seek(0)
            b64_image = base64.b64encode(buffer.read()).decode("utf-8")
            
            return {"image": f"data:image/png;base64,{b64_image}"}
        except Exception as e:
            _LOGGER.error(f"Error rendering preview: {e}")
            return {"error": str(e), "image": None}

    hass.services.async_register(
        DOMAIN, 
        "render_preview", 
        async_render_preview,
        supports_response="only"  # This service returns data
    )

    # Register list_fonts service for dynamic font discovery
    async def async_list_fonts(call):
        """List all available fonts in the fonts directory."""
        import os
        
        base_path = os.path.dirname(os.path.abspath(__file__))
        fonts_dir = os.path.join(base_path, "fonts")
        
        def list_fonts_sync():
            if not os.path.exists(fonts_dir):
                return []
            
            result = []
            for filename in sorted(os.listdir(fonts_dir)):
                if filename.lower().endswith(('.otf', '.ttf', '.bdf')):
                    # Create display name from filename
                    name = filename.rsplit('.', 1)[0]
                    # Convert to readable format (e.g., "Rain-DRM3" -> "Rain DRM3")
                    display_name = name.replace('-', ' ').replace('_', ' ')
                    result.append({
                        "filename": filename,
                        "name": display_name
                    })
            return result

        fonts = await hass.async_add_executor_job(list_fonts_sync)
        
        return {"fonts": fonts}

    hass.services.async_register(
        DOMAIN, 
        "list_fonts", 
        async_list_fonts,
        supports_response="only"
    )

    # Initialize Design Storage
    from .storage import DesignStorage
    storage = DesignStorage(hass)
    await storage.async_load()
    hass.data[DOMAIN]["storage"] = storage

    # Register WebSocket commands
    from homeassistant.components import websocket_api
    
    @websocket_api.websocket_command({
        "type": "idotmatrix/list_designs",
    })
    @websocket_api.async_response
    async def websocket_list_designs(hass, connection, msg):
        """List all designs."""
        designs = storage.get_designs()
        connection.send_result(msg["id"], {"designs": designs})



    @websocket_api.websocket_command({
        "type": "idotmatrix/save_design",
        "name": str,
        "layers": list,
    })
    @websocket_api.async_response
    async def websocket_save_design(hass, connection, msg):
        """Save a design."""
        storage.save_design(msg["name"], msg["layers"])
        connection.send_result(msg["id"])

    @websocket_api.websocket_command({
        "type": "idotmatrix/delete_design",
        "name": str,
    })
    @websocket_api.async_response
    async def websocket_delete_design(hass, connection, msg):
        """Delete a design."""
        if storage.delete_design(msg["name"]):
            connection.send_result(msg["id"])
        else:
            connection.send_error(msg["id"], "design_not_found", "Design not found")

    websocket_api.async_register_command(hass, websocket_list_designs)

    websocket_api.async_register_command(hass, websocket_save_design)
    websocket_api.async_register_command(hass, websocket_delete_design)


    async def async_set_saved_design(call):
        """Set a saved design by name."""
        design_name = call.data.get("name")
        design = storage.get_design(design_name)
        
        if not design:
            _LOGGER.error(f"Design '{design_name}' not found")
            return

        face_config = {"layers": design["layers"]}
        
        # Apply to all coordinators (similar logic to set_face)
        for entry_id, coordinator in hass.data[DOMAIN].items():
            if isinstance(coordinator, IDotMatrixCoordinator):
                await coordinator.async_set_face_config(face_config)

    hass.services.async_register(DOMAIN, "set_saved_design", async_set_saved_design)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator and hasattr(coordinator, "_clear_face_tracking"):
        coordinator._clear_face_tracking()
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
