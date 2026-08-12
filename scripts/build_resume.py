#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简历构建脚本 — md 单源，一键生成成品 MD + PDF

用法:
    python scripts/build_resume.py              # 用默认源文件
    python scripts/build_resume.py <md路径>     # 指定其他源 md

源文件(唯一维护源):
    docs/项目资料/简历-正式版.md

输出:
    output/简历.md     成品 markdown(可直接投递/分享)
    output/简历.pdf    排版好的 A4 PDF(微软雅黑, 蓝色主题)

依赖:
    markdown, PyMuPDF (fitz)  — 均已安装, 无需额外依赖
"""
import re
import sys
from pathlib import Path

import fitz
import markdown

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "项目资料" / "简历-正式版.md"
OUT_MD = ROOT / "output" / "简历.md"
OUT_PDF = ROOT / "output" / "简历.pdf"

# Windows 微软雅黑(正文 / 加粗标题)
FONT_BODY = r"C:\Windows\Fonts\msyh.ttc"
FONT_HEAD = r"C:\Windows\Fonts\msyhbd.ttc"
# WonderCV 风格: 宋体(衬线)正文 / 黑体加粗标题
WONDER_BODY = r"C:\Windows\Fonts\simsun.ttc"
WONDER_HEAD = r"C:\Windows\Fonts\simsunb.ttf"

CSS = """
@font-face {{ font-family: "MSYH"; src: url("{body}"); }}
@font-face {{ font-family: "MSYH-Bold"; src: url("{head}"); }}
body {{ font-family: "MSYH"; font-size: 10pt; line-height: 1.55; color: #35424B; }}
h1 {{ font-family: "MSYH-Bold"; font-size: 22pt; color: #1F2933; margin: 0 0 2pt 0; }}
h1 + p {{ color: #64727C; font-size: 9.5pt; margin-bottom: 6pt; }}
h2 {{ font-family: "MSYH-Bold"; font-size: 12.5pt; color: #176B87;
     border-bottom: 1.2pt solid #176B87; padding-bottom: 3pt;
     margin: 13pt 0 6pt 0; }}
h3 {{ font-family: "MSYH-Bold"; font-size: 11pt; color: #1F2933;
     margin: 10pt 0 2pt 0; }}
p  {{ margin: 0 0 4pt 0; }}
strong {{ font-family: "MSYH-Bold"; color: #64727C; font-weight: bold; }}
ul {{ margin: 2pt 0 6pt 0; padding-left: 16pt; }}
li {{ margin-bottom: 2.5pt; }}
li strong {{ color: #35424B; }}
table {{ border-collapse: collapse; width: 100%; margin: 4pt 0; }}
th, td {{ border: 0.5pt solid #DCE5E8; padding: 3pt 6pt; font-size: 9.5pt; }}
th {{ background: #F3F6F7; font-family: "MSYH-Bold"; }}
"""

# A4 页边距(pt): 左/右 18mm≈51pt, 上 15mm≈42.5pt, 下 14mm≈39.7pt
MARGIN_L, MARGIN_T, MARGIN_R, MARGIN_B = 51, 42.5, 51, 39.7
# WonderCV 风格边距更紧凑(左/右≈34pt)
WONDER_MARGIN_L, WONDER_MARGIN_T, WONDER_MARGIN_R, WONDER_MARGIN_B = 34, 40, 34, 36

# 简历证件照(右上角)
PHOTO = ROOT / "docs" / "项目资料" / "简历照片.jpg"
PHOTO_W, PHOTO_H = 78, 102  # 证件照比例约 2.7cm x 3.6cm


def insert_photo(pdf: Path, style: str) -> None:
    """在简历第一页右上角插入证件照(增量保存)。"""
    if not PHOTO.exists():
        return
    doc = fitz.open(str(pdf))
    page = doc[0]
    mr = WONDER_MARGIN_R if style == "wonder" else MARGIN_R
    mt = WONDER_MARGIN_T if style == "wonder" else MARGIN_T
    x1 = page.rect.width - mr - 10
    x0 = x1 - PHOTO_W
    y0 = mt - 8
    y1 = y0 + PHOTO_H
    page.insert_image(fitz.Rect(x0, y0, x1, y1), filename=str(PHOTO))
    doc.saveIncr()
    doc.close()

# WonderCV「智能一页」模板风格: 宋体衬线 + 蓝色分区标题(#4A8CFF) + 浅色分隔线 + 紧凑排版
WONDER_CSS = """
@font-face {{ font-family: "Song"; src: url("{body}"); }}
@font-face {{ font-family: "SongBold"; src: url("{head}"); }}
body {{ font-family: "Song"; font-size: 10.5pt; line-height: 1.52; color: #1A1A1A; }}
h1 {{ font-family: "SongBold"; font-size: 22pt; color: #111; margin: 0 0 2pt 0; }}
h1 + p {{ color: #444; font-size: 10pt; margin-bottom: 8pt; }}
h2 {{ font-family: "SongBold"; font-size: 13pt; color: #4A8CFF;
     border-bottom: 1px solid #E5EDF9; padding-bottom: 3pt;
     margin: 15pt 0 6pt 0; }}
h3 {{ font-family: "SongBold"; font-size: 11pt; color: #111; margin: 9pt 0 2pt 0; }}
p  {{ margin: 0 0 3pt 0; }}
strong {{ font-family: "SongBold"; color: #555; font-weight: bold; }}
ul {{ margin: 1pt 0 5pt 0; padding-left: 14pt; }}
li {{ margin-bottom: 1.5pt; }}
"""


def build_md() -> Path:
    """复制源 md 到 output 作为成品。"""
    OUT_MD.write_text(SRC.read_text(encoding="utf-8"), encoding="utf-8")
    return OUT_MD


def build_pdf(style: str = "normal") -> Path:
    """markdown -> HTML -> PyMuPDF Story -> PDF(自动分页)。"""
    md_text = SRC.read_text(encoding="utf-8")
    html_body = markdown.markdown(md_text, extensions=["tables", "nl2br"])
    if style == "wonder":
        css = WONDER_CSS.format(
            body=WONDER_BODY.replace("\\", "/"), head=WONDER_HEAD.replace("\\", "/"))
        ml, mt, mr, mb = WONDER_MARGIN_L, WONDER_MARGIN_T, WONDER_MARGIN_R, WONDER_MARGIN_B
        # 项目标题行 → 左标题 + 右时间(右对齐), 角色单列
        # 注: fitz Story 对 CSS class 支持有限, 必须用内联 style
        def _proj(m):
            title, meta = m.group(1), m.group(2)
            tm = re.search(r"\|\s*([^|]+)$", meta)
            if tm:
                time_, role = tm.group(1).strip(), meta[: tm.start()].rstrip(" |").strip()
            else:
                time_, role = "", meta.strip()
            return (f'<table style="width:100%;border-collapse:collapse;margin:9pt 0 0 0;"><tr>'
                    f'<td style="width:75%;border:none;padding:0;text-align:left;font-family:SongBold;'
                    f'font-size:11pt;color:#111;font-weight:bold;">{title}</td>'
                    f'<td style="width:25%;border:none;padding:0;text-align:right;font-size:9.5pt;'
                    f'color:#555;white-space:nowrap;">{time_}</td></tr></table>'
                    f'<div style="color:#555;font-size:10pt;margin:1pt 0 3pt 0;">{role}</div>')
        html_body = re.sub(r"<h3>(.*?)</h3>\s*<p><strong>(.*?)</strong></p>",
                           _proj, html_body, flags=re.S)
    else:
        # 反斜杠在 CSS 里是转义符, 字体路径统一用正斜杠
        css = CSS.format(body=FONT_BODY.replace("\\", "/"), head=FONT_HEAD.replace("\\", "/"))
        ml, mt, mr, mb = MARGIN_L, MARGIN_T, MARGIN_R, MARGIN_B

    # 在 html_body 全部处理后(含 wonder 的项目标题替换)再组装完整 HTML
    html = f'<html><head><meta charset="utf-8"></head><body>{html_body}</body></html>'

    # 先渲染到 tmp 中间文件, 避免 Windows 下覆盖正式输出时的文件锁问题
    import gc
    import time

    raw = ROOT / "tmp" / (OUT_PDF.stem + "_raw.pdf")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.unlink(missing_ok=True)  # 清除上次残留(跨进程后已解锁)
    story = fitz.Story(html=html, user_css=css)
    writer = fitz.DocumentWriter(str(raw))
    media = fitz.paper_rect("a4")
    body = media + (ml, mt, -mr, -mb)
    while True:
        dev = writer.begin_page(media)
        more, _ = story.place(body)
        story.draw(dev)
        writer.end_page()
        if not more:
            break
    writer.close()

    # 压缩: 完整嵌入的中文字体很大(数十MB), 子集化 + 垃圾回收 + 压缩流
    doc = fitz.open(str(raw))
    doc.subset_fonts()
    doc.save(str(OUT_PDF), garbage=4, deflate=True)
    doc.close()
    gc.collect()
    for _ in range(3):  # Windows 句柄延迟释放, 重试删除中间文件
        try:
            raw.unlink(missing_ok=True)
            break
        except PermissionError:
            time.sleep(0.3)
    return OUT_PDF


def main() -> None:
    global SRC, OUT_MD, OUT_PDF
    style = "normal"
    args = sys.argv[1:]
    if "--style" in args:
        i = args.index("--style")
        style = args[i + 1] if i + 1 < len(args) else "normal"
        args = args[:i] + args[i + 2:]
    if args:
        SRC = Path(args[0]).resolve()
        OUT_MD = ROOT / "output" / f"{SRC.stem}.md"
        OUT_PDF = ROOT / "output" / f"{SRC.stem}.pdf"

    if not SRC.exists():
        print(f"[!] 源文件不存在: {SRC}")
        sys.exit(1)

    if style == "wonder":
        OUT_PDF = OUT_PDF.with_name(OUT_PDF.stem + "_wonder.pdf")

    md = build_md()
    pdf = build_pdf(style)
    insert_photo(pdf, style)
    print(f"[OK] MD  -> {md}")
    print(f"[OK] PDF -> {pdf}  (style: {style}{', 含证件照' if PHOTO.exists() else ''})")


if __name__ == "__main__":
    main()
