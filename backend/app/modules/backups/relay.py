"""Standalone fixed-target TCP relay. No application imports, secrets, shell or dynamic commands."""

import asyncio
import ipaddress
import os


async def main():
    host = str(ipaddress.IPv4Address(os.environ["TARGET_HOST"]))
    port = int(os.environ["TARGET_PORT"])
    listen = int(os.environ["LISTEN_PORT"])
    if not ipaddress.ip_address(host).is_private or not (
        1 <= port <= 65535 and 1 <= listen <= 65535
    ):
        raise ValueError("Invalid fixed relay target")

    async def forward(reader, writer):
        while block := await reader.read(65536):
            writer.write(block)
            await writer.drain()

    async def accept(reader, writer):
        remote = None
        try:
            upstream, remote = await asyncio.wait_for(asyncio.open_connection(host, port), 5)
            tasks = [
                asyncio.create_task(forward(reader, remote)),
                asyncio.create_task(forward(upstream, writer)),
            ]
            try:
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
        except (OSError, TimeoutError):
            # Peer disconnects/readiness failures are not application credential errors.
            print("Relay peer unavailable", flush=True)
        finally:
            for connection in (writer, remote):
                if connection:
                    connection.close()
                    await connection.wait_closed()

    server = await asyncio.start_server(accept, "0.0.0.0", listen)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
