"""Rich终端美化输出工具"""

from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box

from .. import __version__
from ..models.job import Job
from ..models.application import Application
from ..models.resume import Resume

console = Console()


def print_banner():
    """打印系统横幅"""
    banner = f"""
[bold cyan]
   █████╗ ██╗          ██╗ ██████╗ ██████╗     ██╗  ██╗██╗   ██╗███╗   ██╗████████╗
  ██╔══██╗██║          ██║██╔═══██╗██╔══██╗    ██║  ██║██║   ██║████╗  ██║╚══██╔══╝
  ███████║██║     █████╗██║██║   ██║██████╔╝    ███████║██║   ██║██╔██╗ ██║   ██║
  ██╔══██║██║     ╚════╝██║██║   ██║██╔══██╗    ██╔══██║██║   ██║██║╚██╗██║   ██║
  ██║  ██║██║          ██║╚██████╔╝██████╔╝    ██║  ██║╚██████╔╝██║ ╚████║   ██║
  ╚═╝  ╚═╝╚═╝          ╚═╝ ╚═════╝ ╚═════╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝
[/bold cyan]
[dim cyan]   AI 智慧求职系统 · v{__version__} · 纯CLI · 本地运行 · 面向中国[/dim cyan]
[dim]   你只管说，AI来做。[/dim]
"""
    console.print(banner)


def print_info(msg: str):
    console.print(f"[cyan]🤖[/cyan] {msg}")


def print_success(msg: str):
    console.print(f"[green]✅[/green] {msg}")


def print_warning(msg: str):
    console.print(f"[yellow]⚠️[/yellow] {msg}")


def print_error(msg: str):
    console.print(f"[red]❌[/red] {msg}")


def print_ai(msg: str):
    """AI思维过程输出"""
    console.print(f"[dim]💭 {msg}[/dim]")


def print_status(msg: str):
    console.print(f"[blue]🔍[/blue] {msg}")


def create_progress() -> Progress:
    """创建进度条"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    )


def display_job_table(jobs: List[Job], title: str = "岗位列表"):
    """显示岗位表格"""
    table = Table(title=title, box=box.ROUNDED, expand=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("匹配度", style="cyan", width=8)
    table.add_column("岗位", style="bold", width=25)
    table.add_column("公司", width=20)
    table.add_column("薪资", style="green", width=12)
    table.add_column("城市", width=8)
    table.add_column("平台", width=10)
    table.add_column("评级", width=6)

    for i, job in enumerate(jobs, 1):
        match = f"[cyan]{job.match_score:.0f}%[/cyan]" if job.match_score > 0 else "[dim]-[/dim]"
        salary = job.salary_range_display
        eval_ = job.eval_score if job.eval_score else "-"
        table.add_row(
            str(i), match, job.title, job.company,
            salary, job.city, job.platform_display, eval_,
        )

    console.print(table)


def display_job_detail(job: Job):
    """显示岗位详情"""
    console.print()
    console.print(Panel.fit(
        f"[bold white]{job.title}[/bold white]",
        border_style="cyan",
    ))

    # 基本信息
    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column(style="dim")
    info_table.add_column(style="white")
    info_table.add_row("🏢 公司", job.company)
    info_table.add_row("📍 地点", f"{job.city} {job.district}".strip())
    info_table.add_row("💰 薪资", f"[green]{job.salary_range_display}[/green]")
    info_table.add_row("🎓 学历", job.education or "不限")
    info_table.add_row("💼 经验", job.experience or "不限")
    info_table.add_row("🔗 来源", f"{job.platform_display} | [dim]{job.source_url[:50]}...[/dim]")
    console.print(info_table)

    # 标签
    if job.tags:
        tags = " · ".join(f"[blue]{t.strip()}[/blue]" for t in job.tags.split(","))
        console.print(f"\n🏷️  {tags}")

    # 匹配度
    if job.match_score > 0:
        color = "green" if job.match_score >= 80 else "yellow" if job.match_score >= 60 else "red"
        console.print(f"\n📊 匹配度: [{color}]{job.match_score:.0f}%[/{color}]")

    if job.recommend_reason:
        console.print(f"💡 推荐理由: {job.recommend_reason}")

    # JD摘要
    if job.description:
        console.print("\n📋 岗位描述:")
        desc = job.description[:500] + ("..." if len(job.description) > 500 else "")
        console.print(Panel(desc, border_style="dim"))

    # 福利
    if job.benefits:
        console.print(f"\n🎁 福利: {job.benefits}")


def display_application_stats(stats: dict):
    """显示投递统计面板"""
    total = stats.get("total", 0)
    if total == 0:
        console.print("\n[dim]暂无投递记录[/dim]\n")
        return

    applied = stats.get("applied", 0)
    replied = stats.get("replied", 0)
    interview = stats.get("interview", 0)
    offer = stats.get("offer", 0)
    rejected = stats.get("rejected", 0)
    ignored = stats.get("ignored", 0)

    content = f"""
[bold]📊 投递总览[/bold]

  总计投递: {total}   |   🟡 已投递: {applied}   |   🟢 已回复: {replied}
  🔵 面试中: {interview}   |   🎉 Offer: {offer}   |   🔴 已拒绝: {rejected}   |   ⚫ 未回复: {ignored}
"""
    console.print(Panel(content.strip(), border_style="cyan"))


def display_application_table(apps: List[Application]):
    """显示投递记录表格"""
    if not apps:
        console.print("\n[dim]暂无投递记录[/dim]\n")
        return

    table = Table(title="📋 投递记录", box=box.ROUNDED, expand=True)
    table.add_column("日期", style="dim", width=12)
    table.add_column("岗位", width=25)
    table.add_column("公司", width=20)
    table.add_column("平台", width=10)
    table.add_column("状态", width=12)
    table.add_column("备注", width=20)

    for app in apps:
        date = app.applied_at[:10] if app.applied_at else "-"
        table.add_row(date, app.job_title, app.company, app.platform, app.status_display, app.notes[:30])

    console.print(table)


def display_resume_summary(resume: Resume):
    """显示简历摘要"""
    table = Table(box=box.ROUNDED, title="📄 简历摘要")
    table.add_column("维度", style="dim")
    table.add_column("内容", style="white")

    if resume.name:
        table.add_row("姓名", resume.name)
    if resume.education_level and resume.university:
        table.add_row("学历", f"{resume.education_level} - {resume.university}")
    if resume.major:
        table.add_row("专业", resume.major)
    if resume.desired_position:
        table.add_row("意向岗位", resume.desired_position)
    if resume.desired_city:
        table.add_row("意向城市", resume.desired_city)
    if resume.salary_min and resume.salary_max:
        table.add_row("期望薪资", f"{resume.salary_min / 1000:.0f}-{resume.salary_max / 1000:.0f}K")
    if resume.skills:
        table.add_row("技能", resume.skills[:80])

    console.print(table)
