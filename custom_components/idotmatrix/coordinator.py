"""DataUpdateCoordinator for iDotMatrix."""
from __future__ import annotations

import logging
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

_LOGGER = logging.getLogger(__name__)


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
        }

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
            
            await Clock().setMode(
                style=settings.get("clock_style", 0),
                visibleDate=settings.get("clock_date", True),
                hour24=h24,
                r=c[0],
                g=c[1],
                b=c[2]
            )
            
        # Notify listeners to update UI states
        self.async_set_updated_data(self.data)

    async def _set_multiline_text(self, text: str, settings: dict) -> None:
        """Generate an image from text and upload it."""
        screen_size = int(settings.get("screen_size", 32))
        font_name = settings.get("font")
        color = tuple(settings.get("color", (255, 0, 0)))
        spacing = int(settings.get("spacing", 1))
        
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
                
        # Determine font size
        font_size = int(settings.get("font_size", 10))

        try:
            if font_path.lower().endswith(".bdf"):
                 font = ImageFont.load(font_path)
            else:
                 font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()

        # Pixel-based Word Wrapping
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
            return w - spacing # Remove last spacing if > 0

        # Space width calculation
        try:
             space_bbox = font.getbbox(" ")
             if space_bbox:
                 space_w = space_bbox[2] - space_bbox[0]
             else:
                 space_w = font.getlength(" ")
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

        # Draw lines
        text_layer = Image.new("RGBA", (screen_size, screen_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        spacing_y = int(settings.get("spacing_y", 1))
        blur = int(settings.get("blur", 5))
        
        y = 0
        ascent, descent = font.getmetrics()
        line_height = ascent + descent + spacing_y
        
        for line_words in lines:
            if y >= screen_size: break
            x = 0
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
