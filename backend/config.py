"""
应用配置
"""
import os
from datetime import timedelta

# 数据库 — 基于文件所在目录定位
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'material_mgmt.db')}")

# JWT
SECRET_KEY = os.getenv("SECRET_KEY", "dianzi-xi-material-mgmt-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8小时

# 审批规则默认值
AUTO_APPROVE_THRESHOLD = 500.0    # 低于此金额自动审批
MULTI_LEVEL_THRESHOLD = 2000.0    # 超过此金额需两级审批

# 分页
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# 上传
UPLOAD_DIR = "uploads"

# 归还管理
RETURN_FINE_RATE = 5.0          # 逾期每日罚款金额（元/天/项）
RETURN_OVERDUE_GRACE_DAYS = 0   # 宽限期（天）
RETURN_DAMAGE_RATE = 0.3        # 损坏赔偿比例（原值的30%）
RETURN_LOSS_RATE = 1.0          # 丢失赔偿比例（原值的100%）
RETURN_MAX_BORROW_DAYS = 30     # 最长借用天数，超期算逾期
