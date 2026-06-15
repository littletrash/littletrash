"""
耗材管理路由：CRUD + 库存调整
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from database import get_db
from models import Material, Category, Supplier, AuditLog, User
from schemas import (MaterialCreate, MaterialUpdate, MaterialResponse,
                     MaterialStockAdjust, PaginatedResponse, MessageResponse)
from auth import get_current_user, require_admin

router = APIRouter(prefix="/api/materials", tags=["耗材管理"])


def generate_code(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    last = db.query(Material).filter(Material.material_code.like(f"HC{today}%"))\
             .order_by(Material.material_code.desc()).first()
    if last:
        seq = int(last.material_code[-4:]) + 1
    else:
        seq = 1
    return f"HC{today}{seq:04d}"


def material_to_response(m: Material) -> dict:
    alert = "normal"
    if m.safety_stock_min and m.stock_qty < m.safety_stock_min:
        alert = "low"
    elif m.safety_stock_max and m.stock_qty > m.safety_stock_max:
        alert = "high"
    return {
        "id": m.id, "material_code": m.material_code, "name": m.name,
        "spec": m.spec, "category_id": m.category_id,
        "category_name": m.category.name if m.category else None,
        "unit": m.unit, "unit_price": float(m.unit_price),
        "stock_qty": m.stock_qty, "stock_value": float(m.stock_qty * m.unit_price),
        "safety_stock_min": m.safety_stock_min, "safety_stock_max": m.safety_stock_max,
        "location": m.location, "supplier_id": m.supplier_id,
        "supplier_name": m.supplier.name if m.supplier else None,
        "fund_source": m.fund_source, "remark": m.remark,
        "alert_status": alert, "status": m.status,
        "created_at": m.created_at, "updated_at": m.updated_at,
    }


@router.get("", response_model=PaginatedResponse)
def list_materials(
    keyword: str = Query(None, description="搜索关键词"),
    category_id: int = Query(None),
    alert_status: str = Query(None, pattern="^(low|high|normal)$"),
    status: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(Material)
    if keyword:
        q = q.filter(Material.name.contains(keyword) | Material.material_code.contains(keyword))
    if category_id:
        q = q.filter(Material.category_id == category_id)
    if status is not None:
        q = q.filter(Material.status == status)

    total = q.count()
    items = q.order_by(Material.updated_at.desc()).offset((page-1)*page_size).limit(page_size).all()

    result = [material_to_response(m) for m in items]
    if alert_status:
        result = [r for r in result if r["alert_status"] == alert_status]

    return PaginatedResponse(items=result, total=total, page=page, page_size=page_size,
                             total_pages=(total + page_size - 1) // page_size)


@router.get("/{material_id}")
def get_material(material_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="耗材不存在")
    return material_to_response(m)


@router.post("")
def create_material(data: MaterialCreate, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    # 检查是否已存在同名同规格
    existing = db.query(Material).filter(and_(Material.name == data.name, Material.spec == data.spec)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"该耗材已存在（编号：{existing.material_code}），请使用入库功能增加库存")

    code = generate_code(db)
    m = Material(material_code=code, **data.model_dump())
    db.add(m)
    db.flush()

    log = AuditLog(user_id=user.id, username=user.username, action_type="create",
                   action_detail=f"新增耗材：{m.name} {m.spec}（编号：{code}）",
                   target_type="material", target_id=m.id, ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    return {"message": f"耗材创建成功，编号：{code}", "success": True, "material_id": m.id}


@router.put("/{material_id}", response_model=MessageResponse)
def update_material(material_id: int, data: MaterialUpdate,
                    user: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="耗材不存在")

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(m, k, v)

    log = AuditLog(user_id=user.id, username=user.username, action_type="edit",
                   action_detail=f"修改耗材信息：{m.name}（编号：{m.material_code}）",
                   target_type="material", target_id=m.id, ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    return MessageResponse(message="耗材信息已更新")


@router.put("/{material_id}/adjust-stock", response_model=MessageResponse)
def adjust_stock(material_id: int, data: MaterialStockAdjust,
                 user: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = db.query(Material).filter(Material.id == material_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="耗材不存在")

    old_qty = m.stock_qty
    new_qty = old_qty + data.adjust_qty
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="调整后库存不能为负数")

    m.stock_qty = new_qty
    log = AuditLog(user_id=user.id, username=user.username, action_type="adjust",
                   action_detail=f"库存调整：{m.name} {old_qty}→{new_qty}（{data.reason}）",
                   target_type="material", target_id=m.id, ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    return MessageResponse(message=f"库存已调整，当前库存：{new_qty}{m.unit}")
