"""DataUpdateCoordinator for iDotMatrix."""
from __future__ import annotations

import logging
import asyncio
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN
from .client.connectionManager import ConnectionManager
from .client.modules.text import Text
from .client.modules.image import Image as IDMImage
from .client.modules.clock import Clock


import os
import tempfile
from PIL import Image, ImageDraw, ImageFont

from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = "idotmatrix_settings_"

class IDotMatrixCoordinator(DataUpdateCoordinator):
    """Class to manage fetching iDotMatrix data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )
        self.entry = entry
        self._store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}{entry.entry_id}")
        
        # Shared settings for Text entity
        self.text_settings = {
            "current_text": "",   # The actual text content
            "font": "Rain-DRM3.otf",
            "animation_mode": 1,  # Marquee
            "speed": 80,
            "color_mode": 1,      # Single Color
            "color": [255, 0, 0], # Red default
            "spacing": 1,         # Horizontal Spacing (pixels)
            "spacing_y": 1,       # Vertical Spacing (pixels)
            "proportional": True, # Use proportional font rendering
            "blur": 5,            # Text Blur/Antialiasing (0=Sharp, 5=Smooth)
            "font_size": 10,      # Font Size (pixels)
            "multiline": False,   # Wrap text as image
            "screen_size": 32,    # 32x32 or 16x16
            "brightness": 128,    # 0-255 (mapped to 5-100)
            "clock_style": 0,     # Default style index
            "clock_date": True,   # Show date
            "clock_format": "24h",# 12h or 24h
            "fun_text_delay": 0.4,# Fun Text delay in seconds
            "autosize": False,    # Auto-scale font to fit screen
        }

    async def async_load_settings(self) -> None:
        """Load settings from storage."""
        if (data := await self._store.async_load()):
            _LOGGER.debug(f"Loaded persist settings: {data}")
            self.text_settings.update(data)

    async def async_save_settings(self) -> None:
        """Save settings to storage."""
        await self._store.async_save(self.text_settings)

    async def _async_update_data(self):
        """Fetch data from the device."""
        return {"connected": True}

    async def async_update_device(self) -> None:
        """Send current configuration to the device."""
        text = self.text_settings.get("current_text", "")
        settings = self.text_settings
        
        if text:
            # Render Text
            if settings.get("multiline", False):
                await self._set_multiline_text(text, settings)
            else:
                # Standard Scroller
                await Text().setMode(
                    text=text,
                    font_size=int(settings.get("font_size", 10)), 
                    font_path=settings.get("font"),
                    text_mode=settings.get("animation_mode", 1),
                    speed=settings.get("speed", 80),
                    text_color_mode=settings.get("color_mode", 1),
                    text_color=tuple(settings.get("color", (255, 0, 0))),
                    text_bg_mode=0,
                    text_bg_color=(0, 0, 0),
                    spacing=settings.get("spacing", 1),
                    proportional=settings.get("proportional", True)
                )
        else:
            # Render Clock (Default fallback)
            # Use self.text_settings for clock config
            # Retrieve color and format
            c = settings.get("color", [255, 0, 0])
            h24 = settings.get("clock_format", "24h") == "24h"
            
            style = settings.get("clock_style", 0)
            show_date = settings.get("clock_date", True)
            
                
            await Clock().setMode(
                style=style,
                visibleDate=show_date,
                hour24=h24,
                r=c[0],
                g=c[1],
                b=c[2]
            )
            
        # Notify listeners to update UI states
        self.async_set_updated_data(self.data)
        
        # Save persistence
        await self.async_save_settings()

    async def _set_multiline_text(self, text: str, settings: dict) -> None:
        """Generate an image from text and upload it."""
        screen_size = int(settings.get("screen_size", 32))
        font_name = settings.get("font")
        color = tuple(settings.get("color", (255, 0, 0)))
        spacing = int(settings.get("spacing", 1))
        spacing_y = int(settings.get("spacing_y", 1))
        blur = int(settings.get("blur", 5))
        
        # Resolve font path
        # Note: __file__ here is coordinator.py, so we need to adjust path logic
        base_path = os.path.dirname(os.path.abspath(__file__))
        fonts_dir = os.path.join(base_path, "fonts")
        font_path = os.path.join(fonts_dir, "Rain-DRM3.otf")
        
        if font_name:
            if not os.path.isabs(font_name):
                 potential = os.path.join(fonts_dir, font_name)
                 if os.path.exists(potential):
                     font_path = potential
            elif os.path.exists(font_name):
                font_path = font_name
                
        # Determine font size and max scanning range if autosize is on
        initial_font_size = int(settings.get("font_size", 10))
        target_font_size = initial_font_size
        
        if settings.get("autosize", False):
            # Start from user's size or 32, whichever is reasonable, and shrink until fit
            # Or always start large? Let's start from current size and shrink, 
            # OR start from 32 (max) to find biggest possible fit? "Perfectly" usually means "Maximize".
            # Let's try to Maximize: Start at 32 (or screen_size) down to 6.
            start_size = screen_size
            end_size = 6
        else:
            # Single pass
            start_size = initial_font_size
            end_size = initial_font_size

        font_path_to_use = font_path

        # Iterative resizing loop
        for s in range(start_size, end_size - 1, -1):
            target_font_size = s
            try:
                if font_path_to_use.lower().endswith(".bdf"):
                     font = ImageFont.load(font_path_to_use)
                     # BDF fonts are fixed size, autosize won't work well unless we pick different files.
                     # For now, skip autosize on BDF or just use it as is.
                else:
                     font = ImageFont.truetype(font_path_to_use, s)
            except:
                font = ImageFont.load_default()

            # Pixel-based Word Wrapping (Simulated for check)
            words = text.split(' ')
            lines = []
            current_line = []
            
            def get_word_width(word):
                if not word: return 0
                w = 0
                for i, char in enumerate(word):
                    bbox = font.getbbox(char)
                    char_w = (bbox[2] - bbox[0]) if bbox else font.getlength(char)
                    w += char_w + spacing
                return w - spacing
            
            # Recalculate space width for this font size
            try:
                space_bbox = font.getbbox(" ")
                space_w = (space_bbox[2] - space_bbox[0]) if space_bbox else font.getlength(" ")
            except:
                space_w = 4
            space_width = space_w + spacing
            if space_width < 1: space_width = 1
            
            current_line_width = 0
            
            for word in words:
                word_width = get_word_width(word)
                if current_line_width + word_width <= screen_size:
                    current_line.append(word)
                    current_line_width += word_width + space_width
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = []
                        current_line_width = 0
                    current_line.append(word)
                    current_line_width = word_width + space_width
            if current_line:
                lines.append(current_line)
            
            # Check Height
            ascent, descent = font.getmetrics()
            line_height = ascent + descent + spacing_y
            total_height = len(lines) * line_height
            
            # If autosize is OFF, we accept the first pass (initial_font_size)
            if not settings.get("autosize", False):
                break
                
            # If autosize is ON, check if it fits
            if total_height <= screen_size and all(get_word_width(w) <= screen_size for w in words):
                 # Fits!
                 break
        
        # Draw lines using chosen target_font_size
        text_layer = Image.new("RGBA", (screen_size, screen_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        y = (screen_size - total_height) // 2 if settings.get("autosize", False) else 0 # Center vertically if autosizing
        if y < 0: y = 0
        
        for line_words in lines:
            if y >= screen_size: break
            # Center Horizontally?
            # Standard wrapper is left aligned. Perfect fit usually implies Center/Center.
            # Let's calculate line width for centering
            line_w = 0
            for i, w in enumerate(line_words):
                 line_w += get_word_width(w)
                 if i < len(line_words) - 1: line_w += space_width
            
            x = (screen_size - line_w) // 2 if settings.get("autosize", False) else 0
            if x < 0: x = 0
            
            for i, word in enumerate(line_words):
                for char in word:
                    if x >= screen_size: break
                    draw.text((x, y), char, font=font, fill=(255, 255, 255, 255))
                    bbox = font.getbbox(char)
                    char_w = (bbox[2] - bbox[0]) if bbox else font.getlength(char)
                    x += char_w + spacing
                if i < len(line_words) - 1:
                     x += space_width
            y += line_height
            
        if blur < 5:
             r, g, b, a = text_layer.split()
             gain = 1.0 + ((5 - blur) * 2.0) 
             def apply_contrast(p):
                 v = (p - 128) * gain + 128
                 return max(0, min(255, int(v)))
             a = a.point(apply_contrast)
             text_layer.putalpha(a)
             
        final_image = Image.new("RGB", (screen_size, screen_size), (0, 0, 0))
        r, g, b, a = text_layer.split()
        colored_text = Image.new("RGB", (screen_size, screen_size), color)
        final_image.paste(colored_text, mask=a)
        
        image = final_image
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image.save(tmp.name)
            tmp_path = tmp.name
        try:
            await IDMImage().setMode(1)
            await IDMImage().uploadProcessed(tmp_path, pixel_size=screen_size)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
