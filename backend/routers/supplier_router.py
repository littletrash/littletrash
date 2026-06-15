"""
供应商管理路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from database import get_db
from models import Supplier, AuditLog, User, InboundRecord, CoopStatus
from schemas import SupplierCreate, PaginatedResponse, MessageResponse
from auth import get_current_user, require_admin

router = APIRouter(prefix="/api/suppliers", tags=["供应商管理"])


def generate_supplier_code(db: Session) -> str:
    year = datetime.utcnow().strftime("%Y")
    last = db.query(Supplier).filter(Supplier.supplier_code.like(f"SUP{year}%"))\
             .order_by(Supplier.supplier_code.desc()).first()
    seq = int(last.supplier_code[-3:]) + 1 if last else 1
    return f"SUP{year}{seq:03d}"


@router.get("", response_model=PaginatedResponse)
def list_suppliers(
    keyword: str = Query(None),
    coop_status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(Supplier).filter(Supplier.deleted_at == None)
    if keyword:
        q = q.filter(Supplier.name.contains(keyword))
    if coop_status:
        q = q.filter(Supplier.coop_status == coop_status)

    total = q.count()
    suppliers = q.order_by(Supplier.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()

    items = []
    for s in suppliers:
        order_count = db.query(InboundRecord).filter(InboundRecord.supplier_id == s.id).count()
        total_amt = db.query(InboundRecord).filter(InboundRecord.supplier_id == s.id).with_entities(
            InboundRecord.total_amount).all()
        total_amount = sum(float(t[0]) for t in total_amt if t[0])
        items.append({
            "id": s.id, "supplier_code": s.supplier_code, "name": s.name,
            "credit_code": s.credit_code, "contact_person": s.contact_person,
            "contact_phone": s.contact_phone, "address": s.address,
            "business_scope": s.business_scope, "coop_status": s.coop_status.value,
            "remark": s.remark, "order_count": order_count, "total_amount": total_amount,
            "created_at": s.created_at,
        })
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size,
                             total_pages=(total + page_size - 1) // page_size)


@router.post("", response_model=MessageResponse)
def create_supplier(data: SupplierCreate, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    code = generate_supplier_code(db)
    s = Supplier(supplier_code=code, **data.model_dump())
    db.add(s)
    log = AuditLog(user_id=user.id, username=user.username, action_type="create",
                   action_detail=f"新增供应商：{s.name}（编号：{code}）",
                   target_type="supplier", target_id=s.id, ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    return MessageResponse(message=f"供应商创建成功，编号：{code}")


@router.put("/{supplier_id}", response_model=MessageResponse)
def update_supplier(supplier_id: int, data: SupplierCreate,
                    user: User = Depends(require_admin), db: Session = Depends(get_db)):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="供应商不存在")
    for k, v in data.model_dump().items():
        setattr(s, k, v)
    db.commit()
    return MessageResponse(message="供应商信息已更新")


@router.delete("/{supplier_id}", response_model=MessageResponse)
def delete_supplier(supplier_id: int, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    s = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="供应商不存在")
    s.deleted_at = datetime.utcnow()
    s.coop_status = CoopStatus.inactive
    db.commit()
    return MessageResponse(message="供应商已停用")
