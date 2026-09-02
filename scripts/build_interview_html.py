#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""面试准备手册 → 精美 HTML(可折叠问答 + 目录 + 打印友好)。
用法: python scripts/build_interview_html.py
输入: docs/项目资料/面试准备.md
输出: output/面试准备.html
"""
import re
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "项目资料" / "面试准备.md"
OUT = ROOT / "output" / "面试准备.html"

CSS = """
:root {
  --bg: #f4f6fb; --card: #fff; --text: #2b3445; --muted: #6b7280;
  --primary: #176B87; --accent: #ff8a5c; --line: #e6ebf2;
  --qa-bg: #f0f6fa; --shadow: 0 2px 10px rgba(23,107,135,.06);
}
* { margin:0; padding:0; box-sizing:border-box; }
body {
  font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
  background: var(--bg); color: var(--text); line-height: 1.7; font-size: 15px;
}
.container { max-width: 860px; margin: 0 auto; padding: 24px 20px 80px; }

/* 头部 */
.hero {
  background: linear-gradient(135deg, #176B87 0%, #22a39f 100%);
  color: #fff; border-radius: 14px; padding: 32px 34px; margin-bottom: 24px;
  box-shadow: var(--shadow);
}
.hero h1 { font-size: 26px; margin-bottom: 6px; }
.hero p { opacity: .92; font-size: 13.5px; }
.hero .tag {
  display: inline-block; background: rgba(255,255,255,.18); border-radius: 20px;
  padding: 3px 14px; font-size: 12px; margin-top: 12px; margin-right: 6px;
}

/* 目录 */
.toc {
  background: var(--card); border-radius: 12px; padding: 18px 22px;
  margin-bottom: 24px; box-shadow: var(--shadow); position: sticky; top: 12px; z-index: 10;
}
.toc b { color: var(--primary); font-size: 13px; display:block; margin-bottom: 8px; }
.toc a {
  display: inline-block; color: var(--muted); text-decoration: none; font-size: 13px;
  margin-right: 12px; margin-bottom: 4px; border-bottom: 1px dashed transparent;
}
.toc a:hover { color: var(--primary); border-color: var(--primary); }

/* 分区 */
section { margin-bottom: 30px; }
h2 {
  font-size: 21px; color: var(--primary); margin: 8px 0 14px;
  padding-left: 12px; border-left: 4px solid var(--accent);
}
h3 {
  font-size: 16.5px; color: #1f2937; margin: 22px 0 8px; padding: 10px 16px;
  background: var(--card); border-radius: 10px; box-shadow: var(--shadow);
  border-left: 3px solid var(--primary);
}
p { margin-bottom: 10px; }
ul, ol { margin: 6px 0 12px 20px; }
li { margin-bottom: 4px; }
blockquote {
  border-left: 3px solid var(--accent); background: #fff7f2; padding: 10px 16px;
  border-radius: 0 8px 8px 0; margin: 10px 0; color: #5c4a3d; font-size: 14px;
}
code { background: #eef2f7; padding: 1px 6px; border-radius: 4px; font-size: 13px; }
strong { color: #1f2937; }

/* 问答折叠 */
details.qa {
  background: var(--card); border-radius: 10px; margin-bottom: 10px;
  box-shadow: var(--shadow); overflow: hidden; border: 1px solid var(--line);
}
details.qa summary {
  cursor: pointer; padding: 12px 16px; font-weight: 600; color: #1f2937;
  list-style: none; display: flex; align-items: center; gap: 8px; font-size: 14.5px;
  user-select: none;
}
details.qa summary::-webkit-details-marker { display: none; }
details.qa summary::before {
  content: "▸"; color: var(--primary); font-size: 14px; transition: transform .15s;
}
details.qa[open] summary::before { transform: rotate(90deg); }
details.qa summary:hover { background: var(--qa-bg); }
details.qa .ans { padding: 0 16px 14px; font-size: 14.5px; color: var(--text); }
details.qa .ans p:last-child { margin-bottom: 0; }

/* 页脚 */
.footer { text-align:center; color: var(--muted); font-size: 12.5px; margin-top: 40px; }

@media print {
  body { background:#fff; font-size: 12.5px; }
  .hero, .toc { box-shadow:none; }
  .toc { position: static; }
  details.qa { box-shadow:none; break-inside: avoid; }
  details.qa summary { color:#1f2937; font-weight:700; }
  details.qa .ans { display:block !important; }
  details.qa summary::before { content:""; }
}
"""


def render_inline(text: str) -> str:
    """转行内 markdown(粗体/代码/链接)。"""
    t = text.replace("**", "\x00").strip()
    # 简单粗体处理
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


def build() -> None:
    text = SRC.read_text(encoding="utf-8")
    lines = text.split("\n")
    body = []
    toc = []
    section_id = 0

    def flush_block(block_lines, is_ans=False):
        if not block_lines:
            return ""
        md = "\n".join(block_lines)
        return markdown.markdown(md, extensions=["sane_lists"])

    i = 0
    n = len(lines)
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s == "---":
            i += 1
            continue
        # H1
        if s.startswith("# "):
            body.append(f"<h1>{render_inline(s[2:])}</h1>")
            i += 1
            continue
        # H2 -> section
        if s.startswith("## "):
            section_id += 1
            title = s[3:].strip()
            body.append(f'<section id="sec{section_id}"><h2>{render_inline(title)}</h2>')
            toc.append(f'<a href="#sec{section_id}">{title}</a>')
            i += 1
            continue
        # H3 -> 项目/子块
        if s.startswith("### "):
            body.append(f"<h3>{render_inline(s[4:])}</h3>")
            i += 1
            continue
        # 问答 Q
        m = re.match(r"\*\*(Q\d*[：:].*?)\*\*", s)
        if m:
            q = m.group(1)
            ans = []
            i += 1
            while i < n:
                ns = lines[i].strip()
                if (ns.startswith("**Q") or ns.startswith("#")
                        or ns == "---" or not ns and _is_next_qa(lines, i)):
                    break
                if not ns and _is_next_qa(lines, i):
                    break
                ans.append(lines[i])
                i += 1
            # 去掉答案块首尾空行
            while ans and not ans[0].strip():
                ans.pop(0)
            while ans and not ans[-1].strip():
                ans.pop()
            body.append(
                f'<details class="qa"><summary>{render_inline(q)}</summary>'
                f'<div class="ans">{flush_block(ans)}</div></details>')
            continue
        # 普通块
        block = []
        while i < n:
            ns = lines[i].strip()
            if (ns.startswith("**Q") or ns.startswith("#")
                    or ns == "---"):
                break
            block.append(lines[i])
            i += 1
        body.append(flush_block(block))

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>面试准备手册</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
  <div class="hero">
    <h1>🎯 面试准备手册</h1>
    <p>基于 v9 简历定制 · 环境数据融合 + 软件开发 + AI 应用 · 投递前系统准备</p>
    <span class="tag">自我介绍</span><span class="tag">项目问答</span>
    <span class="tag">技术/专业</span><span class="tag">行为面试</span><span class="tag">Checklist</span>
  </div>
  <nav class="toc"><b>📑 目录</b>{''.join(toc)}</nav>
  {''.join(body)}
  <div class="footer">Generated {__import__('datetime').date.today()} · 面试准备手册</div>
</div>
</body>
</html>"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"[OK] HTML -> {OUT}")


def _is_next_qa(lines, i):
    """判断下一行是否是新的问答块。"""
    for j in range(i, len(lines)):
        ns = lines[j].strip()
        if not ns:
            continue
        return ns.startswith("**Q") or ns.startswith("#") or ns == "---"
    return True


if __name__ == "__main__":
    build()
