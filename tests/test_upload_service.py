import io
import tempfile
import asyncio

from starlette.datastructures import UploadFile as StarletteUploadFile

from app.services.upload_service import resolve_upload_root, UploadService


def test_upload_service_save_and_list_and_delete():
    with tempfile.TemporaryDirectory() as tmpdir:
        svc = UploadService(tmpdir)
        # create a fake UploadFile
        data = b"hello world"
        # Create a minimal upload-like object with async read, filename and content_type
        class DummyUpload:
            def __init__(self, data, filename="file.bin", content_type="application/octet-stream"):
                self._data = data
                self.filename = filename
                self.content_type = content_type

            async def read(self):
                return self._data

        file = DummyUpload(data, filename="hello.txt", content_type="text/plain")

        # save
        info = asyncio.run(svc.save(file, folder="reports"))
        assert info["name"] == "hello.txt"
        base = svc.resolve_root()
        items = svc.list("reports")
        assert any(i["name"] == "hello.txt" for i in items)

        # delete
        svc.delete(info["path"])
        items_after = svc.list("reports")
        assert not any(i["name"] == "hello.txt" for i in items_after)
