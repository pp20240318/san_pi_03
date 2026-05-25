#!/usr/bin/env python3
"""Mirror activity pages and static assets to local folders."""

import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://388jlvip.com"
ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 90

PAGES = [
    ("218", f"{BASE}/activity/Custom/218"),
    ("211", f"{BASE}/activity/Custom/211"),
]

CORE_ASSETS = [
    "/assets/index-D-xDk-oC.js",
    "/assets/vendor_modules-Dz9LVwzb.js",
    "/assets/index-CQhJqFQU.css",
    "/assets/vendor_modules-9b7WOkhW.css",
    "/assets/polyfills-legacy-BCtcORl3.js",
    "/assets/index-legacy-h_aV9FwN.js",
    "/sw.produce.min.2.1.6.js",
]

ALLOWED_EXTERNAL = (
    "upload.t-u-7-v.com",
    "challenges.cloudflare.com",
    "o.alicdn.com",
    "telegram.org",
)

SAFE_PATH = re.compile(
    r"^/(?:assets|images|svg|icons|first|second|dw)/[a-zA-Z0-9._/-]+\.(?:js|css|png|jpe?g|gif|webp|svg|ico|woff2?|atlas|skel)$"
)

downloaded: dict[str, str] = {}
queue: list[str] = []
failed: set[str] = set()


def fetch(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        print(f"  FAIL: {url} -> {e}")
        failed.add(url)
        return None


def normalize_url(url: str) -> str | None:
    url = url.split("#")[0].strip()
    if not url or url.startswith(("data:", "javascript:", "mailto:", "#")):
        return None
    if url.startswith("//"):
        url = "https:" + url
    elif url.startswith("/"):
        url = BASE + url
    if not url.startswith("http"):
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc == "388jlvip.com":
        if re.match(r"/activity/Custom/\d+$", parsed.path.rstrip("/")):
            return None
        return url
    if parsed.netloc in ALLOWED_EXTERNAL:
        return url
    return None


def url_to_local_path(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "388jlvip.com":
        path = parsed.path.lstrip("/") or "index.html"
        return f"external/{parsed.netloc}/{path}"
    return parsed.path.lstrip("/")


def save_file(url: str, data: bytes) -> str:
    rel = url_to_local_path(url)
    if any(c in rel for c in '<>:"|?*${}'):
        raise ValueError(f"unsafe path: {rel}")
    full = STATIC / rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_bytes(data)
    downloaded[url] = rel
    return rel


def enqueue(url: str | None) -> None:
    if not url or url in downloaded or url in failed or url in queue:
        return
    queue.append(url)


def extract_site_paths(text: str) -> set[str]:
    found: set[str] = set()
    patterns = [
        r'["\'](/(?:assets|images|svg|icons|first|second|dw)/[a-zA-Z0-9._/-]+\.(?:js|css|png|jpe?g|gif|webp|svg|ico|woff2?|atlas|skel))["\']',
        r'url\(\s*["\']?(/(?:assets|images|svg|icons|first|second|dw)/[a-zA-Z0-9._/-]+\.(?:png|jpe?g|gif|webp|svg|woff2?))["\']?\s*\)',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            path = m.group(1)
            if SAFE_PATH.match(path):
                found.add(path)
    return found


def extract_external_from_html(text: str) -> set[str]:
    urls: set[str] = set()
    for m in re.finditer(
        r'(?:src|href)\s*=\s*["\'](https?://[^"\']+)["\']', text, re.IGNORECASE
    ):
        u = normalize_url(m.group(1))
        if u:
            urls.add(u)
    for m in re.finditer(r'https?://upload\.t-u-7-v\.com/[a-zA-Z0-9._/-]+', text):
        u = normalize_url(m.group(0))
        if u:
            urls.add(u)
    return urls


def process_file(url: str, data: bytes) -> None:
    if url.endswith((".js", ".css", ".html", ".svg")):
        text = data.decode("utf-8", errors="replace")
        for path in extract_site_paths(text):
            enqueue(BASE + path)


def download_all() -> None:
    while queue:
        url = queue.pop(0)
        if url in downloaded or url in failed:
            continue
        data = fetch(url)
        if data is None:
            continue
        rel = save_file(url, data)
        print(f"  OK: {rel} ({len(data)} bytes)")
        process_file(url, data)


def page_output_dir(slug: str) -> Path:
    return ROOT / "activity" / "Custom" / slug


def rewrite_html(html: str, page_dir: Path) -> str:
    prefix = "/static/"
    for url, rel in sorted(downloaded.items(), key=lambda x: -len(x[0])):
        local = prefix + rel.replace("\\", "/")
        html = html.replace(url, local)
        if url.startswith(BASE):
            html = html.replace(url[len(BASE) :], local)
    return html


def index_existing_static() -> None:
    if not STATIC.exists():
        return
    for full in STATIC.rglob("*"):
        if not full.is_file():
            continue
        rel = full.relative_to(STATIC).as_posix()
        if rel.startswith("external/"):
            rest = rel[len("external/") :]
            host, _, path = rest.partition("/")
            url = f"https://{host}/{path}"
        else:
            url = f"{BASE}/{rel}"
        downloaded[url] = rel


def ensure_core_assets() -> None:
    for path in CORE_ASSETS:
        url = BASE + path
        full = STATIC / path.lstrip("/")
        if full.exists():
            if url not in downloaded:
                downloaded[url] = path.lstrip("/")
            process_file(url, full.read_bytes())
            continue
        enqueue(url)


def mirror_page(slug: str, page_url: str) -> None:
    print(f"\n=== Page {slug} ===")
    data = fetch(page_url)
    if not data:
        raise SystemExit(f"Cannot fetch {page_url}")
    html = data.decode("utf-8", errors="replace")
    for path in extract_site_paths(html):
        enqueue(BASE + path)
    for ext in extract_external_from_html(html):
        enqueue(ext)
    ensure_core_assets()
    download_all()
    out_dir = page_output_dir(slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(rewrite_html(html, out_dir), encoding="utf-8")
    print(f"Saved {out_dir / 'index.html'}")


def main() -> None:
    STATIC.mkdir(exist_ok=True)
    index_existing_static()
    ensure_core_assets()
    for slug, url in PAGES:
        mirror_page(slug, url)
    for t in ("temp_218.html", "temp_211.html"):
        p = ROOT / t
        if p.exists():
            p.unlink()
    print(f"\nDone: {len(downloaded)} files in {STATIC}")
    print("Open http://localhost:8080/activity/Custom/218/ (with http.server)")
    print("Tip: `python -m http.server 8080` in project root for local preview")


if __name__ == "__main__":
    main()
