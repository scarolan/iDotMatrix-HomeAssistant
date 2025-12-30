"""Text platform for iDotMatrix."""
from __future__ import annotations

import os
import tempfile
import textwrap

from PIL import Image, ImageDraw, ImageFont

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import IDotMatrixEntity
from .client.modules.image import Image as IDMImage
from .client.modules.text import Text

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
    _attr_native_value = None
    
    @property
    def unique_id(self) -> str:
        return f"{self._mac}_display_text"

    @property
    def native_value(self) -> str | None:
        """Return the value reported by the text entity."""
        return self._attr_native_value

    async def async_set_value(self, value: str) -> None:
        """Change the text value."""
        if value:
            settings = self.coordinator.text_settings
            
            if settings.get("multiline", False):
                await self._set_multiline_text(value, settings)
            else:
                await Text().setMode(
                    text=value,
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
            self._attr_native_value = value
            self.async_write_ha_state()

    async def _set_multiline_text(self, text: str, settings: dict) -> None:
        """Generate an image from text and upload it."""
        screen_size = int(settings.get("screen_size", 32))
        font_name = settings.get("font")
        color = tuple(settings.get("color", (255, 0, 0)))
        spacing = int(settings.get("spacing", 1))
        
        # Resolve font path
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
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()

        # Pixel-based Word Wrapping
        words = text.split(' ')
        lines = []
        current_line = []
        
        def get_word_width(word):
            if not word: return 0
            # Width is sum of chars + spacing
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
                 space_w = font.getlength(" ") # Fallback if bbox is empty
        except:
             space_w = 4 # Hard fallback
             
        space_width = space_w + spacing
        # Ensure space has noticeable width even if spacing is negative
        if space_width < 1: space_width = 1

        current_line_width = 0
        
        for word in words:
            word_width = get_word_width(word)
            
            # Check if word fits
            if current_line_width + word_width <= screen_size:
                current_line.append(word)
                current_line_width += word_width + space_width
            else:
                # Flush current line
                if current_line:
                    lines.append(current_line)
                    current_line = []
                    current_line_width = 0
                
                # Check if single word is longer than screen
                # Just add it, it will clip or wrap in future if we improved algo
                current_line.append(word)
                current_line_width = word_width + space_width
        
        if current_line:
            lines.append(current_line)

        # Draw lines
        # Create RGBA image for text to handle alpha/blur processing
        text_layer = Image.new("RGBA", (screen_size, screen_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        
        spacing_y = int(settings.get("spacing_y", 1))
        blur = int(settings.get("blur", 5))
        
        y = 0
        # Calculate line height
        ascent, descent = font.getmetrics()
        line_height = ascent + descent + spacing_y
        
        # Draw words
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
            
        # Process Blur/Sharpness
        if blur < 5:
             # Extract alpha
             r, g, b, a = text_layer.split()
             # Calculate gain based on blur setting (0=Sharpest, 5=softest)
             # gain=1 is normal. gain=high is binary.
             # blur=0 -> gain=10? 
             # blur=4 -> gain=1.2
             gain = 1.0 + ((5 - blur) * 2.0) 
             
             # Apply contrast to alpha channel
             def apply_contrast(p):
                 v = (p - 128) * gain + 128
                 return max(0, min(255, int(v)))
             
             a = a.point(apply_contrast)
             text_layer.putalpha(a)
             
        # Composite text layer over black background with selected color
        final_image = Image.new("RGB", (screen_size, screen_size), (0, 0, 0))
        
        # Colorize logic: We have white text. We want 'color'.
        # We can use ImageOps.colorize on the alpha channel?
        # Or simple alpha composite.
        r, g, b, a = text_layer.split()
        colored_text = Image.new("RGB", (screen_size, screen_size), color)
        
        # Paste colored text using processed alpha as mask
        final_image.paste(colored_text, mask=a)
        
        image = final_image
            
        # Save to temp file and upload
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image.save(tmp.name)
            tmp_path = tmp.name
            
        try:
            # Set mode to DIY (1)
            await IDMImage().setMode(1)
            # Upload processed
            await IDMImage().uploadProcessed(tmp_path, pixel_size=screen_size)
            # Ensure mode is persisted? Some devices revert if not refreshed.
            # But normally setMode(1) should stick until setMode(0) or other command.
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
