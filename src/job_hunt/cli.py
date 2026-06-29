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
_gdb: Optional[Database] = None
_gcfg: Optional[Config] = None
_gbrain: Optional = None
_gout: Optional[Output] = None
_json_mode: bool = False
_yes_mode: bool = False

app = typer.Typer(name="job-hunt", help="AI Job Hunt - CLI-first, AI-ready", no_args_is_help=True, pretty_exceptions_enable=False)


def _setup(json_mode: bool = False, yes_mode: bool = False) -> Output:
    global _gout, _json_mode, _yes_mode
    _json_mode = json_mode
    _yes_mode = yes_mode
    _gout = Output(json_mode=json_mode)
    return _gout


def _json() -> bool: return _json_mode
def _yes() -> bool: return _yes_mode
def _out() -> Output: return _gout


def _db() -> Database:
    global _gdb
    if _gdb is None:
        _gdb = Database()
    return _gdb


def _cfg() -> Config:
    global _gcfg
    if _gcfg is None:
        _gcfg = Config()
    return _gcfg


def _brain():
    global _gbrain
    if _gbrain is None:
        try:
            from .ai.brain import AIBrain
            _gbrain = AIBrain(_cfg())
        except ImportError as e:
            _out().error(f"AI模块不可用: {e}")
            raise typer.Exit(1)
    return _gbrain


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
        import os as _os

        # 自动检测环境变量 DEEPSEEK_API_KEY
        env_key = _os.environ.get("DEEPSEEK_API_KEY", "")
        has_env_key = bool(env_key)
        if has_env_key:
            out.info(f"检测到环境变量 DEEPSEEK_API_KEY (****{env_key[-4:]})，将自动使用")

        provider = Prompt.ask("AI提供商", choices=["deepseek","openai","qwen","custom"], default="deepseek")
        cfg.set("ai", "provider", provider)
        model = Prompt.ask("模型", default="deepseek-chat")
        cfg.set("ai", "model", model)

        # 有环境变量时不需要手动输入 key
        if has_env_key:
            out.info("API Key 将使用环境变量 DEEPSEEK_API_KEY，无需输入")
        else:
            api_key = Prompt.ask("API Key（或设置环境变量 DEEPSEEK_API_KEY）", password=True, default="")
            if api_key:
                cfg.set("ai", "api_key", api_key)
        out.success("AI 配置完成")

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
    elif plat == "univ":
        return _scrape_university_sites(keyword, city, pages, out)
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
# Auto — 全自动闭环流水线
# ═══════════════════════════════════════════════════════════

@app.command()
def auto(
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="搜索关键词（逗号分隔多个）"),
    city: Optional[str] = typer.Option(None, "--city", "-c", help="城市筛选（逗号分隔）"),
    platform: str = typer.Option("gxrc,51job,univ", "--platform", "-p", help="平台: gxrc/51job/univ/all"),
    max_pages: int = typer.Option(2, "--pages", "-n", help="每平台最大页数"),
    json_mode: bool = typer.Option(False, "--json", "-j", help="JSON输出(AI模式)"),
    yes: bool = typer.Option(False, "--yes", "-y", help="非交互模式"),
    min_score: float = typer.Option(30, "--min-score", "-m", help="最低匹配度(%)"),
    ai_mode: bool = typer.Option(False, "--ai", help="启用AI评估(需配置API key)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="干跑模式：仅扫描不评估"),
):
    """⚡ 全自动闭环: scan → match → eval → report

    支持 AI 和 关键词双引擎。AI 不可用时自动降级为关键词匹配。
    示例:
      job-hunt auto -k "Python 开发,数据分析" -c 南宁              # 关键词匹配模式
      job-hunt auto -k "环保,环境" -c 南宁,广州 --ai               # AI评估模式
      job-hunt auto -k "Python 开发" --json --yes                   # 全自动JSON输出
      job-hunt auto -k "大气环境" --dry-run                         # 仅扫描不评估
    """
    out = _setup(json_mode, yes)
    cfg = _cfg(); db = _db()

    city = city or cfg.cities or ""
    keyword = keyword or cfg.keywords
    if not keyword:
        out.error("请指定 --keyword。示例: job-hunt auto -k \"Python 开发,数据分析\" -c 南宁")
        raise typer.Exit(1)

    # 判断哪些关键词要搜索
    keywords = [k.strip() for k in keyword.replace("，", ",").split(",") if k.strip()]
    cities = [c.strip() for c in city.replace("，", ",").split(",") if c.strip()]
    platforms = [p.strip() for p in platform.split(",")]

    # ─── 检测AI是否可用 ───
    brain = None
    if ai_mode:
        try:
            _check_ai()
            from .ai.brain import AIBrain
            brain = AIBrain(cfg)
            out.info("AI引擎已就绪")
        except Exception as e:
            out.warn(f"AI不可用({e})，降级为关键词匹配")
    else:
        out.info("使用关键词匹配引擎（加 --ai 启用AI评估）")

    from .ai.matcher import KeywordMatcher
    matcher = KeywordMatcher()
    resume_d = db.get_resume().to_dict() if db.get_resume() else {}
    if resume_d:
        matcher.skills = [s.strip().lower() for s in (resume_d.get("skills","") or "").split(",") if s.strip()] or matcher.skills

    # ═══════════════════════════════════════════════════
    # Step 1: SCAN
    # ═══════════════════════════════════════════════════
    out.status(f"[1/4] 扫描 | 关键词={keywords} | 城市={cities} | 平台={platforms}")
    all_jobs = []
    scan_errors = []
    for kw in keywords:
        for plat in platforms:
            try:
                jobs = _run_scraper(plat.strip(), kw, city if city else "", max_pages, False, out)
                saved = 0
                for j in jobs:
                    if j.title and len(j.title) >= 2 and not _is_dup(db, j):
                        db.save_job(j)
                        saved += 1
                        all_jobs.append(j)
                if saved:
                    out.info(f"  [{plat}] '{kw}' → {saved}条")
            except Exception as e:
                scan_errors.append(f"{plat}/{kw}: {e}")
                out.warn(f"  [{plat}] '{kw}' 失败: {e}")
    out.success(f"[1/4] 扫描完成: {len(all_jobs)} 新岗位 ({len(scan_errors)} 个平台异常)")

    if not all_jobs:
        # 回退：使用数据库中已有的未评估岗位
        out.info("无新岗位，从数据库中选取已有岗位继续...")
        db_jobs = db.get_jobs(limit=50, city=(city if city else None), active_only=True)
        unrated = [j for j in db_jobs if not getattr(j, 'eval_score', None)]
        all_jobs = unrated if unrated else db_jobs[:30]
        out.info(f"从数据库选取 {len(all_jobs)} 个岗位")

    if dry_run:
        out.result({"status": "dry_run_done", "scanned": len(all_jobs),
                     "jobs": [_job_dict(j) for j in all_jobs[:30]]})
        return

    # ═══════════════════════════════════════════════════
    # Step 2: MATCH
    # ═══════════════════════════════════════════════════
    out.status(f"[2/4] 匹配 {len(all_jobs)} 个岗位...")
    matched = []
    for job in all_jobs:
        try:
            jd = job.to_dict()
            # AI优先，关键词后备
            if brain:
                r = brain.match_job(resume_d, jd)
            else:
                r = matcher.match(jd)
            score = r.get("match_score", 0)
            db.update_job_match(job.id or 0, score, json.dumps(r, ensure_ascii=False))
            job.match_score = score
            if score >= min_score:
                matched.append(job)
        except Exception:
            continue
    matched.sort(key=lambda j: j.match_score, reverse=True)
    count_msg = f"{len(matched)}个>={min_score}%" if matched else f"0个满足门槛，放宽至TOP{min(15,len(all_jobs))}"
    if not matched and all_jobs:
        # 放宽门槛：至少给 TOP 15
        all_jobs.sort(key=lambda j: j.match_score or 0, reverse=True)
        matched = all_jobs[:15]
    out.success(f"[2/4] 匹配完成: {count_msg}")

    # ═══════════════════════════════════════════════════
    # Step 3: EVAL (TOP 10)
    # ═══════════════════════════════════════════════════
    top_n = min(10, len(matched))
    out.status(f"[3/4] 评估 TOP {top_n}...")
    evals = []
    for job in matched[:top_n]:
        try:
            jd = job.to_dict()
            if brain:
                er = brain.evaluate_job(jd, resume_d)
            else:
                er = matcher.evaluate(jd)
            db.update_job_eval(job.id or 0, f"{er.get('overall_score',0)}/5.0",
                               json.dumps(er, ensure_ascii=False))
            evals.append({"job": _job_dict(job), "eval": er})
        except Exception:
            continue
    if not evals:
        if matched:
            top = matched[0]
            er = matcher.evaluate(top.to_dict())
            evals.append({"job": _job_dict(top), "eval": er})
        else:
            out.warn("无岗位可评估，跳过评估步骤")
    out.success(f"[3/4] 评估完成: {len(evals)} 个")

    # ═══════════════════════════════════════════════════
    # Step 4: REPORT
    # ═══════════════════════════════════════════════════
    out.status(f"[4/4] 生成报告...")
    mode_tag = "ai" if brain else "kw"
    report_path = _generate_report_v2(db, matched[:30], evals, keywords, cities, mode_tag)
    out.success(f"[4/4] 报告: {report_path}")

    out.result({
        "status": "done",
        "mode": mode_tag,
        "scanned": len(all_jobs),
        "matched": len(matched),
        "evaluated": len(evals),
        "keyword": keyword, "city": city,
        "top_jobs": [e["job"] for e in evals[:5]],
        "report": report_path,
        "scan_errors": scan_errors if scan_errors else None,
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
def health(
    json_mode: bool = typer.Option(False, "--json", "-j"),
):
    """🏥 系统健康检查（环境/依赖/目录/数据库/API Key）"""
    from .health import get_health_check
    out = _setup(json_mode, False)
    hc = get_health_check()
    summary = hc.get_status_summary()

    if not json_mode:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="Health Checks")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")

        for name, result in summary["checks"].items():
            status = "✓ OK" if result["healthy"] else "✗ FAIL"
            details = result.get("status", "")
            table.add_row(name, status, details)

        console.print(table)
        if summary["healthy"]:
            out.success("All health checks passed")
        else:
            out.warn("Some health checks failed")

    out.result(summary)


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

def _scrape_university_sites(keyword: str, city: str, pages: int, out: Output) -> list:
    """抓取所有大学环境学院就业网（browser open + scroll 触发渲染）"""
    from .models.job import Job
    import re, subprocess as sp, time as _t
    jobs: list = []

    sources = [
        ("gxu", "广西大学·资环材", "https://gxulif.gxu.edu.cn/CN/rcpy/jyxx.htm", "gxu"),
        ("glut", "桂林理工·环境", "https://hjxy.glut.edu.cn/xwzx1/fqtg.htm", "glut"),
        ("scut", "华南理工·就业中心", "https://jyzx.scut.edu.cn/37757/list.htm", "scut"),
    ]

    for tag, name, url, ptype in sources:
        sid = f"u_{tag}"
        try:
            out.info(f"  [univ] {name}...")
            # 关闭旧 session，打开新页面（browser open 触发完整初始渲染）
            sp.run(["browser-act", "session", "close", sid],
                   capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=5)
            r = sp.run(["browser-act", "--session", sid, "browser", "open",
                        "chrome_local_101959002016973032", url],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
            if r.returncode != 0:
                out.warn(f"  [{tag}] open fail: {r.stderr[:50]}"); continue
            _t.sleep(2)

            # 滚动触发懒加载内容
            sp.run(["browser-act", "--session", sid, "scroll", "down", "--amount", "3000"],
                   capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10)
            _t.sleep(1)

            lines = _fetch_univ_text(sid) or []
            if not lines:
                out.info(f"  [{tag}] 0 rows"); continue

            entries = _parse_univ(ptype, lines, tag)
            for e in entries:
                j = _make_univ_job(tag, e["title"], e.get("company",""), e.get("date",""), e.get("desc",""), keyword)
                if j: jobs.append(j)

            rel = sum(1 for j in jobs if j.platform == "univ")
            out.info(f"  [{tag}] {len(entries)} entries → {rel} relevant")
        except sp.TimeoutExpired:
            out.warn(f"  [{tag}] timeout")
        except Exception as e:
            out.warn(f"  [{tag}]: {str(e)[:60]}")

    return jobs


def _fetch_univ_text(session: str) -> list:
    """从当前浏览器页面提取所有招聘相关行"""
    import subprocess as sp
    # 先取全文，再在 Python 侧过滤——比 JS 过滤更可靠
    js = "document.body.innerText.slice(0,10000)"
    r = sp.run(["browser-act", "--session", session, "eval", js],
               capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=15)
    if r.returncode != 0 or not r.stdout:
        return None
    lines = r.stdout.split("\n")
    return [l.strip() for l in lines if len(l.strip()) > 3]


def _parse_univ(ptype: str, lines: list, tag: str) -> list:
    """根据页面类型解析招聘条目"""
    import re
    entries = []
    if ptype == "gxu":
        # 格式: 标题行 → 日期(2026-xx-xx) → 招聘单位：...行
        i = 0
        while i < len(lines):
            line = lines[i]
            m = re.match(r"(\d{4}-\d{2}-\d{2})", line)
            if m:
                title = lines[i-1] if i > 0 else ""
                date_str = m.group(1)
                company = desc = ""
                if i+1 < len(lines) and "招聘单位" in lines[i+1]:
                    company = lines[i+1].split("招聘单位：")[-1].split("所在学校")[0].split("单位简介")[0].strip()[:40]
                    desc = lines[i+1][:300]
                if title and not re.match(r"\d{4}-\d{2}-\d{2}", title):
                    entries.append({"title": title[:80], "company": company, "date": date_str, "desc": desc})
                i += 2
            else:
                i += 1
            if len(entries) >= 12:
                break

    elif ptype == "glut":
        # 格式: "学院举办XXX专场招聘会" 或 "YYY公司到我院开展访企拓岗"
        for i, line in enumerate(lines):
            m = re.search(r"举办\s*(\S{2,30}?(?:有限|集团|科技|股份|设计院|研究院|公司|中心))\s*专场", line)
            if m:
                company = m.group(1)
                title = f"{company}专场招聘会"
            elif "访企拓岗" in line or "专场招聘" in line or "双选会" in line:
                title = line[:80]
                company = re.search(r'(\S{2,30}?(?:公司|集团|研究院|设计院|中心))', line)
                company = company.group(1) if company else ""
            else:
                continue
            desc = lines[i+1][:200] if i+1 < len(lines) else ""
            date_match = re.search(r"(\d{4}[-/]\d{2})", line)
            entries.append({
                "title": title[:80],
                "company": company or "",
                "date": date_match.group(1) if date_match else "",
                "desc": desc,
            })
            if len(entries) >= 10:
                break

    elif ptype == "list":
        for line in lines:
            if any(k in line for k in ["就业信息","招生就业","当前位置","首页"]):
                continue
            date_match = re.search(r"(\d{4}/\d{2}/\d{2})", line)
            entries.append({
                "title": line[:80],
                "company": "",
                "date": date_match.group(1) if date_match else "",
                "desc": line,
            })
            if len(entries) >= 10:
                break

    elif ptype == "scut":
        # SCUT 网络招聘：公司行→岗位行(含|分隔)→日期行
        i = 0
        while i < len(lines):
            l = lines[i]
            # 检测日期行 (YYYY.MM.DD)
            if re.match(r"\d{4}\.\d{2}\.\d{2}$", l):
                date = l.replace(".", "-")
                company = ""; jobs = ""
                j = i - 1
                while j >= 0 and not re.match(r"\d{4}\.\d{2}\.\d{2}$", lines[j]):
                    if re.search(r"公司|集团|有限|中心|学院|大学|研究院", lines[j]) and not company:
                        company = lines[j]
                    elif "|" in lines[j] and not jobs:
                        jobs = lines[j]
                    j -= 1
                if company and jobs:
                    entries.append({
                        "title": f"{company}: {jobs[:60]}",
                        "company": company,
                        "date": date,
                        "desc": jobs[:300],
                    })
                i += 1
            else:
                i += 1
            if len(entries) >= 15:
                break

    return entries


def _make_univ_job(tag: str, title: str, company: str, date: str, desc: str, keyword: str):
    """构造大学就业渠道的 Job 对象，含相关性过滤"""
    from .models.job import Job

    if keyword:
        kws = [k.strip().lower() for k in keyword.replace("，",",").split(",")]
    else:
        kws = ["环境","环保","数据","开发","python","ai","信息","监测","水务","大气","化学","能源"]
    text = f"{title} {company} {desc}".lower()
    if not any(k in text for k in kws):
        return None

    city = ""
    for c in ["南宁","广州","深圳","桂林","柳州","佛山","东莞","北海","钦州"]:
        if c in title or c in company or c in desc:
            city = c; break

    return Job(
        title=f"[{tag}] {title[:60]}",
        company=company or f"{tag}大学就业网",
        platform="univ",
        source_url="",
        description=desc[:300],
        city=city,
        scraped_at=date,
    )

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
    """旧版报告（保留兼容）"""
    return _generate_report_v2(db, jobs, evals, [keyword], [city], "legacy")


def _generate_report_v2(db, jobs, evals, keywords: list, cities: list, mode: str = "kw") -> str:
    """新版统一报告 — 使用 report.css 模板"""
    import datetime
    now = datetime.datetime.now()
    ts = now.strftime("%Y%m%d_%H%M")
    path = f"output/report_{ts}.html"
    Path("output").mkdir(exist_ok=True)

    kw_str = " · ".join(keywords)
    city_str = " · ".join(cities) if cities else "全国"
    mode_str = "AI评估" if mode == "ai" else "关键词匹配"
    kws_tag = keywords[0] if keywords else ""

    # 分类
    cross_jobs, dev_jobs, data_jobs, env_jobs, other_jobs = [], [], [], [], []
    env_kw = ["环保","环境","大气","水务","监测","水","碳","污染","废","绿色","生态","排放","净化"]
    dev_kw = ["python","开发","全栈","软件","java","前端","后端","工程师","agent","智能体","架构师"]
    data_kw = ["数据","分析","统计","GIS","遥感","AI","算法","机器学习","大模型","模型"]

    for j in jobs:
        t = (j.title or "").lower()
        c = (j.company or "").lower()
        d = (getattr(j, "description", "") or "").lower()
        full = f"{t} {c} {d}"
        is_env = any(k in full for k in env_kw)
        is_dev = any(k in full for k in dev_kw)
        is_data = any(k in full for k in data_kw)
        if is_env and (is_data or is_dev):
            cross_jobs.append(j)
        elif is_dev:
            dev_jobs.append(j)
        elif is_data:
            data_jobs.append(j)
        elif is_env:
            env_jobs.append(j)
        else:
            other_jobs.append(j)

    def _card(j) -> str:
        sc = getattr(j, "match_score", 0) or 0
        hl = ' hl' if sc >= 60 else ''
        stars = "★★★★★" if sc >= 80 else "★★★★" if sc >= 60 else "★★★" if sc >= 40 else "★★"
        ev = ""
        for e in evals:
            if e.get("job", {}).get("id") == j.id:
                ev = f'<span class="tg tr">已评估 {e.get("eval", {}).get("overall_score", "")}/5</span>'
                break
        url = getattr(j, "source_url", "") or ""
        ttl = j.title or "(无标题)"
        sal = j.salary_range_display or ""
        co = j.company or ""
        cit = j.city or ""
        pl = getattr(j, "platform", "") or ""
        return f"""<div class="jc{hl}">
<div class="sr">{'<a href="'+url+'" target="_blank">'+ttl+'</a>' if url else ttl} {stars} {ev}</div>
<div class="sy">{sal}</div>
<div class="dc">🏢 {co} · {cit} [{pl}]</div>
</div>"""

    sections = [
        ("🌫️ 环保×计算机交叉", cross_jobs),
        ("💻 Python/AI开发", dev_jobs),
        ("📊 数据分析", data_jobs),
        ("🌿 环保/水务/环境", env_jobs),
        ("🏫 其他", other_jobs),
    ]

    sec_html = ""
    for title, js in sections:
        if not js:
            continue
        cards = "\n".join(_card(j) for j in js[:12])
        sec_html += f"""<div class="sec">
<h2>{title} <span class="badge">{len(js)}条</span></h2>
{cards}
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>岗位报告 — {kw_str} — {ts}</title>
<link rel="stylesheet" href="report.css">
</head><body><div class="w">
<div class="h0"><h1>岗位报告 — {kw_str} — {city_str}</h1>
<div class="mt">👤 陈立志 | 环境工程硕士 | PM2.5+Python+AI<br>
📅 {now.strftime('%Y-%m-%d %H:%M')} | 🤖 {mode_str} | 📡 GXRC + 51job browser-act 实时抓取<br>
📊 扫描 {len(jobs)}条 | 匹配 {sum(1 for j in jobs if getattr(j,'match_score',0)>0)}条 | 评估 {len(evals)}条</div>
</div>
{sec_html}
<div class="sec"><h2>📡 数据来源</h2>
<p style="font-size:12px;color:var(--d)">GXRC(gxrc.com) + 前程无忧(51job.com) browser-act 全浏览器模式 JS eval 实时提取。<br>
所有岗位均有可直接点击的招聘平台详情页链接。<br>
匹配引擎: {mode_str}。关键词: {kw_str}。城市: {city_str}。</p>
</div>
<div class="ft">Generated by ai-job-hunt v{__version__} · CLI-first, AI-ready · {mode_str}</div>
</div></body></html>"""
    Path(path).write_text(html, encoding="utf-8")
    return path


def main_cli():
    app()


if __name__ == "__main__":
    main_cli()
