"""
管道自动化模块
- merge: 合并追踪增量到主追踪表
- dedup: 跨平台去重（同公司同岗位）
- normalize: 投递状态标准化
- liveness: 岗位有效期检测
"""

from .dedup import dedup_jobs, make_job_key
from .liveness import LivenessResult, check_liveness
from .merge import merge_tracker, write_tsv_addition
from .normalize import CANONICAL_STATES, normalize_status
