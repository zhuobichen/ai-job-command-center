"""
统一输出层 — 同时支持终端Rich展示和JSON结构化输出
====================================================
用法:
    out = Output(json_mode=False)  # 终端模式
    out = Output(json_mode=True)   # AI模式
    out.print_result({"status": "ok", "jobs": [...]})
"""

import json
import sys
from typing import Any, Optional


class Output:
    """统一输出器：终端 Rich / JSON AI 双模式"""

    def __init__(self, json_mode: bool = False):
        self.json_mode = json_mode
        self._results: list = []  # 累积结果（JSON模式下收集）

    # ─── 基础输出 ─────────────────────────────────────────

    def info(self, msg: str) -> None:
        """信息提示"""
        if self.json_mode:
            self._results.append({"level": "info", "message": msg})
        else:
            from rich.console import Console
            Console().print(f"[cyan]..[/cyan] {msg}")

    def success(self, msg: str) -> None:
        if self.json_mode:
            self._results.append({"level": "success", "message": msg})
        else:
            from rich.console import Console
            Console().print(f"[green]OK[/green] {msg}")

    def warn(self, msg: str) -> None:
        if self.json_mode:
            self._results.append({"level": "warn", "message": msg})
        else:
            from rich.console import Console
            Console().print(f"[yellow]![/yellow] {msg}")

    def error(self, msg: str) -> None:
        if self.json_mode:
            self._results.append({"level": "error", "message": msg})
        else:
            from rich.console import Console
            Console().print(f"[red]X[/red] {msg}")

    def status(self, msg: str) -> None:
        if self.json_mode:
            self._results.append({"level": "status", "message": msg})
        else:
            from rich.console import Console
            Console().print(f"[blue]>[/blue] {msg}")

    # ─── 表格 ─────────────────────────────────────────────

    def table(self, title: str, rows: list, columns: list = None) -> None:
        """显示表格
        Args:
            rows: 行数据列表，每行为 dict
            columns: 列定义列表 [{"key": "title", "label": "岗位"}, ...]
        """
        if self.json_mode:
            self._results.append({"type": "table", "title": title, "rows": rows})
            return
        if not rows:
            from rich.console import Console
            Console().print(f"\n[dim]({title}: 无数据)[/dim]")
            return
        from rich.table import Table
        from rich import box
        cols = columns or [{"key": k, "label": k} for k in rows[0].keys()]
        from rich.console import Console
        t = Table(title=title, box=box.ROUNDED, expand=True)
        for c in cols[:8]:
            t.add_column(c.get("label", c["key"]), style=c.get("style", ""), width=c.get("width", None))
        for row in rows:
            vals = [str(row.get(c["key"], "-"))[:c.get("max_len", 40)] for c in cols[:8]]
            t.add_row(*vals)
        Console().print(t)

    def panel(self, title: str, content: str, style: str = "cyan") -> None:
        if self.json_mode:
            self._results.append({"type": "panel", "title": title, "content": content})
            return
        from rich.console import Console
        from rich.panel import Panel
        Console().print(Panel.fit(content, border_style=style, title=title))

    # ─── 结构化结果 ───────────────────────────────────────

    def result(self, data: dict, success: bool = True) -> None:
        """输出最终结果"""
        if self.json_mode:
            final = {"success": success, **data, "logs": self._results}
            print(json.dumps(final, ensure_ascii=False, indent=2))
        elif data:
            # 终端模式下也打印关键信息
            for k, v in data.items():
                if k in ("status", "count", "total", "summary"):
                    from rich.console import Console
                    Console().print(f"  {k}: {v}")

    def banner(self) -> None:
        if not self.json_mode:
            from rich.console import Console
            Console().print(f"\n[bold cyan]  AI Job Hunt v0.3 — CLI-first, AI-ready[/bold cyan]\n")

    @staticmethod
    def prompt(msg: str, default: str = "", password: bool = False,
               choices: list = None, json_mode: bool = False) -> str:
        """提示用户输入（JSON模式不交互，返回default）"""
        if json_mode:
            return default
        from rich.prompt import Prompt
        if password:
            return Prompt.ask(msg, password=True, default=default) or default
        if choices:
            return Prompt.ask(msg, choices=choices, default=default or choices[0])
        return Prompt.ask(msg, default=default) or default

    @staticmethod
    def confirm(msg: str, default: bool = True, json_mode: bool = False) -> bool:
        """确认操作（JSON模式不交互，返回default）"""
        if json_mode:
            return default
        from rich.prompt import Confirm
        return Confirm.ask(msg, default=default)
