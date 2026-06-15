"""
系统配置路由：获取/修改审批规则、预警参数
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from models import User, AuditLog
from auth import get_current_user, require_sysadmin
import config

router = APIRouter(prefix="/api/config", tags=["系统配置"])

class ConfigUpdate(BaseModel):
    auto_approve_threshold: float = Field(None, ge=0)
    multi_level_threshold: float = Field(None, ge=0)
    return_fine_rate: float = Field(None, ge=0)
    return_max_borrow_days: int = Field(None, ge=1)
    return_damage_rate: float = Field(None, ge=0, le=1)
    return_loss_rate: float = Field(None, ge=0, le=1)
    safety_stock_min_default: int = Field(None, ge=0)
    safety_stock_max_default: int = Field(None, ge=0)

@router.get("")
def get_config(user: User = Depends(get_current_user)):
    return {
        "auto_approve_threshold": config.AUTO_APPROVE_THRESHOLD,
        "multi_level_threshold": config.MULTI_LEVEL_THRESHOLD,
        "return_fine_rate": config.RETURN_FINE_RATE,
        "return_max_borrow_days": config.RETURN_MAX_BORROW_DAYS,
        "return_damage_rate": config.RETURN_DAMAGE_RATE,
        "return_loss_rate": config.RETURN_LOSS_RATE,
        "safety_stock_min_default": getattr(config, 'SAFETY_STOCK_MIN_DEFAULT', 10),
        "safety_stock_max_default": getattr(config, 'SAFETY_STOCK_MAX_DEFAULT', 1000),
    }

@router.put("")
def update_config(data: ConfigUpdate, user: User = Depends(require_sysadmin), db: Session = Depends(get_db)):
    changes = []
    for field, value in data.model_dump(exclude_unset=True).items():
        upper = field.upper()
        if hasattr(config, upper):
            setattr(config, upper, value)
            changes.append(f"{field}={value}")

    log = AuditLog(user_id=user.id, username=user.username, action_type="config_update",
                   action_detail=f"修改系统配置：{', '.join(changes)}",
                   target_type="config", ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    return {"message": "配置已更新", "success": True, "updated": changes}
