"""
审批与出库路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from database import get_db
from models import Requisition, RequisitionItem, Material, AuditLog, User, ReqStatus
from schemas import ApprovalAction, DeliveryConfirm, MessageResponse
from auth import get_current_user, require_approver, require_admin
from config import AUTO_APPROVE_THRESHOLD

router = APIRouter(prefix="/api/approvals", tags=["审批管理"])


@router.put("/{req_id}/review", response_model=MessageResponse)
def review_requisition(req_id: int, action: ApprovalAction,
                       user: User = Depends(require_approver), db: Session = Depends(get_db)):
    r = db.query(Requisition).options(joinedload(Requisition.items)).filter(Requisition.id == req_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="申请不存在")
    if r.status != ReqStatus.pending:
        raise HTTPException(status_code=400, detail="当前状态不可审批")

    if action.action == "approve":
        r.status = ReqStatus.approved
        r.approver_id = user.id
        r.approved_at = datetime.utcnow()
        r.approval_comment = action.comment or "同意"
        detail = f"审批通过（单号：{r.req_code}）"
    elif action.action == "reject":
        r.status = ReqStatus.rejected
        r.approver_id = user.id
        r.approved_at = datetime.utcnow()
        r.approval_comment = action.comment or "驳回"
        detail = f"驳回申请（单号：{r.req_code}），理由：{r.approval_comment}"
    else:  # return
        r.status = ReqStatus.returned
        r.approver_id = user.id
        r.approved_at = datetime.utcnow()
        r.approval_comment = action.comment or "退回修改"
        detail = f"退回修改（单号：{r.req_code}）"

    log = AuditLog(user_id=user.id, username=user.username, action_type=action.action,
                   action_detail=detail, target_type="requisition", target_id=r.id, ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    return MessageResponse(message=f"操作成功：{'审批通过' if action.action=='approve' else '已驳回' if action.action=='reject' else '已退回修改'}")


@router.put("/{req_id}/deliver", response_model=MessageResponse)
def deliver_requisition(req_id: int, data: DeliveryConfirm,
                        user: User = Depends(require_admin), db: Session = Depends(get_db)):
    r = db.query(Requisition).options(joinedload(Requisition.items)).filter(Requisition.id == req_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="申请不存在")
    if r.status != ReqStatus.approved:
        raise HTTPException(status_code=400, detail="只有已审批的申请可以出库")

    # 校验库存并出库
    for item_data in data.items:
        item = db.query(RequisitionItem).filter(RequisitionItem.id == item_data["item_id"],
                                                 RequisitionItem.requisition_id == req_id).first()
        if not item:
            continue
        actual_qty = item_data["actual_qty"]
        m = db.query(Material).filter(Material.id == item.material_id).first()
        if m.stock_qty < actual_qty:
            raise HTTPException(status_code=400, detail=f"耗材 '{m.name}' 库存不足")
        m.stock_qty -= actual_qty
        item.actual_quantity = actual_qty

    r.status = ReqStatus.signed
    r.deliverer_id = user.id
    r.delivered_at = datetime.utcnow()
    r.signed_at = datetime.utcnow()

    log = AuditLog(user_id=user.id, username=user.username, action_type="outbound",
                   action_detail=f"确认出库（单号：{r.req_code}）", target_type="requisition",
                   target_id=r.id, ip_address="127.0.0.1")
    db.add(log)
    db.commit()
    return MessageResponse(message="出库完成")


@router.put("/{req_id}/sign", response_model=MessageResponse)
def sign_requisition(req_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(Requisition).filter(Requisition.id == req_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="申请不存在")
    if r.applicant_id != user.id:
        raise HTTPException(status_code=403, detail="只能签收自己的申请")
    if r.status != ReqStatus.delivered:
        raise HTTPException(status_code=400, detail="只有已出库的申请可以签收")

    r.status = ReqStatus.signed
    r.signed_at = datetime.utcnow()
    db.commit()
    return MessageResponse(message="签收成功")
