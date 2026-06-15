"""
JWT 认证 & 角色权限控制
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from database import get_db
from models import User, UserRole
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# ─── 密码 ───
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ─── Token ───
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

# ─── 获取当前用户 ───
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="令牌格式错误")
    user = db.query(User).filter(User.id == int(user_id), User.status == 1).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已停用")
    return user

# ─── 角色守卫 ───
def require_role(*roles: UserRole):
    """装饰器工厂：检查当前用户是否拥有指定角色"""
    def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return user
    return checker

# 常用角色组合
require_admin = require_role(UserRole.admin, UserRole.sysadmin)
require_approver = require_role(UserRole.approver, UserRole.admin, UserRole.sysadmin)
require_sysadmin = require_role(UserRole.sysadmin)
