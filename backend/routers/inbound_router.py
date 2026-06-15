"""
入库记录路由
"""
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, date
from database import get_db
from models import InboundRecord, Material, AuditLog, User
from schemas import InboundCreate, InboundResponse, PaginatedResponse, MessageResponse
from auth import get_current_user, require_admin
from excel_utils import create_workbook, write_row, apply_fill, add_summary_row, finalize

router = APIRouter(prefix="/api/inbound-records", tags=["入库管理"])


def generate_inbound_code(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    last = db.query(InboundRecord).filter(InboundRecord.inbound_code.like(f"RK{today}%"))\
             .order_by(InboundRecord.inbound_code.desc()).first()
    seq = int(last.inbound_code[-4:]) + 1 if last else 1
    return f"RK{today}{seq:04d}"


@router.get("", response_model=PaginatedResponse)
def list_inbound(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    start_date: date = Query(None),
    end_date: date = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(InboundRecord).filter(InboundRecord.deleted_at == None)
    if start_date:
        q = q.filter(InboundRecord.inbound_date >= start_date)
    if end_date:
        q = q.filter(InboundRecord.inbound_date <= end_date)

    total = q.count()
    records = q.order_by(InboundRecord.inbound_date.desc()).offset((page-1)*page_size).limit(page_size).all()

    items = []
    for r in records:
        items.append({
            "id": r.id, "inbound_code": r.inbound_code, "material_id": r.material_id,
            "material_name": r.material.name if r.material else None,
            "batch_no": r.batch_no, "quantity": r.quantity,
            "unit_price": float(r.unit_price), "total_amount": float(r.total_amount),
            "supplier_name": r.supplier.name if r.supplier else None,
            "inbound_date": r.inbound_date, "operator_name": r.operator.real_name if r.operator else None,
        })
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size,
                             total_pages=(total + page_size - 1) // page_size)


@router.post("", response_model=MessageResponse)
def create_inbound(data: InboundCreate, user: User = Depends(require_admin), db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == data.material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="耗材不存在")

    code = generate_inbound_code(db)
    total_amount = data.quantity * data.unit_price

    r = InboundRecord(
        inbound_code=code, material_id=data.material_id, batch_no=data.batch_no,
        quantity=data.quantity, unit_price=data.unit_price, total_amount=total_amount,
        supplier_id=data.supplier_id, purchase_date=data.purchase_date,
        fund_source=data.fund_source, operator_id=user.id, remark=data.remark,
    )
    db.add(r)

    # 手动更新库存（触发器在 ORM 层面不会生效，手动处理）
    material.stock_qty += data.quantity
    if data.unit_price > 0:
        material.unit_price = data.unit_price
    if not material.supplier_id:
        material.supplier_id = data.supplier_id

    log = AuditLog(user_id=user.id, username=user.username, action_type="inbound",
                   action_detail=f"入库：{material.name} {data.quantity}{material.unit}（单号：{code}）",
                   target_type="inbound", target_id=r.id, ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    return MessageResponse(message=f"入库成功，单号：{code}")


@router.get("/{record_id}")
def get_inbound(record_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(InboundRecord).filter(InboundRecord.id == record_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {
        "id": r.id, "inbound_code": r.inbound_code, "material_name": r.material.name,
        "batch_no": r.batch_no, "quantity": r.quantity, "unit_price": float(r.unit_price),
        "total_amount": float(r.total_amount), "supplier_name": r.supplier.name,
        "purchase_date": r.purchase_date, "inbound_date": r.inbound_date,
        "operator_name": r.operator.real_name, "remark": r.remark,
    }


# ═══════════════════════════════════════════════════════
#  Excel 导出
# ═══════════════════════════════════════════════════════

@router.get("/export/excel")
def export_inbound_excel(
    start_date: date = Query(None),
    end_date: date = Query(None),
    ids: str = Query(None, description="逗号分隔的记录ID，如 1,3,5"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    导出入库记录为 Excel (.xlsx) 文件，支持按日期范围和ID筛选。
    """
    q = db.query(InboundRecord).filter(InboundRecord.deleted_at == None)
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(InboundRecord.id.in_(id_list))
    if start_date:
        q = q.filter(InboundRecord.inbound_date >= start_date)
    if end_date:
        q = q.filter(InboundRecord.inbound_date <= end_date)

    records = q.order_by(InboundRecord.inbound_date.desc()).all()

    headers = ["序号", "入库单号", "耗材名称", "规格型号", "批次号", "入库数量",
               "单价(元)", "总金额(元)", "供应商", "入库日期", "经手人", "备注"]
    widths = [6, 20, 18, 20, 18, 10, 12, 14, 22, 22, 12, 18]
    wb, ws = create_workbook("入库记录明细", headers, widths)



    total_qty = 0
    total_amt = 0.0
    for idx, r in enumerate(records, 1):
        row = idx + 2
        values = [idx, r.inbound_code,
                  r.material.name if r.material else "",
                  r.material.spec if r.material else "",
                  r.batch_no, r.quantity,
                  round(float(r.unit_price), 2),
                  round(float(r.total_amount), 2),
                  r.supplier.name if r.supplier else "",
                  r.inbound_date.strftime("%Y-%m-%d %H:%M") if r.inbound_date else "",
                  r.operator.real_name if r.operator else "",
                  r.remark or ""]
        write_row(ws, row, values)
        total_qty += r.quantity
        total_amt += float(r.total_amount)

    summary_row = len(records) + 3
    if records:
        add_summary_row(ws, summary_row, 12,
            f"共 {len(records)} 条记录", {6: f"合计: {total_qty}", 8: f"合计: {round(total_amt,2)}"})

    filename = f"入库记录_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        finalize(wb),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    )
