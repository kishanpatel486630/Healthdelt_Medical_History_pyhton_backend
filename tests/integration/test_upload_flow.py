from tests.integration.helpers import register_and_verify


def test_upload_list_delete_roundtrip(client):
    auth = register_and_verify(
        client,
        full_name="Upload Tester",
        email="upload.test@example.com",
        password="uploadpass123",
        role="PATIENT",
    )
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    upload = client.post(
        "/api/uploads?folder=reports",
        headers=headers,
        files={"file": ("lab.txt", b"cbc report content", "text/plain")},
    )
    assert upload.status_code == 200, upload.text
    upload_body = upload.json()
    assert upload_body["success"] is True
    rel_path = upload_body["file"]["path"]

    listing = client.get("/api/uploads?folder=reports", headers=headers)
    assert listing.status_code == 200, listing.text
    listing_body = listing.json()
    assert listing_body["success"] is True
    assert any(item["name"] == "lab.txt" for item in listing_body["items"])

    deletion = client.delete(f"/api/uploads/{rel_path}", headers=headers)
    assert deletion.status_code == 200, deletion.text
    assert deletion.json()["success"] is True
