from typing import Union, List
from ..connectionManager import ConnectionManager
import io
import logging
from PIL import Image as PilImage
import zlib


class Gif:
    logging = logging.getLogger(__name__)

    def __init__(self) -> None:
        self.conn: ConnectionManager = ConnectionManager()

    def _load(self, file_path: str) -> bytes:
        """Load a gif file into a byte buffer.

        Args:
            file_path (str): path to file

        Returns:
            bytes: returns the file contents
        """
        with open(file_path, "rb") as file:
            return file.read()

    def _splitIntoChunks(self, data: bytearray, chunk_size: int) -> List[bytearray]:
        """Split the data into chunks of specified size.

        Args:
            data (bytearray): data to split into chunks
            chunk_size (int): size of the chunks

        Returns:
            List[bytearray]: returns list with chunks of given data input
        """
        return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

    def _createPayloads(
        self, gif_data: bytearray, chunk_size: int = 4096, index: int = 0x0d,
        interval: int = 5
    ) -> List[bytearray]:
        """Creates payloads from a GIF file.

        Args:
            gif_data (bytearray): data of the gif file
            chunk_size (int): size of a chunk
            index (int): GIF index byte. 0x0d (13) for single uploads,
                         0-11 for batch uploads.
            interval (int): Carousel interval in seconds (how long each GIF
                            displays before advancing). Range 0-255.

        Returns:
            List[bytearray]: returns list of bytearray payloads
        """
        # 16-byte chunk header
        header = bytearray(
            [
                255,  # [0:2] chunk_length (filled per chunk)
                255,
                1,    # [2] type: 1 = GIF
                0,    # [3] reserved
                0,    # [4] continuation: 0 = first, 2 = continuation
                255,  # [5:9] file_size (filled below)
                255,
                255,
                255,
                255,  # [9:13] CRC32 (filled below)
                255,
                255,
                255,
                interval & 0xFF,  # [13] carousel interval in seconds
                0,    # [14] reserved
                index & 0xFF,  # [15] index: 0x0d for single, GIF index for batch
            ]
        )
        # split gif into chunks
        chunks = []
        gif_chunks = self._splitIntoChunks(gif_data, chunk_size)
        # set gif length
        header[5:9] = int(len(gif_data)).to_bytes(4, byteorder="little")
        # set crc of gif
        crc = zlib.crc32(gif_data)
        header[9:13] = crc.to_bytes(4, byteorder="little")
        # iterate over chunks
        for i, chunk in enumerate(gif_chunks):
            # starting from the second chunk, set the header to 2
            header[4] = 2 if i > 0 else 0
            # set chunk length in header
            chunk_len = len(chunk) + len(header)
            header[0:2] = chunk_len.to_bytes(2, byteorder="little")
            # append chunk to chunk list
            chunks.append(bytearray(header) + chunk)
        return chunks

    async def uploadUnprocessed(self, file_path: str) -> Union[bool, bytearray]:
        """uploads an image without further checks and resizes.

        Args:
            file_path (str): path to the image file

        Returns:
            Union[bool, bytearray]: False if there's an error, otherwise returns bytearray payload
        """
        try:
            gif_data = self._load(file_path)
            data = self._createPayloads(gif_data)
            if self.conn:
                await self.conn.connect()
                for chunk in data:
                    await self.conn.send(data=chunk)
            return data
        except BaseException as error:
            self.logging.error(f"could not upload gif unprocessed: {error}")
            return False

    def _processGif(self, file_path: str, pixel_size: int = 32, index: int = 0x0d,
                    interval: int = 5) -> Union[bool, List[bytearray]]:
        """Process a GIF file and create payloads (sync, for use in executor).

        Args:
            file_path (str): path to the image file
            pixel_size (int, optional): amount of pixels. Defaults to 32.
            index (int): GIF index byte for header[15].
            interval (int): Carousel interval in seconds.

        Returns:
            Union[bool, List[bytearray]]: False if error, otherwise list of payload chunks
        """
        try:
            with PilImage.open(file_path) as img:
                frames = []
                duration = img.info.get("duration", 100)
                try:
                    while True:
                        frame = img.copy()
                        if frame.size != (pixel_size, pixel_size):
                            frame = frame.resize(
                                (pixel_size, pixel_size), PilImage.NEAREST
                            )
                        frames.append(frame.copy())
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass
                gif_buffer = io.BytesIO()
                frames[0].save(
                    gif_buffer,
                    format="GIF",
                    save_all=True,
                    append_images=frames[1:],
                    loop=1,
                    duration=duration,
                    disposal=2,
                )
                gif_buffer.seek(0)
                return self._createPayloads(gif_buffer.getvalue(), index=index, interval=interval)
        except BaseException as error:
            self.logging.error(f"could not process gif: {error}")
            return False

    async def uploadProcessed(
        self, file_path: str, pixel_size: int = 32, index: int = 0x0d,
        interval: int = 5
    ) -> Union[bool, bytearray]:
        """uploads a file processed to make sure everything is correct before uploading to the device.

        Args:
            file_path (str): path to the image file
            pixel_size (int, optional): amount of pixels (either 16 or 32 makes sense). Defaults to 32.
            index (int): GIF index byte. 0x0d for single, 0-11 for batch.
            interval (int): Carousel interval in seconds.

        Returns:
            Union[bool, bytearray]: False if there's an error, otherwise returns bytearray payload
        """
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, self._processGif, file_path, pixel_size, index, interval)

            if data is False:
                return False

            if self.conn:
                await self.conn.connect()
                for chunk in data:
                    await self.conn.send(data=chunk)
            return data
        except BaseException as error:
            self.logging.error(f"could not upload gif processed: {error}")
            return False

    async def uploadBatch(
        self, file_paths: List[str], pixel_size: int = 32, interval: int = 5
    ) -> bool:
        """Upload multiple GIFs as a batch using the device's batch protocol.

        Sends up to 12 GIFs at once. The device will loop through them automatically.

        Args:
            file_paths: List of paths to GIF files (max 12).
            pixel_size: Pixel size for resizing (16 or 32). Defaults to 32.
            interval: Carousel interval in seconds (how long each GIF displays
                      before advancing to the next). Range 0-255. Defaults to 5.

        Returns:
            True if successful, False on error.
        """
        import asyncio

        if not file_paths:
            return False

        # Device supports max 12 GIFs per batch
        file_paths = file_paths[:12]
        count = len(file_paths)

        try:
            if not self.conn:
                return False

            await self.conn.connect()

            # 1. Send batch mode enable: 04 00 0a 01
            batch_enable = bytearray([0x04, 0x00, 0x0a, 0x01])
            await self.conn.send(data=batch_enable)
            # Brief pause for device to process command
            await asyncio.sleep(0.1)

            # 2. Send batch header with count and indices
            # Format: [length, 0x00, 0x02, 0x01, count, idx0, idx1, ...]
            batch_header = bytearray([0x00, 0x00, 0x02, 0x01, count])
            batch_header.extend(range(count))
            batch_header[0] = len(batch_header) & 0xFF
            batch_header[1] = (len(batch_header) >> 8) & 0xFF
            await self.conn.send(data=batch_header)
            await asyncio.sleep(0.1)

            # 3. Process and stream all GIFs back-to-back
            loop = asyncio.get_event_loop()
            for i, file_path in enumerate(file_paths):
                data = await loop.run_in_executor(
                    None, self._processGif, file_path, pixel_size, i, interval
                )
                if data is False:
                    self.logging.error(f"Failed to process GIF {i}: {file_path}")
                    return False

                for chunk in data:
                    await self.conn.send(data=chunk)

            self.logging.info(f"Batch upload complete: {count} GIFs, interval={interval}s")
            return True

        except BaseException as error:
            self.logging.error(f"Batch upload failed: {error}")
            return False
