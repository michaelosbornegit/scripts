# Make sure to run install-aioble.py script before running this
import aioble
import bluetooth

import asyncio

_ENV_SENSE_UUID = bluetooth.UUID(0x181A)
_ENV_SENSE_TEMP_UUID = bluetooth.UUID(0x2A6E)
_GENERIC_THERMOMETER = const(768)

_ADV_INTERVAL_US = const(250000)

temp_service = aioble.Service(_ENV_SENSE_UUID)
temp_char = aioble.Characteristic(temp_service, _ENV_SENSE_TEMP_UUID, read=True, notify=True)

aioble.register_services(temp_service)

async def main():
    while True:
        connection = await aioble.advertise(
                _ADV_INTERVAL_US,
                name="temp-sense",
                services=[_ENV_SENSE_UUID],
                appearance=_GENERIC_THERMOMETER,
                manufacturer=(0xabcd, b"1234"),
            )
        print("Connection from", connection)


asyncio.run(main())