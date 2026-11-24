import importlib.util
import json
import os
from pathlib import Path

import httpx
import pytest

SCRIPT = (
    Path(__file__).parents[1]
    / "skills/health-record-export/scripts/mychart_documents.py"
)
spec = importlib.util.spec_from_file_location("mychart_documents", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_download_resolves_application_relative_url():
    assert (
        module.download_url("https://portal.example", "/MyChart", "/Documents/file")
        == "https://portal.example/MyChart/Documents/file"
    )


@pytest.mark.parametrize(
    "url",
    [
        "https://other.example/file",
        "//other.example/file",
        "http://portal.example/file",
        "https://user@portal.example/file",
    ],
)
def test_download_rejects_cross_origin_or_credential_bearing_urls(url):
    with pytest.raises(ValueError):
        module.download_url("https://portal.example", "/MyChart", url)


def test_original_tiff_bytes_and_page_two_are_preserved(tmp_path):
    pages = [
        [{"dcsID": "document-1", "docExt": "TIF", "docType": "Example scan"}],
        [{"dcsID": "document-2", "docExt": "TIF", "docType": "Example scan"}],
        [],
    ]
    original = b"II*\x00\x00\x00\x00\x00"

    def respond(request):
        if request.url.path.endswith("LoadOtherDocuments"):
            return httpx.Response(200, json={"documents": pages.pop(0)})
        if request.url.path.endswith("GetDocumentDetails"):
            source_id = json.loads(request.content)["dcsId"]
            return httpx.Response(
                200,
                json={
                    "downloadUrl": "/Documents/" + source_id,
                    "mimeType": "image/tiff",
                    "token": "must-not-persist",
                },
            )
        return httpx.Response(200, content=original)

    with httpx.Client(
        base_url="https://portal.example", transport=httpx.MockTransport(respond)
    ) as client:
        result = module.export_documents(
            client, "/MyChart", tmp_path, "Example institution"
        )
    assert len(result) == 2
    assert all(Path(record["path"]).read_bytes() == original for record in result)
    assert len({record["path"] for record in result}) == 2
    assert "must-not-persist" not in (tmp_path / "manifest.jsonl").read_text()


def test_malformed_document_response_is_not_an_empty_archive(tmp_path):
    with (
        httpx.Client(
            base_url="https://portal.example",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"error": "expired session"})
            ),
        ) as client,
        pytest.raises((ValueError, TypeError)),
    ):
        module.export_documents(client, "/MyChart", tmp_path, "Example institution")


def test_login_page_cannot_be_archived_as_a_document(tmp_path):
    def respond(request):
        if request.url.path.endswith("LoadOtherDocuments"):
            return httpx.Response(
                200, json={"documents": [{"dcsID": "document-1", "docExt": "HTML"}]}
            )
        if request.url.path.endswith("GetDocumentDetails"):
            return httpx.Response(200, json={"downloadUrl": "/Documents/file"})
        return httpx.Response(200, text='<html><input type="password"></html>')

    with (
        httpx.Client(
            base_url="https://portal.example", transport=httpx.MockTransport(respond)
        ) as client,
        pytest.raises(ValueError),
    ):
        module.export_documents(client, "/MyChart", tmp_path, "Example institution")
    assert not list(tmp_path.glob("*.html"))


def test_saved_receipt_survives_a_later_failed_download(tmp_path):
    pages = [
        [
            {"dcsID": "document-1", "docExt": "TXT"},
            {"dcsID": "document-2", "docExt": "TXT"},
        ],
        [],
    ]

    def respond(request):
        if request.url.path.endswith("LoadOtherDocuments"):
            return httpx.Response(200, json={"documents": pages.pop(0)})
        if request.url.path.endswith("GetDocumentDetails"):
            return httpx.Response(
                200,
                json={
                    "downloadUrl": "/Documents/" + json.loads(request.content)["dcsId"]
                },
            )
        return httpx.Response(
            503 if request.url.path.endswith("document-2") else 200,
            content=b"Original source text",
        )

    with (
        httpx.Client(
            base_url="https://portal.example", transport=httpx.MockTransport(respond)
        ) as client,
        pytest.raises(httpx.HTTPStatusError),
    ):
        module.export_documents(client, "/MyChart", tmp_path, "Example institution")
    receipts = (tmp_path / "manifest.jsonl").read_text().splitlines()
    assert len(receipts) == 1
    assert Path(json.loads(receipts[0])["path"]).read_bytes() == b"Original source text"


def test_repeated_page_is_a_failure_instead_of_an_infinite_loop(tmp_path):
    def respond(request):
        if request.url.path.endswith("LoadOtherDocuments"):
            return httpx.Response(
                200, json={"documents": [{"dcsID": "document-1", "docExt": "TXT"}]}
            )
        if request.url.path.endswith("GetDocumentDetails"):
            return httpx.Response(200, json={"downloadUrl": "/Documents/file"})
        return httpx.Response(200, content=b"Original source text")

    with (
        httpx.Client(
            base_url="https://portal.example", transport=httpx.MockTransport(respond)
        ) as client,
        pytest.raises(ValueError),
    ):
        module.export_documents(client, "/MyChart", tmp_path, "Example institution")


@pytest.mark.parametrize(
    ("extension", "body"),
    [
        ("TXT", b"<html><title>Sign in</title></html>"),
        ("HTML", b"<html><input type=password></html>"),
        ("HTML", b'<html><title>Sign in</title><form action="/saml"></form></html>'),
    ],
)
def test_authentication_html_is_not_promoted_to_an_original(tmp_path, extension, body):
    pages = [[{"dcsID": "document-1", "docExt": extension}], []]

    def respond(request):
        if request.url.path.endswith("LoadOtherDocuments"):
            return httpx.Response(200, json={"documents": pages.pop(0)})
        if request.url.path.endswith("GetDocumentDetails"):
            return httpx.Response(200, json={"downloadUrl": "/Documents/file"})
        return httpx.Response(200, content=body, headers={"content-type": "text/html"})

    with (
        httpx.Client(
            base_url="https://portal.example", transport=httpx.MockTransport(respond)
        ) as client,
        pytest.raises(ValueError),
    ):
        module.export_documents(client, "/MyChart", tmp_path, "Example institution")
    assert (tmp_path / "manifest.jsonl").read_text() == ""


def test_interrupted_promotion_does_not_leave_a_truncated_original(
    tmp_path, monkeypatch
):
    def no_space(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(os, "replace", no_space)
    pages = [[{"dcsID": "document-1", "docExt": "TXT"}], []]

    def respond(request):
        if request.url.path.endswith("LoadOtherDocuments"):
            return httpx.Response(200, json={"documents": pages.pop(0)})
        if request.url.path.endswith("GetDocumentDetails"):
            return httpx.Response(200, json={"downloadUrl": "/Documents/file"})
        return httpx.Response(200, content=b"Original source text")

    with (
        httpx.Client(
            base_url="https://portal.example", transport=httpx.MockTransport(respond)
        ) as client,
        pytest.raises(OSError),
    ):
        module.export_documents(client, "/MyChart", tmp_path, "Example institution")
    assert not list(tmp_path.glob("*.txt"))
    assert not list(tmp_path.glob(".pending-*"))
    assert (tmp_path / "manifest.jsonl").read_text() == ""


def test_incomplete_final_receipt_can_be_recovered_without_losing_prior_receipts(
    tmp_path,
):
    previous = {
        "source": "Example institution",
        "source_id": "previous-document",
        "metadata": {"dcsID": "previous-document", "docExt": "TXT"},
        "path": str(tmp_path / "previous.txt"),
        "sha256": "previous-hash",
        "bytes": 20,
        "content_type": "text/plain",
    }
    ledger = tmp_path / "manifest.jsonl"
    ledger.write_text(json.dumps(previous) + '\n{"source_id":')
    with httpx.Client(
        base_url="https://portal.example",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"documents": []})
        ),
    ) as client:
        assert (
            module.export_documents(client, "/MyChart", tmp_path, "Example institution")
            == []
        )
    assert ledger.read_text() == json.dumps(previous) + "\n"
