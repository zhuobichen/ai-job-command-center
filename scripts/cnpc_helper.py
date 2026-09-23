# -*- coding: utf-8 -*-
"""中石油网申表单操作 helper — 避免 JS 转义问题。
用法: python scripts/cnpc_helper.py <mode> [args]
mode:
  targets            列出中石油标签页
  clickbtn <文字>     点击含指定文字的按钮/a
  clickid <id>       点击指定 id 元素
  setval <id> <值>    设置输入框值(触发事件)
  setdate <id> <日期> 用 datetimepicker API 设置日期 (YYYY-MM-DD)
  getval <id>        读取值
  state              页面概况
  edu                教育背景表单状态
  errors             查找错误提示
"""
import json
import sys
import urllib.parse
import urllib.request

BASE = "http://localhost:3456"


def find_target():
    d = json.loads(urllib.request.urlopen(f"{BASE}/targets", timeout=10).read())
    for t in d:
        if "cnpc" in (t.get("url") or "") and "createResume" in (t.get("url") or ""):
            return t["targetId"]
    return None


def ev(js, target=None):
    target = target or find_target()
    if not target:
        return "无中石油标签页"
    url = f"{BASE}/eval?target=" + urllib.parse.quote(target)
    req = urllib.request.Request(url, data=js.encode("utf-8"), method="POST")
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")


def click_at(selector, target=None):
    """真实鼠标点击（CDP Input.dispatchMouseEvent），能触发文件对话框等。"""
    target = target or find_target()
    url = f"{BASE}/clickAt?target=" + urllib.parse.quote(target)
    req = urllib.request.Request(url, data=selector.encode("utf-8"), method="POST")
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "state"

    if mode == "openform":
        # 找"添加XX"按钮 → 滚到视口中央 → 等滚动完成 → 真实点击
        import time as _t
        txt = sys.argv[2]
        js = (
            "(()=>{"
            "const bs=[...document.querySelectorAll('a,button,div,span')].filter(function(e){"
            "  return e.offsetParent && e.textContent.replace(/[+ \\s]+/g,'')=== " + json.dumps(txt) + " && e.children.length<=2;"
            "});"
            "if(!bs.length) return 'not-found';"
            "const b=bs[bs.length-1]; b.id='zzTarget';"
            "b.scrollIntoView({block:'center'});"
            "return 'marked:'+b.tagName;})()"
        )
        r = ev(js)
        print("标记:", r[:100])
        if "marked" in r:
            _t.sleep(1.5)  # 等滚动完成
            print("点击:", click_at("#zzTarget")[:200])
        sys.exit(0)

    if mode == "targets":
        d = json.loads(urllib.request.urlopen(f"{BASE}/targets", timeout=10).read())
        for t in d:
            print(t["targetId"], "|", (t.get("title") or "")[:30], "|", (t.get("url") or "")[:60])

    elif mode == "clickbtn":
        txt = sys.argv[2]
        js = (
            "(()=>{const t=" + json.dumps(txt) + ";"
            "const bs=[...document.querySelectorAll('a,button')].filter(e=>e.offsetParent);"
            "const b=bs.find(e=>e.textContent.replace(/[ \\t\\n]+/g,'').indexOf(t)>=0);"
            "if(!b) return 'not-found'; b.click(); return 'clicked:'+b.textContent.trim().slice(0,15);})()"
        )
        print(ev(js))

    elif mode == "clickid":
        eid = sys.argv[2]
        print(ev("(()=>{const e=document.getElementById(" + json.dumps(eid) + "); if(!e) return 'nf'; e.click(); return 'clicked';})()"))

    elif mode == "setval":
        eid, val = sys.argv[2], sys.argv[3]
        js = (
            "(()=>{const e=document.getElementById(" + json.dumps(eid) + "); if(!e) return 'nf';"
            "const proto=e.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;"
            "const s=Object.getOwnPropertyDescriptor(proto,'value').set; s.call(e," + json.dumps(val) + ");"
            "e.dispatchEvent(new Event('input',{bubbles:true}));"
            "e.dispatchEvent(new Event('change',{bubbles:true}));"
            "return 'ok:'+e.value;})()"
        )
        print(ev(js))

    elif mode == "setdate":
        eid, val = sys.argv[2], sys.argv[3]
        y, m, d = val.split("-")
        js = (
            "(()=>{const jq=window.jQuery; if(typeof jq!=='function') return 'no-jq';"
            "const el=document.getElementById(" + json.dumps(eid) + ");"
            "const dp=jq(el).data('datetimepicker'); if(!dp) return 'no-instance';"
            "dp.setDate(new Date(" + str(int(y)) + "," + str(int(m) - 1) + "," + str(int(d)) + "));"
            "return 'set:'+el.value;})()"
        )
        print(ev(js))

    elif mode == "getval":
        eid = sys.argv[2]
        js = (
            "(()=>{const e=document.getElementById(" + json.dumps(eid) + "); if(!e) return 'nf';"
            "return e.tagName==='SELECT' ? (e.options[e.selectedIndex]||{}).text : e.value;})()"
        )
        print(ev(js))

    elif mode == "state":
        js = (
            "(()=>{const t=document.body.innerText;"
            "const forms=[...document.querySelectorAll('form')].filter(e=>e.offsetParent).map(e=>e.id||'no-id');"
            "return JSON.stringify({url:location.href.slice(-40), h:document.documentElement.scrollHeight, visibleForms:forms});})()"
        )
        print(ev(js))

    elif mode == "errors":
        js = (
            "(()=>{const ds=[...document.querySelectorAll('div')].filter(e=>{const x=e.textContent||'';"
            "return e.offsetParent && x.length<130 && (x.indexOf('请选择')>=0||x.indexOf('请填写')>=0||x.indexOf('不能')>=0||x.indexOf('最多')>=0||x.indexOf('请上传')>=0);});"
            "return ds.slice(0,5).map(e=>e.textContent.replace(/[ \\t\\n]+/g,' ').trim().slice(0,70)).join('  ||  ')||'无错误提示';})()"
        )
        print(ev(js))

    elif mode == "edu":
        js = (
            "(()=>{const f=document.getElementById('resumeEducation');"
            "const g=(id)=>{const e=document.getElementById(id); return e?(e.tagName==='SELECT'?(e.options[e.selectedIndex]||{}).text:(e.value||'(空)')):'-';};"
            "return JSON.stringify({表单存在:!!f, 可见:f?f.offsetParent!==null:false,"
            "省:g('province'), 校:g('schoolCode'), 入学:g('educationStartDate'), 学位:g('xw'),"
            "毕业:g('educationEndDate'), 学历:g('xl'), 专业:g('major'), 绩点:g('gradePointType')});})()"
        )
        print(ev(js))

    else:
        print("unknown mode:", mode)
