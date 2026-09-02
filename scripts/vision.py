# -*- coding: utf-8 -*-
"""用 DeepSeek 识图模型描述图片(视觉工具保底方案)。
用法: python scripts/vision.py <图片路径> [提示词]
API Key 从环境变量 DEEPSEEK_API_KEY 或 VISION_FALLBACK_API_KEY 读取, 勿硬编码。"""
import base64
import json
import os
import sys
import urllib.request

API_KEY = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("VISION_FALLBACK_API_KEY") or ""
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-flash-vision-exp"

if not API_KEY:
    print("错误: 请设置环境变量 DEEPSEEK_API_KEY 或 VISION_FALLBACK_API_KEY")
    sys.exit(1)

img_path = sys.argv[1]
PROMPTS = {
    "html": "评估这个页面的视觉设计是否美观、专业，配色和排版如何。简短回答。",
    "default": "请用中文详细描述这张图片的内容，包括文字、人物、场景、物体等所有可见元素。",
}
prompt = PROMPTS.get(sys.argv[2] if len(sys.argv) > 2 else "default")

data = base64.b64encode(open(img_path, "rb").read()).decode()
body = json.dumps({
    "model": MODEL,
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": [
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}},
        {"type": "text", "text": prompt},
    ]}],
}).encode()

req = urllib.request.Request(API_URL, data=body, headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
})
try:
    resp = urllib.request.urlopen(req, timeout=60)
    d = json.loads(resp.read())
    print(d["choices"][0]["message"]["content"])
except urllib.error.HTTPError as e:
    print("HTTP错误", e.code, ":", e.read().decode()[:300])
except Exception as e:
    print("ERR:", str(e)[:150])
