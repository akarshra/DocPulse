import asyncio
from backend.tests.test_services import test_stream_chat_missing_index_yields_error
import pytest

async def run():
    class DummyMonkeyPatch:
        def setattr(self, *args, **kwargs):
            pass
    try:
        await test_stream_chat_missing_index_yields_error(DummyMonkeyPatch())
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(run())
