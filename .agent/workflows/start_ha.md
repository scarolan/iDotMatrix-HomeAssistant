---
description: Start Home Assistant development instance
---

This workflow starts the Home Assistant instance for testing the integration.

**Requirements:**
- Python 3.12 (Strict requirement due to dependency compatibility)
- `ha_venv` (Created automatically if missing)

**Steps:**

1. Run the development script:
   ```bash
   ./run_ha_dev.sh
   ```
   *Note: This script handles venv creation using `python3.12`, links the integration, copies the card to `config/www`, and kills any process already listening on port 8128.*

2. Monitor the output for "Starting Home Assistant...".

3. Open Home Assistant at `http://localhost:8128`.

**Troubleshooting:**
- If you see `TypeError: Channel.getaddrinfo()`, it means Python 3.13 was used. Delete `ha_venv` and rebuild with Python 3.12.
- If you see database schema errors, delete `config/home-assistant_v2.db`.
- If you want a different port, edit `run_ha_dev.sh` before starting.
