#!/usr/bin/env python3
"""Move pages to production-like URLs: activity/Custom/{id}/"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SLUGS = ["218", "211"]


def fix_html(html: str) -> str:
    for old in ("../static/", "../../../static/", "../../../../static/"):
        html = html.replace(old, "/static/")
    html = html.replace('<base href="./"/>', '<base href="/"/>')
    html = html.replace('<base href="./">', '<base href="/">')
    return html


def main() -> None:
    sources = []
    for slug in SLUGS:
        for src in (
            ROOT / f"activity_Custom_{slug}" / "index.html",
            ROOT / "activity" / "Custom" / slug / "index.html",
        ):
            if src.exists():
                sources.append((slug, src))
                break

    for slug, src in sources:
        dst_dir = ROOT / "activity" / "Custom" / slug
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / "index.html"
        dst.write_text(fix_html(src.read_text(encoding="utf-8")), encoding="utf-8")
        print(f"OK: {dst}")

    print("\nOpen:")
    print("  http://localhost:8080/activity/Custom/218/")
    print("  http://localhost:8080/activity/Custom/211/")


if __name__ == "__main__":
    main()
