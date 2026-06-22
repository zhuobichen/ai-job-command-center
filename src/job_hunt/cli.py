"""
AI智慧求职系统 - CLI入口 (v0.3)
=================================
纯CLI、AI驱动、双模式输出（终端Rich / JSON AI-ready）

用法:
  job-hunt init              AI引导初始化
  job-hunt scan -k "Python"  扫描岗位
  job-hunt auto -k "Python"  全自动流水线
  job-hunt match             智能匹配
  job-hunt eval <id>         A-G深度评估
  job-hunt resume <id>       生成简历
  job-hunt apply <id>        智能投递
  job-hunt status            投递状态
  job-hunt report            生成报告
  job-hunt config <op>       配置管理
  job-hunt pipeline <op>     管道管理
  job-hunt filter <op>       黑名单
  job-hunt verify <公司>     公司验证
  job-hunt parse <文件>      简历解析

AI模式（JSON输出，非交互）:
  job-hunt scan -k "Python" -c 南宁 --json --yes
  job-hunt auto -k "Python" -c 广西 --json --yes
  job-hunt match --json --yes
"""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Optional

import typer

from . import __version__
from .db.database import Database
from .utils.config import Config
from .utils.output import Output

# ─── 全局状态 ───────────────────────────────────────────
_db: Optional[Database] = None
_config: Optional[Config] = None
_brain: Optional = None
_out: Optional[Output] = None
_json_mode: bool = False
_yes_mode: bool = False

app = typer.Typer(name="job-hunt", help="AI Job Hunt - CLI-first, AI-ready", no_args_is_help=True, pretty_exceptions_enable=False)


def _setup(json_mode: bool = False, yes_mode: bool = False) -> Output:
    global _out, _json_mode, _yes_mode
    _json_mode = json_mode
    _yes_mode = yes_mode
    _out = Output(json_mode=json_mode)
    return _out


def _json() -> bool: return _json_mode
def _yes() -> bool: return _yes_mode
def _out() -> Output: return _out


def _db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


def _cfg() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config


def _brain():
    global _brain
    if _brain is None:
        try:
            from .ai.brain import AIBrain
            _brain = AIBrain(_cfg())
        except ImportError as e:
            _out().error(f"AI模块不可用: {e}")
            raise typer.Exit(1)
    return _brain


def _check_ai() -> None:
    if not _cfg().is_configured:
        _out().error("AI未配置，请先运行: job-hunt init")
        raise typer.Exit(1)

# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="版本号"),
):
    if version:
        print(f"job-hunt v{__version__}")
        return
    if ctx.invoked_subcommand is None:
        _out().banner()
        _out().info("输入 job-hunt --help 查看所有命令")
        _out().info("AI模式: job-hunt <cmd> --json --yes")

# ═══════════════════════════════════════════════════════════
# Init
# ═══════════════════════════════════════════════════════════

@app.command()
def init(
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON输出（AI模式）"),
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过交互，使用默认值"),
):
    """🚀 AI引导式初始化（非交互模式用 -y 跳过）"""
    out = _setup(json_mode, yes)
    cfg = _cfg()
    db = _db()
    out.banner()

    # Step 1: AI Key
    if not yes:
        from rich.prompt import Prompt
        provider = Prompt.ask("AI提供商", choices=["deepseek","openai","qwen","custom"], default="deepseek")
        cfg.set("ai", "provider", provider)
        model = Prompt.ask("模型", default="deepseek-chat")
        cfg.set("ai", "model", model)
        api_key = Prompt.ask("API Key", password=True, default=cfg.get("ai","api_key",""))
        cfg.set("ai", "api_key", api_key)
        out.success("AI配置完成")

        # Step 2: 简历
        resume_path = Prompt.ask("简历路径(PDF/DOCX/TXT，可跳过)", default="")
        if resume_path and os.path.exists(resume_path):
            try:
                brain = _brain()
                raw = _read_file(resume_path)
                parsed = brain.parse_resume(raw)
                from .models.resume import Resume
                r = Resume(
                    name=parsed.get("name",""), phone=parsed.get("phone",""), email=parsed.get("email",""),
                    education_level=parsed.get("education_level",""), university=parsed.get("university",""),
                    major=parsed.get("major",""), skills=parsed.get("skills",""),
                    desired_city=parsed.get("desired_city",""), desired_position=parsed.get("desired_position",""),
                    salary_min=parsed.get("salary_min",0), salary_max=parsed.get("salary_max",0),
                    raw_text=raw[:5000], raw_file_path=resume_path,
                )
                db.save_resume(r)
                out.success(f"简历解析: {r.summary()}")
            except Exception as e:
                out.warn(f"简历解析失败: {e}")

        # Step 3: 求职意向
        cities = Prompt.ask("意向城市", default="南宁,广州")
        cfg.set("preferences", "cities", cities)
        pos = Prompt.ask("意向岗位", default="")
        cfg.set("preferences", "position", pos)
        keywords = Prompt.ask("搜索关键词", default=cfg.get("scanner","keywords","Python 开发,数据分析"))
        cfg.set("scanner", "keywords", keywords)
        out.success(f"求职画像: {cities} | {pos} | {keywords}")

    # Step 4: 保存最终配置
    out.success("初始化完成")
    out.result({
        "status": "initialized",
        "ai_configured": cfg.is_configured,
        "cities": cfg.get("preferences","cities"),
        "keywords": cfg.get("scanner","keywords"),
        "next": "job-hunt scan --json --yes  # 开始扫描"
    }, success=True)


def _read_file(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        try:
            from PyPDF2 import PdfReader
            return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
        except ImportError:
            with open(path, "rb") as f: return f.read().decode("utf-8", errors="ignore")
    elif ext in (".docx", ".doc"):
        try:
            from docx import Document
            return "\n".join(p.text for p in Document(path).paragraphs)
        except ImportError:
            with open(path, "rb") as f: return f.read().decode("utf-8", errors="ignore")
    else:
        with open(path, "r", encoding="utf-8") as f: return f.read()

# ═══════════════════════════════════════════════════════════
# Scan
# ═══════════════════════════════════════════════════════════

@app.command()
def scan(
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="搜索关键词"),
    city: Optional[str] = typer.Option(None, "--city", "-c", help="城市筛选"),
    platform: str = typer.Option("gxrc", "--platform", "-p", help="平台: gxrc/guipin/boss/all"),
    max_pages: int = typer.Option(3, "--pages", "-n", help="每站最大页数"),
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON输出"),
    yes: bool = typer.Option(False, "--yes", "-y", help="非交互模式"),
    debug: bool = typer.Option(False, "--debug", help="保存调试HTML"),
):
    """🔍 扫描招聘平台抓取岗位"""
    out = _setup(json_mode, yes)
    _check_ai(); cfg = _cfg(); db = _db()

    city = city or cfg.cities or ""
    keyword = keyword or cfg.keywords
    if not keyword:
        out.error("请指定 --keyword")
        raise typer.Exit(1)

    out.banner()
    _city_tiers = _parse_cities(city)
    out.status(f"扫描: {keyword} | {city or '全国'} | {platform}")

    if platform == "all": targets = ["gxrc", "guipin", "boss", "bing"]
    else: targets = [platform]

    all_jobs = []
    for plat in targets:
        jobs = _run_scraper(plat, keyword, city, max_pages, debug, out)
        saved = 0
        for j in jobs:
            if j.title:
                db.save_job(j); saved += 1; all_jobs.append(j)
        if jobs:
            out.success(f"{plat}: {saved}条")

    total = db.get_job_count()
    out.result({
        "new": len(all_jobs), "total_in_db": total,
        "keyword": keyword, "city": city, "platform": platform,
        "jobs": [_job_dict(j) for j in all_jobs[:20]],
        "next": "job-hunt match --json --yes",
    }, success=True)


def _run_scraper(plat: str, keyword: str, city: str, pages: int, debug: bool, out: Output):
    if plat == "gxrc":
        from .scrapers.gxrc import GxrcScraper
        async def _go():
            s = GxrcScraper(headless=True, debug=debug)
            try: return await s.search(keyword=keyword, city=city, max_pages=pages)
            finally: await s.close()
        try: return asyncio.run(_go())
        except Exception as e: out.warn(f"gxrc: {e}"); return []
    elif plat == "guipin":
        from .scrapers.guipin import GuiPinScaper
        try:
            s = GuiPinScaper(debug=debug)
            try: return s.search(keyword=keyword, city=city, max_pages=pages)
            finally: s.close()
        except Exception as e: out.warn(f"guipin: {e}"); return []
    elif plat == "boss":
        from .scrapers.boss import BossScraper
        async def _go():
            s = BossScraper(headless=True)
            try: return await s.search(keyword=keyword, city=city, max_pages=pages)
            finally: await s.close()
        try: return asyncio.run(_go())
        except Exception as e: out.warn(f"boss: {e}"); return []
    elif plat == "bing":
        from .scrapers.bing import bing_job_search
        try: return bing_job_search(keyword=keyword, city=city, max_results=pages*5)
        except Exception as e: out.warn(f"bing: {e}"); return []
    return []

# ═══════════════════════════════════════════════════════════
# Match
# ═══════════════════════════════════════════════════════════

@app.command()
def match(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="匹配数量"),
    min_score: float = typer.Option(0, "--min-score", "-m", help="最低匹配度0-100"),
    city: Optional[str] = typer.Option(None, "--city", "-c", help="城市筛选"),
    json_mode: bool = typer.Option(False, "--json", "-j"),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """🎯 AI智能匹配岗位"""
    out = _setup(json_mode, yes)
    _check_ai(); db = _db(); brain = _brain(); cfg = _cfg()

    resume = db.get_resume()
    if not resume:
        out.error("无简历，请先 job-hunt init")
        raise typer.Exit(1)

    city = city or cfg.cities or ""
    jobs = db.get_jobs(limit=limit or 200, city=city, active_only=True)
    unrated = [j for j in jobs if j.match_score == 0]
    if not unrated:
        rated = sorted([j for j in jobs if j.match_score>=min_score], key=lambda j: j.match_score, reverse=True)
        out.result({"matched": len(rated), "jobs": [_job_dict(j) for j in rated[:30]]})
        return

    out.status(f"匹配 {len(unrated)} 个岗位...")
    resume_d = resume.to_dict()
    matched = []
    for i, job in enumerate(unrated, 1):
        try:
            result = brain.match_job(resume_d, job.to_dict())
            score = result.get("match_score", 0)
            db.update_job_match(job.id or 0, score, json.dumps(result, ensure_ascii=False))
            job.match_score = score
            if score >= min_score: matched.append(job)
        except Exception as e:
            out.warn(f"匹配#{i}出错: {e}")

    matched.sort(key=lambda j: j.match_score, reverse=True)
    out.result({
        "total_evaluated": len(unrated), "matched": len(matched),
        "top": [_job_dict(j) for j in matched[:15]],
        "next": "job-hunt eval <id> --json",
    }, success=True)

# ═══════════════════════════════════════════════════════════
# Eval — A-G 八块
# ═══════════════════════════════════════════════════════════

@app.command()
def eval(
    job_id: int = typer.Argument(..., help="岗位ID"),
    json_mode: bool = typer.Option(False, "--json", "-j"),
):
    """📊 A-G八块深度评估"""
    out = _setup(json_mode, False)
    _check_ai(); db = _db(); brain = _brain()

    job = db.get_job_by_id(job_id)
    if not job: out.error(f"岗位#{job_id}不存在"); raise typer.Exit(1)
    resume = db.get_resume()
    if not resume: out.error("无简历"); raise typer.Exit(1)

    out.status(f"A-G评估: {job.title} @ {job.company}")
    result = brain.evaluate_job(job.to_dict(), resume.to_dict())

    score = result.get("overall_score", 0)
    db.update_job_eval(job_id, f"{score}/5.0", json.dumps(result, ensure_ascii=False))

    if not json_mode:
        out.panel(f"Score: {score}/5.0 | {result.get('apply_recommendation','')}", f"{job.title}\n{job.company} | {job.city} | {job.salary_range_display}")
        for block_id, label in [
            ("A_role_summary","A"), ("B_cv_match","B"), ("C_level_strategy","C"),
            ("D_comp","D"), ("E_resume_custom","E"), ("F_interview","F"), ("G_legitimacy","G"),
        ]:
            data = result.get(block_id)
            if data:
                from rich.console import Console
                Console().print(f"\n[bold cyan]{label}[/bold cyan]")
                if isinstance(data, dict):
                    for k, v in data.items():
                        vstr = "; ".join(str(x) for x in v[:3]) if isinstance(v, list) else str(v)[:80]
                        Console().print(f"  [dim]{k}:[/dim] {vstr}")

    out.result({"job_id": job_id, "eval": result, "next": "job-hunt resume {} --json".format(job_id)})

# ═══════════════════════════════════════════════════════════
# Auto — 全自动流水线
# ═══════════════════════════════════════════════════════════

@app.command()
def auto(
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="搜索关键词"),
    city: Optional[str] = typer.Option(None, "--city", "-c", help="城市"),
    platform: str = typer.Option("gxrc", "--platform", "-p"),
    max_pages: int = typer.Option(2, "--pages", "-n"),
    json_mode: bool = typer.Option(False, "--json", "-j"),
    yes: bool = typer.Option(False, "--yes", "-y"),
    min_score: float = typer.Option(50, "--min-score", "-m", help="最低匹配度"),
):
    """⚡ 全自动流水线: scan → match → eval → report"""
    out = _setup(json_mode, yes)
    _check_ai(); cfg = _cfg(); db = _db(); brain = _brain()

    city = city or cfg.cities or ""
    keyword = keyword or cfg.keywords
    if not keyword: out.error("请指定 --keyword"); raise typer.Exit(1)

    out.status(f"[1/4] 扫描: {keyword} | {city}")
    all_jobs = []
    for plat in (platform.split(",") if platform != "all" else ["gxrc","guipin","boss"]):
        jobs = _run_scraper(plat.strip(), keyword, city, max_pages, False, out)
        for j in jobs:
            if j.title and not _is_dup(db, j):
                db.save_job(j); all_jobs.append(j)
    out.success(f"扫描完成: {len(all_jobs)} 新岗位")

    if not all_jobs:
        out.result({"status": "no_new_jobs", "keyword": keyword, "city": city})
        return

    # match
    out.status(f"[2/4] AI匹配 {len(all_jobs)} 个...")
    resume_d = db.get_resume().to_dict() if db.get_resume() else {}
    matched = []
    for job in all_jobs:
        try:
            r = brain.match_job(resume_d, job.to_dict())
            score = r.get("match_score", 0)
            db.update_job_match(job.id or 0, score, json.dumps(r, ensure_ascii=False))
            job.match_score = score
            if score >= min_score: matched.append(job)
        except Exception: pass
    matched.sort(key=lambda j: j.match_score, reverse=True)
    out.success(f"匹配完成: {len(matched)} 个 >= {min_score}%")

    # eval top 10
    out.status(f"[3/4] A-G评估 TOP {min(10, len(matched))}...")
    evals = []
    for job in matched[:10]:
        try:
            er = brain.evaluate_job(job.to_dict(), resume_d)
            db.update_job_eval(job.id or 0, f"{er.get('overall_score',0)}/5.0", json.dumps(er, ensure_ascii=False))
            evals.append({"job": _job_dict(job), "eval": er})
        except Exception: pass
    out.success(f"评估完成: {len(evals)} 个")

    # report
    out.status(f"[4/4] 生成报告...")
    report_path = _generate_report(db, matched[:20], evals, keyword, city)
    out.success(f"报告: {report_path}")

    out.result({
        "status": "done",
        "scanned": len(all_jobs),
        "matched": len(matched),
        "evaluated": len(evals),
        "keyword": keyword, "city": city,
        "top_jobs": [e["job"] for e in evals[:5]],
        "evals": evals,
        "report": report_path,
    }, success=True)


# ═══════════════════════════════════════════════════════════
# Resume
# ═══════════════════════════════════════════════════════════

@app.command()
def resume(
    job_id: int = typer.Argument(..., help="岗位ID"),
    fmt: str = typer.Option("md", "--format", "-f", help="输出格式: md/pdf"),
    json_mode: bool = typer.Option(False, "--json", "-j"),
):
    """📄 生成定制化简历"""
    out = _setup(json_mode, False)
    _check_ai(); db = _db(); brain = _brain()
    job = db.get_job_by_id(job_id)
    if not job: out.error(f"岗位#{job_id}不存在"); raise typer.Exit(1)
    r = db.get_resume()
    if not r: out.error("无简历"); raise typer.Exit(1)

    out.status(f"生成简历: {job.title} @ {job.company}")
    md = brain.generate_resume(r.to_dict(), job.to_dict())

    safe = lambda s: "".join(c for c in s if c.isalnum() or c in " _-")[:20]
    base = f"{safe(job.company)}_{safe(job.title)}_简历"
    md_path = Path("output") / f"{base}.md"
    md_path.parent.mkdir(exist_ok=True)
    md_path.write_text(md, encoding="utf-8")
    out.success(f"已保存: {md_path}")

    out.result({"resume": str(md_path), "job": _job_dict(job), "format": fmt})

# ═══════════════════════════════════════════════════════════
# Apply
# ═══════════════════════════════════════════════════════════

@app.command()
def apply(
    job_id: int = typer.Argument(..., help="岗位ID"),
    json_mode: bool = typer.Option(False, "--json", "-j"),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """🚀 智能投递（含评分门槛+智能过滤）"""
    out = _setup(json_mode, yes)
    _check_ai(); db = _db(); brain = _brain(); cfg = _cfg()

    job = db.get_job_by_id(job_id)
    if not job: out.error(f"岗位#{job_id}不存在"); raise typer.Exit(1)
    resume = db.get_resume()
    if not resume: out.error("无简历"); raise typer.Exit(1)

    # 伦理约束
    min_score = float(cfg.get("advanced", "min_apply_score", "4.0") or 4.0)
    if job.match_score > 0 and job.match_score / 20 < min_score:
        out.warn(f"评分 {job.match_score/20:.1f}/5 < 门槛 {min_score}，建议不投")
        if not yes and not out.confirm("仍要投递？", False, json_mode): return

    # 智能过滤
    from .applier.filter import should_filter, load_blacklist
    fr = should_filter(job, resume=resume, blacklist=load_blacklist(db))
    if not fr.passed:
        out.warn(f"过滤拦截: {fr.reason}")
        if not yes and not out.confirm("仍要投递？", False, json_mode): return

    greeting = brain.generate_greeting(resume.to_dict(), job.to_dict())
    out.info(f"打招呼语: {greeting}")

    if not yes and not out.confirm("确认投递？", True, json_mode):
        out.info("已取消"); return

    from .models.application import Application
    app_rec = Application(job_id=job.id or 0, job_title=job.title, company=job.company,
                          platform=job.platform, status="applied", greeting=greeting)
    db.save_application(app_rec)
    out.success(f"已投递: {job.title} @ {job.company}")
    out.result({"applied": True, "job": _job_dict(job), "greeting": greeting})

# ═══════════════════════════════════════════════════════════
# Status / Report / Config / Pipeline / Filter / Verify / Parse
# ═══════════════════════════════════════════════════════════

@app.command()
def status(
    json_mode: bool = typer.Option(False, "--json", "-j"),
):
    """📊 投递状态"""
    out = _setup(json_mode, False); db = _db()
    stats = db.get_application_stats()
    apps = db.get_applications(limit=50)
    r = db.get_resume()

    out.result({
        "stats": stats,
        "applications": [{"job_id": a.job_id, "title": a.job_title, "company": a.company,
                          "status": a.status, "applied_at": a.applied_at[:10] if a.applied_at else "",
                          "notes": a.notes} for a in apps],
        "resume_loaded": bool(r and r.name),
        "total_jobs": db.get_job_count(),
    } if json_mode else {"stats": stats, "applications": [a.to_dict() for a in apps]})


@app.command()
def report(
    output_format: str = typer.Option("json", "--format", "-f", help="json/html/md"),
    limit: int = typer.Option(30, "--limit", "-n", help="包含岗位数"),
    city: Optional[str] = typer.Option(None, "--city", "-c"),
    json_mode: bool = typer.Option(False, "--json", "-j"),
):
    """📋 生成求职报告"""
    out = _setup(json_mode, False); db = _db(); cfg = _cfg()
    city = city or cfg.cities or ""
    jobs = db.get_jobs(limit=limit, city=city, active_only=True)
    apps = db.get_applications(limit=100)

    report_data = {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "stats": db.get_application_stats(),
        "total_jobs": len(jobs),
        "matched_jobs": [_job_dict(j) for j in jobs if j.match_score > 0],
        "top_jobs": [_job_dict(j) for j in sorted(jobs, key=lambda j: j.match_score, reverse=True)[:10]],
        "applications": len(apps),
        "city": city,
    }

    if output_format == "json" or json_mode:
        print(json.dumps(report_data, ensure_ascii=False, indent=2))
    elif output_format == "html":
        path = _generate_report(db, jobs, [], "report", city)
        out.success(f"HTML报告: {path}")
    out.result(report_data)


@app.command()
def config(
    action: str = typer.Argument("list", help="list/get/set"),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="配置键 (section.key)"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="配置值"),
    json_mode: bool = typer.Option(False, "--json", "-j"),
):
    """⚙️ 配置管理: list / get -k section.key / set -k section.key -v value"""
    out = _setup(json_mode, False); cfg = _cfg()
    if action == "list":
        if json_mode:
            print(json.dumps(cfg.data, ensure_ascii=False, indent=2))
        else:
            import rich
            rich.print(cfg.data)
    elif action == "get" and key:
        section, _, k = key.partition(".")
        v = cfg.get(section, k, "")
        if json_mode: print(json.dumps({key: v}))
        else: print(f"{key} = {v}")
    elif action == "set" and key and value:
        section, _, k = key.partition(".")
        cfg.set(section, k, value)
        out.success(f"{key} = {value}")
        if json_mode: print(json.dumps({"ok": True, "key": key, "value": value}))
    else:
        out.error("用法: config list|get -k a.b|set -k a.b -v val")


# sub-command group: pipeline
pipeline_app = typer.Typer(help="管道管理"); app.add_typer(pipeline_app, name="pipeline")

@pipeline_app.command()
def liveness(limit: int = typer.Option(50, "--limit", "-n"), json_mode: bool = typer.Option(False, "--json", "-j")):
    """岗位有效期检测"""
    out = _setup(json_mode, False); db = _db()
    jobs = db.get_jobs(limit=limit, active_only=True)
    from .pipeline.liveness import batch_check_liveness
    results = batch_check_liveness(jobs)
    stale = [{"url": r.url, "reason": r.reason, "confidence": r.confidence}
             for r in results if not r.is_active]
    out.result({"checked": len(jobs), "stale": len(stale), "details": stale[:20]})

@pipeline_app.command()
def dedup(json_mode: bool = typer.Option(False, "--json", "-j")):
    """跨平台去重"""
    out = _setup(json_mode, False); db = _db()
    jobs = db.get_jobs(limit=10000)
    from .pipeline.dedup import dedup_jobs, find_cross_platform_duplicates
    from .pipeline.dedup import dedup_jobs as _dd
    from .pipeline.dedup import find_cross_platform_duplicates as _fcd
    result = _dd(jobs); cross = _fcd(jobs)
    out.result({"total": len(jobs), "unique": len(result["unique"]),
                "cross_dups": len(cross),
                "pairs": [{"a": f"[{a.platform}]{a.title}@{a.company}",
                            "b": f"[{b.platform}]{b.title}@{b.company}", "sim": f"{s:.0%}"}
                           for a, b, s in cross[:20]]})

@pipeline_app.command()
def health(json_mode: bool = typer.Option(False, "--json", "-j")):
    """管道健康检查"""
    out = _setup(json_mode, False); db = _db()
    from .pipeline.normalize import validate_pipeline
    r = validate_pipeline(db)
    out.result(r)


@app.command(name="filter")
def filter_cmd(
    company: str = typer.Argument(..., help="公司名"),
    remove: bool = typer.Option(False, "--remove", "-r", help="从黑名单移除"),
    json_mode: bool = typer.Option(False, "--json", "-j"),
):
    """⛔ 黑名单管理（命令名: filter）"""
    out = _setup(json_mode, False); db = _db()
    from .applier.filter import load_blacklist, add_to_blacklist
    current = load_blacklist(db)
    if remove:
        if company in current: current.remove(company); db.set_config("blacklist", ",".join(current))
        out.success(f"移除: {company}")
    else:
        add_to_blacklist(db, company)
        out.success(f"添加: {company}")
    out.result({"blacklist": load_blacklist(db)})


@app.command()
def verify(
    company_name: str = typer.Argument(..., help="公司全称"),
    direction: Optional[str] = typer.Option(None, "--direction", "-d", help="关注方向"),
    json_mode: bool = typer.Option(False, "--json", "-j"),
):
    """🔍 公司五层交叉验证"""
    out = _setup(json_mode, False); _check_ai(); cfg = _cfg()
    direction = direction or cfg.get("preferences", "position", "环境信息系统")
    out.status(f"验证: {company_name}")

    from .ai.verifier import verify_company, VerifyResult
    result = verify_company(company_name, direction)

    out.result({
        "company": company_name, "verdict": result.verdict,
        "score": result.overall_score, "risk": result.risk_level,
        "registered": result.registered, "has_website": result.has_website,
        "warnings": result.warnings, "evidence": result.evidence,
    })


@app.command()
def parse(
    file_path: str = typer.Argument(..., help="简历文件路径"),
    json_mode: bool = typer.Option(False, "--json", "-j"),
):
    """📄 解析简历"""
    out = _setup(json_mode, False); _check_ai(); db = _db(); brain = _brain()
    if not os.path.exists(file_path): out.error("文件不存在"); raise typer.Exit(1)

    raw = _read_file(file_path)
    parsed = brain.parse_resume(raw)
    from .models.resume import Resume
    r = Resume(**{k: parsed.get(k, "") for k in ["name","phone","email","education_level",
                  "university","major","skills","desired_city","desired_position"]},
               salary_min=parsed.get("salary_min",0), salary_max=parsed.get("salary_max",0),
               raw_text=raw[:5000], raw_file_path=file_path)
    db.save_resume(r)
    out.result({"resume": r.to_dict()})


# ═══════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════

def _job_dict(job) -> dict:
    return {
        "id": job.id, "title": job.title, "company": job.company,
        "city": job.city, "salary": job.salary_range_display,
        "platform": getattr(job, "platform", ""),
        "match_score": getattr(job, "match_score", 0),
        "eval_score": getattr(job, "eval_score", ""),
        "source_url": getattr(job, "source_url", ""),
        "tags": getattr(job, "tags", ""),
        "education": getattr(job, "education", ""),
        "experience": getattr(job, "experience", ""),
    }


def _is_dup(db: Database, job) -> bool:
    """检查是否重复（同平台+同公司+同标题模糊匹配）"""
    existing = db.get_jobs(limit=10000, active_only=False)
    for j in existing:
        if (j.platform == getattr(job, "platform", "") and
            (getattr(j, "company", "") or "") in (getattr(job, "company", "") or "") and
            (getattr(job, "title", "") or "")[:6] in (getattr(j, "title", "") or "")):
            return True
    return False


def _parse_cities(s: str) -> list:
    import re
    return [c.strip() for c in re.split(r'[,，、\s]+', s) if c.strip()]


def _generate_report(db, jobs, evals, keyword, city) -> str:
    """生成HTML报告"""
    import datetime
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    path = f"output/report_{now}.html"
    Path("output").mkdir(exist_ok=True)

    rows = ""
    for j in jobs[:20]:
        score = getattr(j, "match_score", 0)
        color = "green" if score >= 80 else "orange" if score >= 60 else "red"
        rows += f"""<tr>
            <td>{score:.0f}%</td><td><b>{j.title}</b></td><td>{j.company}</td>
            <td>{j.city}</td><td>{j.salary_range_display}</td><td>{getattr(j,'platform','')}</td>
        </tr>"""

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>body{{font-family:'Microsoft YaHei',sans-serif;max-width:900px;margin:20px auto;padding:20px;background:#f8f9fa}}
h1{{color:#1a73e8}}table{{width:100%;border-collapse:collapse;background:white;box-shadow:0 1px 3px rgba(0,0,0,.1)}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid #e0e0e0}}th{{background:#1a73e8;color:white}}
tr:hover{{background:#f5f5f5}}.green{{color:green;font-weight:bold}}.orange{{color:orange}}.red{{color:red}}
.summary{{background:white;padding:15px;margin:15px 0;border-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,.1)}}</style>
</head><body><h1>AI Job Hunt Report</h1>
<div class="summary"><p><b>关键词:</b> {keyword} | <b>城市:</b> {city} | <b>时间:</b> {now} |
<b>总岗位:</b> {len(jobs)} | <b>已评估:</b> {len(evals)}</p></div>
<table><tr><th>匹配</th><th>岗位</th><th>公司</th><th>城市</th><th>薪资</th><th>平台</th></tr>
{rows}</table><p style="color:#999;margin-top:20px">Generated by ai-job-hunt v{__version__}</p></body></html>"""
    Path(path).write_text(html, encoding="utf-8")
    return path


def main_cli():
    app()


if __name__ == "__main__":
    main_cli()
