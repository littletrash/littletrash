"""
用户管理路由：列表、新增、停用/启用、重置密码
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import User, AuditLog, UserRole
from schemas import PaginatedResponse, MessageResponse
from pydantic import BaseModel, Field
from auth import get_current_user, require_sysadmin, hash_password

router = APIRouter(prefix="/api/users", tags=["用户管理"])

class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    real_name: str = Field(..., min_length=1, max_length=50)
    role: str = Field("teacher", pattern="^(admin|teacher|approver|sysadmin)$")
    password: str = Field(..., min_length=4, max_length=50)
    phone: str = Field("", max_length=20)
    email: str = Field("", max_length=100)

class ResetPassword(BaseModel):
    new_password: str = Field(..., min_length=4, max_length=50)

@router.get("", response_model=PaginatedResponse)
def list_users(
    keyword: str = Query(None),
    role: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_sysadmin),
    db: Session = Depends(get_db)
):
    q = db.query(User)
    if keyword:
        q = q.filter(User.username.contains(keyword) | User.real_name.contains(keyword))
    if role:
        q = q.filter(User.role == role)
    total = q.count()
    items = q.order_by(User.id).offset((page-1)*page_size).limit(page_size).all()
    return PaginatedResponse(
        items=[{"id": u.id, "username": u.username, "real_name": u.real_name,
                "role": u.role.value, "phone": u.phone, "email": u.email,
                "status": u.status, "last_login_at": u.last_login_at,
                "created_at": u.created_at} for u in items],
        total=total, page=page, page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )

@router.post("")
def create_user(data: UserCreate, user: User = Depends(require_sysadmin), db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    u = User(
        username=data.username, password_hash=hash_password(data.password),
        real_name=data.real_name, role=UserRole(data.role),
        phone=data.phone, email=data.email, avatar_initials=data.real_name[0]
    )
    db.add(u)
    db.flush()
    log = AuditLog(user_id=user.id, username=user.username, action_type="create_user",
                   action_detail=f"新增用户：{u.username}（{u.real_name}，角色：{u.role.value}）",
                   target_type="user", target_id=u.id, ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    return {"message": f"用户 {u.username} 创建成功", "success": True, "user_id": u.id}

@router.put("/{user_id}/toggle-status")
def toggle_user_status(user_id: int, user: User = Depends(require_sysadmin), db: Session = Depends(get_db)):
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="不能停用自己的账号")
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.status = 0 if u.status == 1 else 1
    log = AuditLog(user_id=user.id, username=user.username, action_type="toggle_user",
                   action_detail=f"{'停用' if u.status==0 else '启用'}用户：{u.username}",
                   target_type="user", target_id=u.id, ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    return {"message": f"用户 {'已停用' if u.status==0 else '已启用'}", "success": True}

@router.put("/{user_id}/reset-password")
def reset_password(user_id: int, data: ResetPassword, user: User = Depends(require_sysadmin), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    u.password_hash = hash_password(data.new_password)
    log = AuditLog(user_id=user.id, username=user.username, action_type="reset_pwd",
                   action_detail=f"重置用户 {u.username} 的密码",
                   target_type="user", target_id=u.id, ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    return {"message": f"密码已重置", "success": True}
