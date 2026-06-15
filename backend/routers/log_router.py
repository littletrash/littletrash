"""
操作日志路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date
from database import get_db
from models import AuditLog, User
from schemas import PaginatedResponse
from auth import get_current_user, require_admin

router = APIRouter(prefix="/api/audit-logs", tags=["操作日志"])


@router.get("", response_model=PaginatedResponse)
def list_logs(
    keyword: str = Query(None),
    action_type: str = Query(None),
    start_date: date = Query(None),
    end_date: date = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(AuditLog)

    # 教师只能看自己的
    if user.role.value == "teacher":
        q = q.filter(AuditLog.user_id == user.id)

    if keyword:
        q = q.filter(AuditLog.action_detail.contains(keyword) | AuditLog.username.contains(keyword))
    if action_type:
        q = q.filter(AuditLog.action_type == action_type)
    if start_date:
        q = q.filter(AuditLog.created_at >= start_date)
    if end_date:
        q = q.filter(AuditLog.created_at <= end_date)

    total = q.count()
    logs = q.order_by(AuditLog.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()

    items = [{
        "id": l.id, "username": l.username, "action_type": l.action_type,
        "action_detail": l.action_detail, "target_type": l.target_type,
        "target_id": l.target_id, "ip_address": l.ip_address,
        "created_at": l.created_at,
    } for l in logs]
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size,
                             total_pages=(total + page_size - 1) // page_size)


@router.get("/action-types")
def get_action_types():
    """返回所有操作类型（用于筛选下拉）"""
    return ["login", "logout", "inbound", "outbound", "apply", "approve",
            "reject", "return", "adjust", "edit", "create", "delete", "reverse", "backup", "alert"]
