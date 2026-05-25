#!/usr/bin/env python3
"""
生成 nginx_deploy/ 目录：在部署目录下建立与线上一致的路径别名（assets、images 等指向 static 内对应目录）。
Windows 用目录联接（junction），Linux/macOS 用符号链接。
"""

import os
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEPLOY = ROOT / "nginx_deploy"

# 线上 JS 会请求的根路径 → static 下的子目录
ALIASES = [
    "assets",
    "images",
    "svg",
    "icons",
    "first",
    "second",
    "dw",
]


def link_dir(target: Path, source: Path) -> None:
    if target.exists() or target.is_symlink():
        if target.is_dir() and not target.is_symlink():
            # 已是实体目录则跳过
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
        if target.exists():
            print(f"  junction: {target.name} -> {source}")
        else:
            print(f"  copy (junction failed): {target.name}")
            shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        target.symlink_to(source, target_is_directory=True)
        print(f"  symlink: {target.name} -> {source}")


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"  copy: {src.name}")


def main() -> None:
    static = ROOT / "static"
    if not static.is_dir():
        print("缺少 static/，请先运行 mirror_pages.py")
        sys.exit(1)

    if DEPLOY.exists():
        print(f"清理旧目录 {DEPLOY.name}/ ...")
        shutil.rmtree(DEPLOY)

    DEPLOY.mkdir()
    print(f"创建 {DEPLOY.name}/")

    # static 整包
    copy_tree(static, DEPLOY / "static")

    # activity 页面
    activity = ROOT / "activity"
    if activity.is_dir():
        copy_tree(activity, DEPLOY / "activity")
    else:
        print("警告: 无 activity/ 目录")

    # 根路径别名（与 nginx.conf 里 location /assets/ 等等价）
    print("建立资源路径别名:")
    for name in ALIASES:
        src = DEPLOY / "static" / name
        if src.is_dir():
            link_dir(DEPLOY / name, src)
        else:
            print(f"  skip missing: static/{name}")

    sw = DEPLOY / "static" / "sw.produce.min.2.1.6.js"
    if sw.is_file():
        shutil.copy2(sw, DEPLOY / "sw.produce.min.2.1.6.js")
        print("  copy: sw.produce.min.2.1.6.js")

    # 示例 nginx 配置（路径改为 deploy）
    example = (ROOT / "nginx.conf.example").read_text(encoding="utf-8")
    example = example.replace("F:/2026Code/san_pi_03", str(DEPLOY).replace("\\", "/"))
    (DEPLOY / "nginx.conf").write_text(example, encoding="utf-8")

    print(f"\n完成。将 {DEPLOY} 上传到服务器，用其中的 nginx.conf 作参考。")
    print("访问: http://你的域名/activity/Custom/218/")


if __name__ == "__main__":
    main()
