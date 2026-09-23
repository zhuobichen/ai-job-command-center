# -*- coding: utf-8 -*-
"""CDP proxy 助手 — 用 base64 传 JS 规避 Windows/GBK 编码问题。

用法:
  python scripts/cdp.py <target> eval <base64的JS>
  python scripts/cdp.py <target> text [maxlen]      页面文本
  python scripts/cdp.py <target> goto <url>         导航
  python scripts/cdp.py <target> click <selector>   点击
  python scripts/cdp.py <target> shot <file>        截图
"""
import base64
import json
import sys
import urllib.parse
import urllib.request

BASE = "http://localhost:3456"


def _req(endpoint, params=None, data=None):
    qs = urllib.parse.urlencode(params or {})
    url = f"{BASE}/{endpoint}" + (f"?{qs}" if qs else "")
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")


def main():
    target = sys.argv[1]
    cmd = sys.argv[2]

    if cmd == "eval":
        js = base64.b64decode(sys.argv[3]).decode("utf-8")
        print(_req("eval", {"target": target}, js.encode("utf-8")))
    elif cmd == "text":
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
        js = f"document.body.innerText.slice(0,{n})"
        print(_req("eval", {"target": target}, js.encode("utf-8")))
    elif cmd == "html":
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
        js = f"document.documentElement.outerHTML.slice(0,{n})"
        print(_req("eval", {"target": target}, js.encode("utf-8")))
    elif cmd == "goto":
        print(_req("navigate", {"target": target, "url": sys.argv[3]}))
    elif cmd == "click":
        sel = base64.b64decode(sys.argv[3]).decode("utf-8")
        print(_req("eval", {"target": target},
                   f"(()=>{{const e=document.querySelector({json.dumps(sel)}); if(!e)return 'not found'; e.click(); return 'clicked';}})()".encode("utf-8")))
    elif cmd == "shot":
        print(_req("screenshot", {"target": target, "file": sys.argv[3]}))
    else:
        print("unknown cmd")


if __name__ == "__main__":
    main()
