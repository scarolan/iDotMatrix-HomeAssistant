# iDotMatrix Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/tukies/iDotMatrix-HomeAssistant)](https://github.com/tukies/iDotMatrix-HomeAssistant/releases)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-yellow.svg)](https://buymeacoffee.com/tukie)

A fully featured, modern Home Assistant integration for **iDotMatrix** pixel art displays. 

Connects directly to your device via Bluetooth (native or proxy) without any cloud dependencies. Unlock the full potential of your display with advanced animations, typography controls, and "Party Mode" features.

---

## Features

- **Instant Bluetooth Connectivity**: Supports native adapters and ESPHome Bluetooth Proxies for rock-solid connections.
- **Advanced Text Engine**: 
    - Full control over Font, Color, Speed, and Animation Mode.
    - **Pixel Fonts**: Bundled fonts include VT323, Press Start 2P, Rain DRM3, and classic BDF bitmap sets.
    - **Typography Controls**: Adjust letter spacing (horizontal/vertical), blur/sharpness, and font size.
- **Fun Text (Party Mode)**: 
    - Animates messages word-by-word with random bright colors.
    - Adjustable delay for perfect timing.
- **Autosize Perfect Fit**: 
    - Automatically scales text to fit the screen bounds, centering it for a clean look.
- **Clock Control**: 
    - Syncs time automatically.
    - Customizable 12h/24h formats, date display, and colors.
- **Designer Card (Layered Templates)**:
    - Build multi-layer faces using text + icon templates.
    - Save/load designs and auto-refresh with a trigger entity (e.g., `sensor.time`).
- **Icons**:
    - Render `mdi:` icons directly.
    - Use `/local/...png` or URL icons for custom sets. SVG requires Cairo (optional).
- **Device Control**:
    - Turn On/Off, set Brightness, color, and screen size (16x16 / 32x32 / 64x64).

---

## Installation

### Option 1: HACS (Recommended)
1. Open HACS in Home Assistant.
2. Go to **Integrations** > **Triple Dots** > **Custom Repositories**.
3. Add `https://github.com/tukies/iDotMatrix-HomeAssistant` as an **Integration**.
4. Click **Download**.
5. Restart Home Assistant.

### Option 2: Manual
1. Download the `custom_components/idotmatrix` folder from this repository.
2. Copy it to your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.

---

## Configuration

1. Go to **Settings** > **Devices & Services**.
2. Click **Add Integration** and search for **iDotMatrix**.
3. The integration will automatically discover nearby devices. Select your device.
    - *Note: Ensure your device is powered on and not connected to the phone app.*

---

## Lovelace Card (Designer)

1. Add the resource in **Settings** > **Dashboards** > **Resources**:
   - URL: `/local/idotmatrix-card.js`
   - Type: `JavaScript Module`
2. Add a card to your dashboard:
   ```yaml
   type: custom:idotmatrix-card
   title: iDotMatrix Designer
   ```
3. Set `Display Mode` on the device page to **Display design from the Card**.

---

## Usage Guide

### Display Mode
Pick what the device shows from the device page:
- **Entity**: `select.<device>_display_mode`
- **Options**: Display Text Field / Display design from the Card
- **Tip**: Entity IDs are per-device, e.g., `text.idm_3fb639_display_text`.

### Text Control
Control the scrolling text on your device using the `Display Text` entity.
- **Entity**: `text.<device>_display_text`
- **Actions**: Type any text to update the display immediately.
- **Settings**: Use the configuration entities (sliders/selects) to adjust:
    - **Font**: Choose from installed pixel-perfect fonts.
    - **Speed**: Scroll speed (1-100).
    - **Color**: Full RGB control via `light.<device>_panel_colour`.
    - **Spacing**: Tweak kerning with "Text Spacing".

### Fun Text (Party Mode)
Want to spice things up? Use the Fun Text entity!
- **Entity**: `text.<device>_fun_text`
- **How it works**:
    1. Enter a phrase like "HAPPY NEW YEAR".
    2. The display shows one word at a time (split on spaces).
    3. Each word gets a **random bright color** from a fixed palette.
    4. The last word remains on screen (no final full‑sentence render).
- **Control**: Adjust the delay between words with the **Fun Text Delay** slider (`number.<device>_fun_text_delay`).

### Autosize (Perfect Fit)
Stop guessing font sizes. Let the integration do the math.
- **Entity**: `switch.<device>_text_perfect_fit_autosize`
- **How it works**:
    - **ON**: The integration iteratively resizes your text (shrinking from max size) until it fits perfectly within the screen capabilities 
    - **OFF**: Standard scrolling or manual font size.

### Designer Card (Layers + Icons)
- Use the Designer card to build a layered face.
- Each layer supports:
  - **Template**: Jinja template for text
  - **Icon Template**: Jinja template that returns an icon string (e.g., `mdi:floor-lamp`)
  - **Icon Size**: Pixel size for the icon
  - **X/Y, font, spacing, blur, color**
- To combine icons and text, use separate layers and offset X/Y.

Examples:
- Icon based on entity state:
  ```
  {{ 'mdi:floor-lamp' if is_state('light.lamp', 'on') else 'mdi:floor-lamp-outline' }}
  ```
- Use an entity icon directly:
  ```
  {{ state_attr('light.lamp', 'icon') }}
  ```
- Custom PNG icon:
  ```
  /local/icons/alert.png
  ```

### Clock & Time
- **Sync Time**: Press `button.<device>_sync_time` to sync the device clock to Home Assistant's time.
- **Formats**: Toggle `select.<device>_clock_format` (12h/24h) and `switch.<device>_clock_show_date`.

### Bluetooth Proxy
This integration fully supports **ESPHome Bluetooth Proxies**.
- If your Home Assistant server is far from the device, use a cheap ESP32 with ESPHome to extend range.
- The integration will automatically find and use the proxy with the best signal.

---

## Troubleshooting

**"Device unavailable" / "No backend found"**
- Ensure the device is **disconnected** from the mobile app. It can only talk to one controller at a time.
- If using a local adapter on macOS/Linux, ensure BlueZ is up to date.
- Restart the iDotMatrix device (unplug/replug).

**Icons not showing**
- For `mdi:` icons, make sure Home Assistant has internet access on first render (the font + metadata are fetched and cached in memory).
- For custom icons, use PNG URLs (`/local/...png` or `https://...png`).
- SVG URLs require Cairo; install it and restart if you need SVG rasterization.

**Designer card changes not showing**
- Hard-refresh the browser after updating `idotmatrix-card.js`.
- If you run `run_ha_dev.sh`, it rewrites `config/configuration.yaml` and uses port 8128.

---

<p align="center">
  Built with ❤️ by Adrian
</p>
