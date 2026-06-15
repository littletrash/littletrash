# 电子信息系耗材管理系统 — 数据库ER说明

> 对应文件：`schema.sql` · `seed.sql`
> 数据库名：`material_mgmt`
> 字符集：`utf8mb4`

---

## 实体关系总览

```
┌──────────┐       ┌──────────────┐       ┌──────────────┐
│  users   │       │  categories  │       │  suppliers   │
│ (用户表) │       │  (耗材类别)   │       │  (供应商)     │
└────┬─────┘       └──────┬───────┘       └──────┬───────┘
     │                    │                      │
     │ 1:N (操作人)        │ 1:N (分类)           │ 1:N (供货)
     │                    │                      │
     ▼                    ▼                      ▼
┌──────────────────────────────────────────────────────────┐
│                      materials (耗材信息主表)              │
│  核心字段：name + spec 联合唯一                            │
│  库存字段 stock_qty 由触发器自动维护                        │
└──────────┬──────────────────────────┬────────────────────┘
           │                          │
           │ 1:N                      │ 1:N
           ▼                          ▼
┌──────────────────┐       ┌──────────────────────────┐
│ inbound_records  │       │   requisition_items      │
│   (入库记录)      │       │     (领用明细)            │
│  触发器更新库存    │       │    N:1 → requisitions    │
└──────────────────┘       └───────────┬──────────────┘
                                       │ N:1
                                       ▼
                             ┌──────────────────┐
                             │   requisitions   │
                             │   (领用申请)      │
                             │  状态机管理流转    │
                             └──────────────────┘

┌──────────────────┐
│   audit_logs     │  ← 所有表操作均记入此日志（只追加）
│   (操作日志)      │
└──────────────────┘
```

---

## 核心表关系详解

### 1. users（用户表）→ 多角色引用

用户表被多张表引用，扮演不同角色：

| 引用表 | 外键字段 | 角色含义 |
|--------|----------|----------|
| inbound_records | `operator_id` | 入库操作人 |
| requisitions | `applicant_id` | 领用申请人 |
| requisitions | `approver_id` | 审批人 |
| requisitions | `deliverer_id` | 出库操作人 |
| audit_logs | `user_id` | 操作人（可为 NULL 表示系统操作） |

`role` 字段使用 ENUM：
- `admin` — 耗材管理员（可入库/出库/盘点）
- `teacher` — 教师（可浏览/申请）
- `approver` — 系部负责人（可审批）
- `sysadmin` — 系统管理员（全局配置）

---

### 2. materials（耗材信息）— 核心主表

```
materials
├── category_id → categories.id       (类别)
├── supplier_id → suppliers.id        (主要供应商，可空)
├── name + spec = 联合唯一约束         (同名同规格只能建一条)
├── stock_qty = 触发器自动维护         (禁止手动修改)
├── safety_stock_min/max = 预警阈值
└── status = 1(正常) / 0(停用)
```

**库存更新规则**：
- 入库 → `AFTER INSERT ON inbound_records` → `stock_qty += quantity`
- 出库 → 通过存储过程 `sp_confirm_delivery` → `stock_qty -= actual_quantity`
- 红冲 → 通过存储过程 `sp_reverse_inbound` → `stock_qty -= quantity`
- 预警 → `AFTER UPDATE ON materials` → 自动写 `audit_logs` 报警记录

---

### 3. requisitions（领用申请）— 状态机

```
   draft(草稿)
      │
      ▼
  pending(待审批) ──→ returned(退回修改) ──→ pending
      │
      ├──→ rejected(已驳回) [终态]
      │
      └──→ approved(已审批)
               │
               ▼
          delivered(已出库)
               │
               ▼
            signed(已签收)
               │
               ▼ (仅可复用耗材)
        returned_stock(已归还) [终态]
```

**状态转换规则**：
- `draft → pending`：申请人提交
- `pending → approved/rejected/returned`：审批人操作
- `approved → delivered`：管理员确认出库（调用存储过程 `sp_confirm_delivery`）
- `delivered → signed`：教师签收
- `signed → returned_stock`：归还可复用耗材（管理员操作）

---

### 4. requisition_items（领用明细）— 一对多子表

每条领用申请可包含多条明细：

```
requisitions (1) ──→ (N) requisition_items
                            │
                            ├── material_id → materials.id
                            ├── req_quantity  (申请数量)
                            ├── actual_quantity (实际出库数量)
                            └── return_quantity (已归还数量，可复用耗材)
```

---

### 5. 审计与软删除策略

| 表 | 删除策略 | 说明 |
|----|----------|------|
| `inbound_records` | 软删除 (`deleted_at`) | 红冲时标记，不物理删除 |
| `suppliers` | 软删除 (`deleted_at`) | 保留历史供货记录 |
| `audit_logs` | **禁止删除** | 审计日志永久保留 |
| `requisitions` | **禁止删除** | 审批记录全程留痕 |
| `materials` | 状态标记 (`status`) | 停用而非删除 |
| `users` | 状态标记 (`status`) | 停用而非删除 |

---

### 6. 编号生成规则

| 实体 | 前缀 | 格式 | 示例 |
|------|------|------|------|
| 耗材编号 | HC | HC + YYYYMMDD + 4位流水 | `HC202606150001` |
| 入库单号 | RK | RK + YYYYMMDD + 4位流水 | `RK202606150001` |
| 申请编号 | LY | LY + YYYYMMDD + 4位流水 | `LY202606150001` |
| 明细编号 | ITM | ITM + YYYYMMDD + 3位流水 | `ITM20260615001` |
| 供应商编号 | SUP | SUP + YYYY + 3位流水 | `SUP2024001` |

---

## 索引设计

高頻查询字段均已建索引：

- `materials`: `category_id`, `name`, `stock_qty`, `status`, `(name, spec)` 联合唯一
- `requisitions`: `applicant_id`, `approver_id`, `status`, `created_at`
- `inbound_records`: `material_id`, `supplier_id`, `inbound_date`, `batch_no`
- `audit_logs`: `user_id`, `action_type`, `created_at`, `(target_type, target_id)`
- `suppliers`: `name`, `coop_status`

---

## 视图用途

| 视图 | 用途 |
|------|------|
| `v_stock_overview` | 库存概览页 — 关联类别名、供应商名、预警状态 |
| `v_requisition_full` | 领用申请详情 — 关联申请人、审批人、出库人姓名及明细统计 |
