# 电子信息系耗材管理系统 — API接口清单

> Base URL：`http://localhost:8000`
> Swagger文档：`http://localhost:8000/docs`
> 认证方式：JWT Bearer Token（Header: `Authorization: Bearer <token>`）

---

## 1. 认证模块 (`/api/auth`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|:--:|
| POST | `/api/auth/login` | 用户登录，返回JWT Token | 无 |
| GET | `/api/auth/me` | 获取当前用户信息 | 登录 |
| POST | `/api/auth/logout` | 登出，记录日志 | 登录 |

**登录请求示例**：
```json
POST /api/auth/login
{"username": "admin", "password": "123456"}

Response:
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {"id": 1, "username": "admin", "real_name": "张管理", "role": "admin"}
}
```

---

## 2. 耗材管理 (`/api/materials`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|:--:|
| GET | `/api/materials` | 耗材列表（分页+筛选） | 登录 |
| GET | `/api/materials/{id}` | 耗材详情 | 登录 |
| POST | `/api/materials` | 新增耗材 | admin |
| PUT | `/api/materials/{id}` | 修改耗材信息 | admin |
| PUT | `/api/materials/{id}/adjust-stock` | 库存调整 | admin |

**查询参数**：`keyword`, `category_id`, `alert_status`(low/high/normal), `status`, `page`, `page_size`

---

## 3. 入库管理 (`/api/inbound-records`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|:--:|
| GET | `/api/inbound-records` | 入库记录列表 | 登录 |
| GET | `/api/inbound-records/{id}` | 入库记录详情 | 登录 |
| POST | `/api/inbound-records` | 创建入库记录 | admin |

**创建入库请求**：
```json
{
  "material_id": 1,
  "batch_no": "PO20260615-001",
  "quantity": 100,
  "unit_price": 0.5,
  "supplier_id": 1,
  "purchase_date": "2026-06-15"
}
```
**自动处理**：库存自动累加 `materials.stock_qty += quantity`

---

## 4. 领用申请 (`/api/requisitions`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|:--:|
| GET | `/api/requisitions` | 申请列表 | 登录 |
| GET | `/api/requisitions/{id}` | 申请详情（含明细） | 登录 |
| POST | `/api/requisitions` | 提交领用申请 | 登录 |
| PUT | `/api/requisitions/{id}` | 修改草稿 | 本人 |
| PUT | `/api/requisitions/{id}/submit` | 提交草稿 | 本人 |

**权限**：教师只能看到自己的申请

---

## 5. 审批管理 (`/api/approvals`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|:--:|
| PUT | `/api/approvals/{id}/review` | 审批（同意/驳回/退回） | approver |
| PUT | `/api/approvals/{id}/deliver` | 确认出库 | admin |
| PUT | `/api/approvals/{id}/sign` | 签收确认 | 申请人 |

**审批请求**：
```json
{"action": "approve", "comment": "同意"}
// action: approve | reject | return
```

**出库请求**：
```json
{"items": [{"item_id": 1, "actual_qty": 10}]}
```

---

## 6. 供应商管理 (`/api/suppliers`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|:--:|
| GET | `/api/suppliers` | 供应商列表 | 登录 |
| POST | `/api/suppliers` | 新增供应商 | admin |
| PUT | `/api/suppliers/{id}` | 修改供应商 | admin |
| DELETE | `/api/suppliers/{id}` | 停用供应商（软删除） | admin |

---

## 7. 报表导出 (`/api/reports`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|:--:|
| GET | `/api/reports/stock` | 库存报表（按类别汇总） | 登录 |
| GET | `/api/reports/consumption` | 消耗趋势 | 登录 |
| GET | `/api/reports/inbound-summary` | 入库汇总 | 登录 |
| GET | `/api/reports/supplier-stats` | 供应商供货统计 | 登录 |

---

## 8. 操作日志 (`/api/audit-logs`)

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|:--:|
| GET | `/api/audit-logs` | 日志列表 | 登录 |
| GET | `/api/audit-logs/action-types` | 操作类型枚举 | 登录 |

**教师只能看自己的日志**

---

## 9. 角色权限速查

| 操作 | admin | teacher | approver | sysadmin |
|------|:--:|:--:|:--:|:--:|
| 登录/查看库存 | ✓ | ✓ | ✓ | ✓ |
| 入库/出库 | ✓ | ✗ | ✗ | ✓ |
| 提交领用申请 | ✓ | ✓ | ✓ | ✗ |
| 审批申请 | ✗ | ✗ | ✓ | ✗ |
| 供应商管理 | ✓ | ✗ | ✗ | ✓ |
| 查看全部日志 | ✓ | ✗ | ✗ | ✓ |
| 用户管理 | ✗ | ✗ | ✗ | ✓ |
