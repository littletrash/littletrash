"""
认证路由：登录、获取当前用户、头像上传
"""
import os, shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import User, AuditLog
from schemas import LoginRequest, TokenResponse
from auth import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证"])

AVATAR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "avatars")

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username, User.status == 1).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user.last_login_at = datetime.utcnow()
    db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role.value})

    # 记录登录日志
    log = AuditLog(user_id=user.id, username=user.username, action_type="login",
                   action_detail="用户登录系统", ip_address="127.0.0.1")
    db.add(log)
    db.commit()

    return TokenResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "real_name": user.real_name,
              "role": user.role.value, "avatar_initials": user.avatar_initials}
    )

@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "real_name": user.real_name,
            "role": user.role.value, "avatar_initials": user.avatar_initials,
            "phone": user.phone, "email": user.email}

@router.put("/profile")
def update_profile(
    username: str = Query(None), real_name: str = Query(None),
    phone: str = Query(None), email: str = Query(None),
    avatar: str = Query(None, max_length=2), new_password: str = Query(None),
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if username and username != user.username:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            raise HTTPException(status_code=400, detail="用户名已被占用")
        user.username = username
    if real_name: user.real_name = real_name
    if phone is not None: user.phone = phone
    if email is not None: user.email = email
    if avatar: user.avatar_initials = avatar
    if new_password and len(new_password) >= 4:
        from auth import hash_password
        user.password_hash = hash_password(new_password)
    db.commit()
    return {"message": "个人资料已更新", "success": True,
            "user": {"id": user.id, "username": user.username, "real_name": user.real_name,
                     "role": user.role.value, "avatar_initials": user.avatar_initials,
                     "phone": user.phone, "email": user.email}}

@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="仅支持图片文件")
    os.makedirs(AVATAR_DIR, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in (file.filename or "") else "png"
    filename = f"{user.id}.{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    avatar_url = f"/api/auth/avatar/{user.id}"
    user.avatar_url = avatar_url
    db.commit()
    return {"message": "头像上传成功", "success": True, "avatar_url": avatar_url}

@router.get("/avatar/{user_id}")
def get_avatar(user_id: int):
    for ext in ["png", "jpg", "jpeg", "gif"]:
        fp = os.path.join(AVATAR_DIR, f"{user_id}.{ext}")
        if os.path.exists(fp):
            return FileResponse(fp, media_type=f"image/{ext}")
    raise HTTPException(status_code=404, detail="无头像")

@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log = AuditLog(user_id=user.id, username=user.username, action_type="logout",
                   action_detail="用户登出系统", ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    return {"message": "已登出"}
