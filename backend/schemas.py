"""
Pydantic 请求/响应 Schema
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field


# ─── Auth ───
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserInfo(BaseModel):
    id: int
    username: str
    real_name: str
    role: str
    avatar_initials: Optional[str] = None

    class Config: from_attributes = True

# ─── Material ───
class MaterialBase(BaseModel):
    name: str = Field(..., max_length=100)
    spec: str = Field(..., max_length=100)
    category_id: int
    unit: str = "个"
    unit_price: float = 0
    safety_stock_min: Optional[int] = None
    safety_stock_max: Optional[int] = None
    location: str = ""
    supplier_id: Optional[int] = None
    fund_source: Optional[str] = None
    remark: Optional[str] = None

class MaterialCreate(MaterialBase):
    pass

class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    spec: Optional[str] = None
    category_id: Optional[int] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    safety_stock_min: Optional[int] = None
    safety_stock_max: Optional[int] = None
    location: Optional[str] = None
    supplier_id: Optional[int] = None
    fund_source: Optional[str] = None
    remark: Optional[str] = None
    status: Optional[int] = None

class MaterialResponse(MaterialBase):
    id: int
    material_code: str
    stock_qty: int
    stock_value: float = 0
    alert_status: str = "normal"
    category_name: Optional[str] = None
    supplier_name: Optional[str] = None
    status: int = 1
    created_at: datetime
    updated_at: datetime

    class Config: from_attributes = True

class MaterialStockAdjust(BaseModel):
    adjust_qty: int = Field(..., description="正数增加，负数减少")
    reason: str = Field(..., max_length=500)

# ─── Inbound ───
class InboundCreate(BaseModel):
    material_id: int
    batch_no: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    supplier_id: int
    purchase_date: Optional[date] = None
    fund_source: Optional[str] = None
    remark: Optional[str] = None

class InboundResponse(BaseModel):
    id: int
    inbound_code: str
    material_id: int
    material_name: Optional[str] = None
    batch_no: str
    quantity: int
    unit_price: float
    total_amount: float
    supplier_name: Optional[str] = None
    inbound_date: datetime
    operator_name: Optional[str] = None

    class Config: from_attributes = True

# ─── Requisition ───
class ReqItemCreate(BaseModel):
    material_id: int
    req_quantity: int = Field(..., gt=0)

class RequisitionCreate(BaseModel):
    purpose: str = Field(..., max_length=300)
    use_date: Optional[date] = None
    items: List[ReqItemCreate] = Field(..., min_length=1)
    remark: Optional[str] = None

class RequisitionUpdate(BaseModel):
    purpose: Optional[str] = None
    use_date: Optional[date] = None
    items: Optional[List[ReqItemCreate]] = None
    remark: Optional[str] = None

class RequisitionResponse(BaseModel):
    id: int
    req_code: str
    applicant_name: str
    purpose: str
    use_date: Optional[date] = None
    total_amount: float
    status: str
    approver_name: Optional[str] = None
    approval_comment: Optional[str] = None
    delivered_at: Optional[datetime] = None
    signed_at: Optional[datetime] = None
    item_count: int = 0
    total_quantity: int = 0
    items: List[dict] = []
    created_at: datetime

    class Config: from_attributes = True

# ─── Approval ───
class ApprovalAction(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|return)$")
    comment: Optional[str] = None

class DeliveryConfirm(BaseModel):
    items: List[dict]  # [{item_id: 1, actual_qty: 10}, ...]

# ─── Supplier ───
class SupplierCreate(BaseModel):
    name: str = Field(..., max_length=200)
    credit_code: Optional[str] = None
    contact_person: str
    contact_phone: str
    address: Optional[str] = None
    business_scope: Optional[str] = None
    remark: Optional[str] = None

class SupplierResponse(SupplierCreate):
    id: int
    supplier_code: str
    coop_status: str
    order_count: int = 0
    total_amount: float = 0
    created_at: datetime

    class Config: from_attributes = True

# ─── Report ───
class ReportFilter(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    category_id: Optional[int] = None

# ─── Return ───
class ReturnItemEntry(BaseModel):
    requisition_item_id: int = Field(..., description="领用明细ID")
    return_quantity: int = Field(..., gt=0, description="归还数量")
    return_condition: str = Field("good", pattern="^(good|damaged|lost)$", description="归还状态: good/damaged/lost")

class ReturnCreate(BaseModel):
    requisition_id: int = Field(..., description="领用申请ID")
    items: List[ReturnItemEntry] = Field(..., min_length=1, description="归还明细列表")
    remark: Optional[str] = Field(None, max_length=500)

class OverduePreviewRequest(BaseModel):
    requisition_id: int = Field(..., description="领用申请ID")

class OverduePreviewResponse(BaseModel):
    requisition_id: int
    req_code: str
    applicant_name: str
    delivered_at: Optional[datetime] = None
    overdue_days: int = 0
    items: List[dict] = []
    total_fine: float = 0.0

class ReturnRecordResponse(BaseModel):
    id: int
    return_code: str
    requisition_id: int
    req_code: Optional[str] = None
    item_code: Optional[str] = None
    material_name: Optional[str] = None
    material_spec: Optional[str] = None
    return_quantity: int
    return_condition: str
    overdue_days: int = 0
    fine_rate: float = 0
    fine_amount: float = 0
    fine_paid: int = 0
    handler_name: Optional[str] = None
    return_date: Optional[datetime] = None
    remark: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config: from_attributes = True

class ReturnExportFilter(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    return_condition: Optional[str] = None
    keyword: Optional[str] = None
    requisition_id: Optional[int] = None

class FineUpdate(BaseModel):
    fine_paid: int = Field(..., ge=0, le=1, description="0=未缴, 1=已缴")

# ─── Common ───
class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int

class MessageResponse(BaseModel):
    message: str
    success: bool = True
