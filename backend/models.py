"""
SQLAlchemy ORM 模型定义（对应 schema.sql）
"""
from datetime import datetime
from sqlalchemy import (Column, Integer, String, Text, Float, Numeric,
                        Date, DateTime, Enum, ForeignKey, Index, CheckConstraint,
                        UniqueConstraint, JSON, text)
from sqlalchemy.orm import relationship
from database import Base
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    teacher = "teacher"
    approver = "approver"
    sysadmin = "sysadmin"

class CoopStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"

class ReqStatus(str, enum.Enum):
    draft = "draft"
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    returned = "returned"
    delivered = "delivered"
    signed = "signed"
    returned_stock = "returned_stock"

class ReturnCondition(str, enum.Enum):
    good = "good"
    damaged = "damaged"
    lost = "lost"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(50), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.teacher)
    phone = Column(String(20))
    email = Column(String(100))
    avatar_initials = Column(String(4))
    avatar_url = Column(String(200))
    status = Column(Integer, nullable=False, default=1)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"))
    sort_order = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    parent = relationship("Category", remote_side=[id], backref="children")
    __table_args__ = (UniqueConstraint("name", "parent_id"),)


class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    credit_code = Column(String(50))
    contact_person = Column(String(50), nullable=False)
    contact_phone = Column(String(30), nullable=False)
    address = Column(String(300))
    business_scope = Column(String(500))
    coop_status = Column(Enum(CoopStatus), nullable=False, default=CoopStatus.active)
    remark = Column(String(500))
    deleted_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    spec = Column(String(100), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    unit = Column(String(20), nullable=False, default="个")
    unit_price = Column(Numeric(12, 2), nullable=False, default=0)
    stock_qty = Column(Integer, nullable=False, default=0)
    safety_stock_min = Column(Integer)
    safety_stock_max = Column(Integer)
    location = Column(String(100), nullable=False, default="")
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    fund_source = Column(String(100))
    remark = Column(String(500))
    status = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category")
    supplier = relationship("Supplier")
    __table_args__ = (UniqueConstraint("name", "spec"),)


class InboundRecord(Base):
    __tablename__ = "inbound_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    inbound_code = Column(String(20), unique=True, nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    batch_no = Column(String(30), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_amount = Column(Numeric(14, 2), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    purchase_date = Column(Date)
    inbound_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    fund_source = Column(String(100))
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    remark = Column(String(500))
    deleted_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    material = relationship("Material")
    supplier = relationship("Supplier")
    operator = relationship("User")


class Requisition(Base):
    __tablename__ = "requisitions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    req_code = Column(String(20), unique=True, nullable=False)
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    purpose = Column(String(300), nullable=False)
    use_date = Column(Date)
    total_amount = Column(Numeric(14, 2), nullable=False, default=0)
    status = Column(Enum(ReqStatus), nullable=False, default=ReqStatus.draft)
    approver_id = Column(Integer, ForeignKey("users.id"))
    approval_comment = Column(String(300))
    approved_at = Column(DateTime)
    deliverer_id = Column(Integer, ForeignKey("users.id"))
    delivered_at = Column(DateTime)
    signed_at = Column(DateTime)
    remark = Column(String(500))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    applicant = relationship("User", foreign_keys=[applicant_id])
    approver = relationship("User", foreign_keys=[approver_id])
    deliverer = relationship("User", foreign_keys=[deliverer_id])
    items = relationship("RequisitionItem", back_populates="requisition", cascade="all, delete-orphan")


class RequisitionItem(Base):
    __tablename__ = "requisition_items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    item_code = Column(String(20), unique=True, nullable=False)
    requisition_id = Column(Integer, ForeignKey("requisitions.id", ondelete="CASCADE"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    req_quantity = Column(Integer, nullable=False)
    actual_quantity = Column(Integer)
    return_quantity = Column(Integer, default=0)
    returned_at = Column(DateTime)

    requisition = relationship("Requisition", back_populates="items")
    material = relationship("Material")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    username = Column(String(50), nullable=False)
    action_type = Column(String(30), nullable=False)
    action_detail = Column(String(1000), nullable=False)
    target_type = Column(String(50))
    target_id = Column(Integer)
    ip_address = Column(String(45))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class ReturnRecord(Base):
    """物品归还记录表"""
    __tablename__ = "return_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    return_code = Column(String(20), unique=True, nullable=False)
    requisition_id = Column(Integer, ForeignKey("requisitions.id"), nullable=False)
    requisition_item_id = Column(Integer, ForeignKey("requisition_items.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    return_quantity = Column(Integer, nullable=False)
    return_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    return_condition = Column(Enum(ReturnCondition), nullable=False, default=ReturnCondition.good)
    overdue_days = Column(Integer, default=0)
    fine_rate = Column(Numeric(10, 2), default=0)
    fine_amount = Column(Numeric(14, 2), default=0)
    fine_paid = Column(Integer, default=0)
    handler_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    remark = Column(String(500))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    requisition = relationship("Requisition", foreign_keys=[requisition_id])
    requisition_item = relationship("RequisitionItem", foreign_keys=[requisition_item_id])
    material = relationship("Material")
    handler = relationship("User")
