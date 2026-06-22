"""
岗位有效期检测 — 确认岗位是否仍然活跃

检测策略（按可靠性排序）：
1. browser-act / Playwright 直接访问详情页，检查 Apply 按钮
2. httpx 快速请求，检查 HTTP 状态码
3. 根据抓取日期判断（超过30天标记为可疑）
"""

import httpx
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timedelta


@dataclass
class LivenessResult:
    """岗位有效期检测结果"""
    job_id: int = 0
    url: str = ""
    is_active: bool = True
    confidence: str = ""        # high / medium / low
    reason: str = ""
    http_status: int = 0
    checked_at: str = ""

    @property
    def display(self) -> str:
        if self.confidence == "high":
            return "[OK] Active" if self.is_active else "[CLOSED]"
        elif self.confidence == "medium":
            return "[?] Likely active" if self.is_active else "[?] Likely closed"
        else:
            return "[?] Unknown"


def check_liveness_http(url: str, timeout: int = 10) -> LivenessResult:
    """通过 HTTP 请求快速检测

    Returns:
        LivenessResult
    """
    result = LivenessResult(url=url, checked_at=datetime.now().isoformat())

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            result.http_status = resp.status_code

            if resp.status_code == 404:
                result.is_active = False
                result.confidence = "high"
                result.reason = "HTTP 404 — 页面不存在"
                return result

            if resp.status_code == 301 or resp.status_code == 302:
                result.is_active = False
                result.confidence = "medium"
                result.reason = f"HTTP {resp.status_code} — 已重定向，岗位可能已下架"
                return result

            if resp.status_code >= 500:
                result.is_active = False
                result.confidence = "low"
                result.reason = f"HTTP {resp.status_code} — 服务器错误"
                return result

            # 200 OK — 需要进一步检查内容
            result.is_active = True
            result.confidence = "medium"
            result.reason = "HTTP 200 — 页面可访问"

            # 检查页面内容是否包含 "已过期" "已下架" 等关键词
            text = resp.text.lower()
            closed_signals = [
                "已过期", "已下架", "已失效", "职位已关闭", "该职位已结束",
                "job expired", "position closed", "no longer available",
                "该页面不存在", "404", "岗位已招",
            ]
            for signal in closed_signals:
                if signal in text:
                    result.is_active = False
                    result.confidence = "high"
                    result.reason = f"页面内容包含关闭信号: '{signal}'"
                    break
    except httpx.TimeoutException:
        result.is_active = False
        result.confidence = "low"
        result.reason = "请求超时"
    except httpx.ConnectError:
        result.is_active = False
        result.confidence = "high"
        result.reason = "无法连接 — 网站可能已关闭"
    except Exception as e:
        result.is_active = False
        result.confidence = "low"
        result.reason = f"请求异常: {str(e)[:80]}"

    return result


def check_liveness_by_age(
    scraped_at: str,
    max_days: int = 60,
) -> LivenessResult:
    """根据抓取日期判断

    经验规则：
    - < 30天: 基本可信
    - 30-60天: 可疑
    - > 60天: 大概率已关闭
    """
    result = LivenessResult(checked_at=datetime.now().isoformat())

    try:
        scraped_date = datetime.fromisoformat(scraped_at)
    except (ValueError, TypeError):
        scraped_date = datetime.now() - timedelta(days=365)

    age = (datetime.now() - scraped_date).days

    if age < 30:
        result.is_active = True
        result.confidence = "medium"
        result.reason = f"抓取日期 {scraped_at}（{age}天前）"
    elif age < max_days:
        result.is_active = True
        result.confidence = "low"
        result.reason = f"抓取日期 {scraped_at}（{age}天前，可能已下架）"
    else:
        result.is_active = False
        result.confidence = "low"
        result.reason = f"抓取日期 {scraped_at}（{age}天前，大概率已下架）"

    return result


def check_liveness(
    url: str = "",
    scraped_at: str = "",
    use_http: bool = True,
) -> LivenessResult:
    """综合检测岗位有效期

    优先级: HTTP 实测 > 抓取日期推断
    """
    if use_http and url:
        return check_liveness_http(url)
    if scraped_at:
        return check_liveness_by_age(scraped_at)
    return LivenessResult(
        is_active=True,
        confidence="low",
        reason="无 URL 也无抓取日期，默认假定有效",
    )


def batch_check_liveness(jobs: list, max_concurrent: int = 5) -> list:
    """批量检测岗位有效期

    对每个岗位做 HTTP 检查（有 URL）或日期推断（无 URL）。
    注意: 当前为顺序执行，max_concurrent 参数保留用于后续升级为 asyncio 并行。

    Args:
        jobs: 岗位列表（需有 source_url, scraped_at, id 属性）
        max_concurrent: 保留参数，当前版本未使用（后续支持并行）

    Returns:
        LivenessResult 列表
    """
    results = []
    for job in jobs:
        url = getattr(job, "source_url", "")
        scraped_at = getattr(job, "scraped_at", "")
        result = check_liveness(url=url, scraped_at=scraped_at)
        if hasattr(job, "id"):
            result.job_id = job.id if job.id else 0
        results.append(result)
    return results
