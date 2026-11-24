# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.28"]
# ///
"""Download originals from an already authenticated MyChart My Documents page."""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx


def download_url(origin, prefix, link):
    if not isinstance(link, str) or not link:
        raise ValueError("The source did not supply a document download URL")
    # Epic returns these paths relative to the application, not the host.
    if link.startswith("/Documents/"):
        link = prefix + link
    absolute = urljoin(origin.rstrip("/") + "/", link)
    expected, actual = urlsplit(origin), urlsplit(absolute)
    if (
        actual.scheme != "https"
        or actual.netloc != expected.netloc
        or actual.username is not None
    ):
        raise ValueError("Refusing to forward portal credentials to another origin")
    return absolute


def atomic_write(path, content):
    pending = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".pending-", delete=False
        ) as output:
            pending = Path(output.name)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(pending, path)
    finally:
        if pending is not None:
            pending.unlink(missing_ok=True)


def read_receipts(path):
    records = []
    lines = path.read_bytes().splitlines(keepends=True)
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except (ValueError, UnicodeError):
            if index != len(lines) - 1 or line.endswith(b"\n"):
                raise ValueError(
                    "Receipt manifest is corrupt before its final incomplete record"
                ) from None
            atomic_write(
                path, "".join(json.dumps(record) + "\n" for record in records).encode()
            )
    return records


def export_documents(client, prefix, destination, source):
    destination = Path(destination)
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination.chmod(0o700)
    ledger = destination / "manifest.jsonl"
    ledger.touch(mode=0o600, exist_ok=True)
    ledger.chmod(0o600)
    receipts = read_receipts(ledger)
    previous = {record["path"] for record in receipts}
    seen = set()
    saved = []
    initial = True
    while True:
        response = client.post(
            prefix + "/api/documents/viewer/LoadOtherDocuments",
            json={"isInitialLoad": initial},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(
            payload.get("documents"), list
        ):
            raise TypeError(
                "Unexpected document list; an expired session is not an empty archive"
            )
        documents = payload["documents"]
        if not documents:
            return saved
        initial = False
        for document in documents:
            if (
                not isinstance(document, dict)
                or not isinstance(document.get("dcsID"), str)
                or not document["dcsID"]
            ):
                raise ValueError("Source document has no usable identifier")
            source_id = document["dcsID"]
            if source_id in seen:
                raise ValueError(
                    "Pagination repeated a source document; coverage is unresolved"
                )
            seen.add(source_id)
            extension = document.get("docExt", "")
            if not isinstance(extension, str) or not re.fullmatch(
                r"[A-Za-z0-9]{1,10}", extension
            ):
                raise ValueError("Unsafe or missing document file extension")
            response = client.post(
                prefix + "/api/documents/viewer/GetDocumentDetails",
                json={
                    "dcsId": source_id,
                    "fileExtension": extension,
                    "organizationId": "",
                    "useOldMobileLink": True,
                },
            )
            response.raise_for_status()
            details = response.json()
            if not isinstance(details, dict):
                raise TypeError("Unexpected document details")
            url = download_url(str(client.base_url), prefix, details.get("downloadUrl"))
            response = client.get(url)
            response.raise_for_status()
            content = response.content
            if not content:
                raise ValueError("The source returned an empty document")
            lower = content[:100_000].lower()
            is_html = "text/html" in response.headers.get(
                "content-type", ""
            ).lower() or lower.lstrip().startswith((b"<!doctype html", b"<html"))
            if is_html and extension.upper() not in ("HTML", "HTM"):
                raise ValueError(
                    "Unexpected HTML was returned instead of the source file type"
                )
            if (
                re.search(rb"<input\b[^>]*type\s*=\s*[\"\x27]?password\b", lower)
                or re.search(rb"<title[^>]*>\s*(?:sign\s*in|log\s*in|login)\b", lower)
                or re.search(
                    rb"<input\b[^>]*name\s*=\s*[\"\x27]?(?:samlresponse|samlrequest|wresult|id_token)\b",
                    lower,
                )
            ):
                raise ValueError(
                    "A sign-in page was returned instead of the source document"
                )
            if extension.upper() in ("TIF", "TIFF") and not content.startswith(
                (b"II*\x00", b"MM\x00*")
            ):
                raise ValueError("The source did not return the expected TIFF original")
            if extension.upper() == "PDF" and not content.startswith(b"%PDF-"):
                raise ValueError("The source did not return the expected PDF original")
            if extension.upper() in ("JPG", "JPEG") and not content.startswith(
                b"\xff\xd8\xff"
            ):
                raise ValueError("The source did not return the expected JPEG original")
            if extension.upper() == "PNG" and not content.startswith(
                b"\x89PNG\r\n\x1a\n"
            ):
                raise ValueError("The source did not return the expected PNG original")
            digest = hashlib.sha256(content).hexdigest()
            identity = hashlib.sha256((source + "|" + source_id).encode()).hexdigest()
            path = destination / (identity + "-" + digest + "." + extension.lower())
            if path.exists():
                if path.read_bytes() != content:
                    raise ValueError(
                        "An existing original differs; preserving it for review"
                    )
            else:
                atomic_write(path, content)
            record = {
                "source": source,
                "source_id": source_id,
                "metadata": document,
                "path": str(path),
                "sha256": digest,
                "bytes": len(content),
                "content_type": response.headers.get("content-type", ""),
            }
            if str(path) not in previous:
                receipts.append(record)
                atomic_write(
                    ledger,
                    "".join(
                        json.dumps(row, ensure_ascii=False) + "\n" for row in receipts
                    ).encode(),
                )
                previous.add(str(path))
            saved.append(record)


AUTH_JS = r"""
const [target, port] = process.argv.slice(2);
const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const page = pages.find(p => p.id === target && p.type === 'page');
if (!page) throw new Error('The exact browser target is unavailable');
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  ws.addEventListener('open', resolve, {once:true});
  ws.addEventListener('error', reject, {once:true});
});
let next = 0;
const pending = new Map();
ws.addEventListener('message', event => {
  const reply = JSON.parse(event.data);
  const promise = pending.get(reply.id);
  if (promise) {
    pending.delete(reply.id);
    reply.error ? promise.reject(new Error(reply.error.message)) : promise.resolve(reply.result);
  }
});
const send = (method, params={}) => new Promise((resolve,reject) => {
  const id = ++next;
  pending.set(id, {resolve,reject});
  ws.send(JSON.stringify({id,method,params}));
});
const timer = setTimeout(() => {process.stderr.write('Browser session read timed out\n'); process.exit(1)}, 20000);
try {
  const result = await send('Runtime.evaluate', {returnByValue:true, expression:`(() => {
    if (!location.pathname.endsWith('/app/document-center/my-documents')) throw new Error('Open My Documents first');
    const token = document.querySelector('input[name=__RequestVerificationToken]')?.value;
    if (!token) throw new Error('The authenticated page has no request token');
    return {origin:location.origin,prefix:location.pathname.split('/app/')[0],referer:location.href,token,userAgent:navigator.userAgent};
  })()`});
  if (result.exceptionDetails || !result.result?.value) throw new Error('Unable to read this identified My Documents session');
  const auth = result.result.value;
  const cookies = await send('Network.getCookies', {urls:[auth.referer]});
  auth.cookie = cookies.cookies.map(c => `${c.name}=${c.value}`).join('; ');
  process.stdout.write(JSON.stringify(auth));
} finally {
  clearTimeout(timer);
  ws.close();
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        required=True,
        help="Exact owned CDP target already displaying My Documents",
    )
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument(
        "--source",
        required=True,
        help="Confirmed institution label from the private export register",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Private temporary directory for originals and receipts",
    )
    args = parser.parse_args()
    # The captured stdout stays in memory; session credentials never enter argv or files.
    result = subprocess.run(
        ["node", "--input-type=module", "-", args.target, str(args.port)],
        input=AUTH_JS,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        parser.exit(
            1,
            "Could not read the exact authenticated My Documents tab; no fallback target used.\n",
        )
    auth = json.loads(result.stdout)
    headers = {
        "Cookie": auth["cookie"],
        "__RequestVerificationToken": auth["token"],
        "Origin": auth["origin"],
        "Referer": auth["referer"],
        "User-Agent": auth["userAgent"],
    }
    try:
        with httpx.Client(
            base_url=auth["origin"],
            headers=headers,
            timeout=120,
            follow_redirects=False,
        ) as client:
            records = export_documents(
                client, auth["prefix"], args.out_dir, args.source
            )
    except httpx.HTTPError as error:
        status = (
            error.response.status_code
            if isinstance(error, httpx.HTTPStatusError)
            else "network error"
        )
        parser.exit(
            1,
            f"Export stopped ({status}); existing originals and receipts are retained.\n",
        )
    except (ValueError, TypeError) as error:
        parser.exit(1, f"{error}; existing originals and receipts are retained.\n")
    print(
        json.dumps(
            {
                "source": args.source,
                "documents": len(records),
                "bytes": sum(r["bytes"] for r in records),
                "manifest": str(args.out_dir / "manifest.jsonl"),
            }
        )
    )


if __name__ == "__main__":
    main()
