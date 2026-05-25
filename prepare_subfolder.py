#!/usr/bin/env python3
"""
把所有活动页相关文件收进一个子目录（默认 aba/），便于放在网站根目录下不影响其它文件。

访问地址示例：
  http://你的域名/aba/activity/Custom/218/

用法：
  python prepare_subfolder.py
  python prepare_subfolder.py mydir    # 自定义子目录名
"""

import os
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_NAME = "aba"

ALIASES = ["assets", "images", "svg", "icons", "first", "second", "dw"]

# 仅静态资源路径要加 /aba/ 前缀；路由路径不要加（已由 vue-router base 处理）
ASSET_PATH_PREFIXES = [
    "/assets/",
    "/images/",
    "/svg/",
    "/icons/",
    "/first/",
    "/second/",
    "/dw/",
    "/static/",
]

TEXT_EXTENSIONS = {".js", ".css", ".html", ".svg"}


def norm_prefix(name: str) -> str:
    name = name.strip().strip("/\\")
    if not name or name in (".", ".."):
        raise SystemExit("子目录名无效")
    return name


def link_dir(target: Path, source: Path) -> None:
    if target.exists() or target.is_symlink():
        if target.is_dir() and not target.is_symlink():
            if any(target.iterdir()):
                print(f"  skip (exists): {target.name}")
                return
            target.rmdir()
        else:
            target.unlink()
    source = source.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if platform.system() == "Windows":
        os.system(f'mklink /J "{target}" "{source}"')
        if not target.exists():
            shutil.copytree(source, target, dirs_exist_ok=True)
            print(f"  copy: {target.name}")
        else:
            print(f"  junction: {target.name}")
    else:
        target.symlink_to(source, target_is_directory=True)
        print(f"  symlink: {target.name}")


def patch_router_base(text: str, prefix: str) -> str:
    p = prefix if prefix.endswith("/") else prefix + "/"
    # vue-router history 基路径
    text = text.replace('v3("/")', f'v3("{p}")')
    text = text.replace("v3('/')", f'v3("{p}")')
    return text


def patch_html(html: str, prefix: str) -> str:
    p = prefix if prefix.endswith("/") else prefix + "/"
    # 只改资源与 base，避免破坏 __APP_CONFIG__ 等大段 JSON
    for old in ("/static/", "../static/", "../../../static/"):
        html = html.replace(old, f"{p}static/")
    html = html.replace('<base href="/"/>', f'<base href="{p}"/>')
    html = html.replace('<base href="/">', f'<base href="{p}">')
    html = html.replace('<base href="./"/>', f'<base href="{p}"/>')
    html = html.replace('<base href="./">', f'<base href="{p}">')
    return html


def patch_js_css(text: str, prefix: str) -> str:
    p = prefix.rstrip("/")
    text = patch_router_base(text, prefix)
    for rp in ASSET_PATH_PREFIXES:
        text = text.replace(f'"{rp}', f'"{p}{rp}')
        text = text.replace(f"'{rp}", f"'{p}{rp}")
        text = text.replace(f"url({rp}", f"url({p}{rp}")
        text = text.replace(f"url('{rp}", f"url('{p}{rp}")
        text = text.replace(f'url("{rp}', f'url("{p}{rp}')
    return text


def patch_text_file(path: Path, prefix: str) -> None:
    text = path.read_text(encoding="utf-8", errors="replace")
    orig = text
    if path.suffix == ".html":
        text = patch_html(text, prefix)
    elif path.suffix in {".js", ".css"}:
        text = patch_js_css(text, prefix)
    if text != orig:
        path.write_text(text, encoding="utf-8")


def copy_and_patch_tree(src: Path, dst: Path, prefix: str) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    for f in dst.rglob("*"):
        if f.is_file() and f.suffix.lower() in TEXT_EXTENSIONS:
            patch_text_file(f, prefix)


def write_nginx_snippet(out: Path, prefix: str, folder_name: str) -> None:
    root = str(out).replace("\\", "/")
    p = prefix.rstrip("/")
    snippet = f"""# 将下面 location 放进你现有的 server {{ }} 中（与其它站点文件共存）
# 网站根目录其它文件不受影响，仅 /{folder_name}/ 由本目录提供

location ^~ /{folder_name}/ {{
    alias {root}/;
    index index.html;
}}

# 访问:
#   http://你的域名/{folder_name}/activity/Custom/218/
#   http://你的域名/{folder_name}/activity/Custom/211/
"""
    (out / "nginx-location.conf").write_text(snippet, encoding="utf-8")


def main() -> None:
    folder_name = norm_prefix(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_NAME)
    prefix = f"/{folder_name}/"
    out = ROOT / folder_name

    static = ROOT / "static"
    activity = ROOT / "activity"
    if not static.is_dir():
        print("缺少 static/，请先运行 mirror_pages.py")
        sys.exit(1)
    if not activity.is_dir():
        print("缺少 activity/，请先运行 fix_paths.py")
        sys.exit(1)

    if out.exists():
        print(f"清理 {folder_name}/ ...")
        shutil.rmtree(out)

    out.mkdir()
    print(f"生成子目录包: {folder_name}/  (URL 前缀 {prefix})")

    print("复制并修补 static/ ...")
    copy_and_patch_tree(static, out / "static", prefix)

    print("复制并修补 activity/ ...")
    copy_and_patch_tree(activity, out / "activity", prefix)

    print("建立资源路径别名:")
    for name in ALIASES:
        src = out / "static" / name
        if src.is_dir():
            link_dir(out / name, src)

    sw_src = out / "static" / "sw.produce.min.2.1.6.js"
    if sw_src.is_file():
        shutil.copy2(sw_src, out / "sw.produce.min.2.1.6.js")
        patch_text_file(out / "sw.produce.min.2.1.6.js", prefix)

    write_nginx_snippet(out, prefix, folder_name)

    print(f"\n完成。把整个 {folder_name}/ 文件夹放到网站根目录下即可。")
    print(f"  本地预览: cd 到网站根目录的上一级，或:")
    print(f"    cd {ROOT}")
    print(f"    python -m http.server 8080")
    print(f"  浏览器: http://127.0.0.1:8080/{folder_name}/activity/Custom/218/")
    print(f"  Nginx:  参考 {folder_name}/nginx-location.conf")


if __name__ == "__main__":
    main()
