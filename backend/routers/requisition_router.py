"""
领用申请路由：CRUD + 状态流转
"""
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date
from database import get_db
from models import Requisition, RequisitionItem, Material, AuditLog, User, ReqStatus
from schemas import (RequisitionCreate, RequisitionUpdate, RequisitionResponse,
                     PaginatedResponse, MessageResponse)
from auth import get_current_user, require_admin
from config import AUTO_APPROVE_THRESHOLD
from excel_utils import create_workbook, write_row, apply_fill, add_summary_row, finalize

router = APIRouter(prefix="/api/requisitions", tags=["领用申请"])


def generate_req_code(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    last = db.query(Requisition).filter(Requisition.req_code.like(f"LY{today}%"))\
             .order_by(Requisition.req_code.desc()).first()
    seq = int(last.req_code[-4:]) + 1 if last else 1
    return f"LY{today}{seq:04d}"

def generate_item_code(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    last = db.query(RequisitionItem).filter(
        RequisitionItem.item_code.like(f"ITM{today}%")
    ).order_by(RequisitionItem.item_code.desc()).first()
    seq = int(last.item_code[-3:]) + 1 if last else 1
    return f"ITM{today}{seq:03d}"


def req_to_dict(r: Requisition) -> dict:
    items = []
    for i in r.items:
        m = i.material
        items.append({
            "item_id": i.id, "item_code": i.item_code,
            "material_id": i.material_id,
            "material_name": m.name if m else "", "material_spec": m.spec if m else "",
            "req_quantity": i.req_quantity, "actual_quantity": i.actual_quantity,
            "return_quantity": i.return_quantity, "returned_at": i.returned_at,
        })
    return {
        "id": r.id, "req_code": r.req_code,
        "applicant_name": r.applicant.real_name if r.applicant else "",
        "purpose": r.purpose, "use_date": r.use_date,
        "total_amount": float(r.total_amount), "status": r.status.value,
        "approver_name": r.approver.real_name if r.approver else None,
        "approval_comment": r.approval_comment,
        "delivered_at": r.delivered_at, "signed_at": r.signed_at,
        "item_count": len(r.items), "total_quantity": sum(i.req_quantity for i in r.items),
        "items": items, "created_at": r.created_at,
    }


@router.get("", response_model=PaginatedResponse)
def list_requisitions(
    status: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    q = db.query(Requisition).options(joinedload(Requisition.items).joinedload(RequisitionItem.material))
    # 教师只能看自己的
    if user.role.value == "teacher":
        q = q.filter(Requisition.applicant_id == user.id)
    if status:
        q = q.filter(Requisition.status == status)

    total = q.count()
    reqs = q.order_by(Requisition.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
    return PaginatedResponse(items=[req_to_dict(r) for r in reqs], total=total,
                             page=page, page_size=page_size,
                             total_pages=(total + page_size - 1) // page_size)


@router.post("", response_model=MessageResponse)
def create_requisition(data: RequisitionCreate, user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    code = generate_req_code(db)
    total_amount = 0.0

    # 校验耗材和库存
    for item in data.items:
        m = db.query(Material).filter(Material.id == item.material_id, Material.status == 1).first()
        if not m:
            raise HTTPException(status_code=404, detail=f"耗材ID {item.material_id} 不存在或已停用")
        if item.req_quantity > m.stock_qty:
            raise HTTPException(status_code=400,
                detail=f"耗材 '{m.name}' 库存不足（可用：{m.stock_qty}，申请：{item.req_quantity}）")
        total_amount += float(m.unit_price) * item.req_quantity

    # 自动审批：低于阈值自动通过
    auto_approved = total_amount < AUTO_APPROVE_THRESHOLD
    r = Requisition(req_code=code, applicant_id=user.id, purpose=data.purpose,
                    use_date=data.use_date, total_amount=total_amount,
                    status=ReqStatus.approved if auto_approved else ReqStatus.pending,
                    approver_id=None,
                    approved_at=datetime.utcnow() if auto_approved else None,
                    approval_comment="系统自动审批（低于阈值）" if auto_approved else None,
                    remark=data.remark)
    db.add(r)
    db.flush()

    for item in data.items:
        icode = generate_item_code(db)
        ri = RequisitionItem(item_code=icode, requisition_id=r.id,
                             material_id=item.material_id, req_quantity=item.req_quantity)
        db.add(ri)

    action_type = "auto_approve" if auto_approved else "apply"
    detail = f"提交领用申请（单号：{code}）" + (" [系统自动审批]" if auto_approved else "")
    log = AuditLog(user_id=user.id, username=user.username, action_type=action_type,
                   action_detail=detail, target_type="requisition",
                   target_id=r.id, ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    msg = f"领用申请已自动审批，单号：{code}" if auto_approved else f"领用申请已提交，单号：{code}"
    return MessageResponse(message=msg)


@router.get("/{req_id}")
def get_requisition(req_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(Requisition).options(joinedload(Requisition.items).joinedload(RequisitionItem.material))\
          .filter(Requisition.id == req_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="申请不存在")
    # 教师只能看自己
    if user.role.value == "teacher" and r.applicant_id != user.id:
        raise HTTPException(status_code=403, detail="无权查看")
    return req_to_dict(r)


@router.put("/{req_id}", response_model=MessageResponse)
def update_requisition(req_id: int, data: RequisitionUpdate,
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(Requisition).filter(Requisition.id == req_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="申请不存在")
    if r.applicant_id != user.id:
        raise HTTPException(status_code=403, detail="只能修改自己的申请")
    if r.status not in [ReqStatus.draft, ReqStatus.returned]:
        raise HTTPException(status_code=400, detail="当前状态不可修改")

    if data.purpose: r.purpose = data.purpose
    if data.use_date: r.use_date = data.use_date
    if data.remark: r.remark = data.remark
    db.commit()
    return MessageResponse(message="申请已更新")


@router.put("/{req_id}/submit", response_model=MessageResponse)
def submit_requisition(req_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(Requisition).filter(Requisition.id == req_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="申请不存在")
    if r.applicant_id != user.id:
        raise HTTPException(status_code=403, detail="只能提交自己的申请")
    if r.status != ReqStatus.draft:
        raise HTTPException(status_code=400, detail="只有草稿状态可提交")

    r.status = ReqStatus.pending
    db.commit()
    return MessageResponse(message="申请已提交，等待审批")


# ═══════════════════════════════════════════════════════
#  Excel 导出
# ═══════════════════════════════════════════════════════

STATUS_LABELS = {
    "draft": "草稿", "pending": "待审批", "approved": "已审批",
    "rejected": "已驳回", "returned": "退回修改",
    "delivered": "已出库", "signed": "已签收", "returned_stock": "已归还"
}

@router.get("/export/excel")
def export_requisitions_excel(
    status: str = Query(None, description="按状态筛选"),
    start_date: date = Query(None),
    end_date: date = Query(None),
    ids: str = Query(None, description="逗号分隔的申请ID"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    导出领用申请记录为 Excel (.xlsx) 文件，支持按状态、日期和ID筛选。
    """
    q = db.query(Requisition).options(
        joinedload(Requisition.items).joinedload(RequisitionItem.material)
    )
    if user.role.value == "teacher":
        q = q.filter(Requisition.applicant_id == user.id)
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(Requisition.id.in_(id_list))
    if status:
        q = q.filter(Requisition.status == status)
    if start_date:
        q = q.filter(Requisition.created_at >= start_date)
    if end_date:
        q = q.filter(Requisition.created_at <= end_date)

    reqs = q.order_by(Requisition.created_at.desc()).all()

    headers = ["序号", "申请单号", "申请人", "用途", "使用日期", "耗材明细",
               "申请总量", "总金额(元)", "状态", "审批人", "审批意见", "出库时间", "签收时间", "申请时间"]
    widths = [6, 20, 12, 28, 14, 40, 10, 14, 10, 12, 18, 22, 22, 22]
    wb, ws = create_workbook("领用申请记录", headers, widths)

    total_qty = 0
    total_amt = 0.0
    for idx, r in enumerate(reqs, 1):
        row = idx + 2
        detail = "、".join(
            f"{it.material.name if it.material else ''} ×{it.req_quantity}"
            for it in r.items
        )
        values = [
            idx, r.req_code,
            r.applicant.real_name if r.applicant else "",
            r.purpose,
            r.use_date.strftime("%Y-%m-%d") if r.use_date else "",
            detail,
            sum(it.req_quantity for it in r.items),
            round(float(r.total_amount), 2),
            STATUS_LABELS.get(r.status.value, r.status.value),
            r.approver.real_name if r.approver else "",
            r.approval_comment or "",
            r.delivered_at.strftime("%Y-%m-%d %H:%M") if r.delivered_at else "",
            r.signed_at.strftime("%Y-%m-%d %H:%M") if r.signed_at else "",
            r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
        ]
        write_row(ws, row, values)

        # 状态着色
        st = r.status.value
        if st in ("rejected",):
            apply_fill(ws, row, len(headers), "FCE4D6")
        elif st in ("returned",):
            apply_fill(ws, row, len(headers), "FFF2CC")
        elif st in ("draft",):
            apply_fill(ws, row, len(headers), "F2F2F2")
        elif st in ("delivered", "signed", "returned_stock"):
            apply_fill(ws, row, len(headers), "E2EFDA")

        total_qty += sum(it.req_quantity for it in r.items)
        total_amt += float(r.total_amount)

    summary_row = len(reqs) + 3
    if reqs:
        add_summary_row(ws, summary_row, len(headers),
            f"共 {len(reqs)} 条申请", {7: f"合计: {total_qty}", 8: f"合计: {round(total_amt,2)}"})

    filename = f"领用记录_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        finalize(wb),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    )
