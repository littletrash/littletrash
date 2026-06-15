-- ============================================================
-- 电子信息系 · 耗材管理系统 — 数据库建表脚本
-- 目标数据库：MySQL 8.0+ / MariaDB 10.5+
-- 编码：UTF-8 (utf8mb4)
-- 作者：电子信息系耗材管理员
-- 日期：2026-06-15
-- 版本：V1.0
-- ============================================================

CREATE DATABASE IF NOT EXISTS material_mgmt
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE material_mgmt;

-- ============================================================
-- 1. 用户表 (users)
-- ============================================================
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY   COMMENT '主键',
    username        VARCHAR(50)  NOT NULL UNIQUE         COMMENT '登录用户名（工号）',
    password_hash   VARCHAR(255) NOT NULL                COMMENT '密码哈希（bcrypt）',
    real_name       VARCHAR(50)  NOT NULL                COMMENT '真实姓名',
    role            ENUM('admin','teacher','approver','sysadmin')
                                NOT NULL DEFAULT 'teacher' COMMENT '角色：admin=耗材管理员, teacher=教师, approver=系部负责人, sysadmin=系统管理员',
    phone           VARCHAR(20)  DEFAULT NULL             COMMENT '联系电话',
    email           VARCHAR(100) DEFAULT NULL             COMMENT '邮箱',
    avatar_initials VARCHAR(4)   DEFAULT NULL             COMMENT '头像缩写（姓氏首字）',
    status          TINYINT      NOT NULL DEFAULT 1       COMMENT '状态：1=正常, 0=停用',
    last_login_at   DATETIME     DEFAULT NULL             COMMENT '最后登录时间',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    INDEX idx_users_role (role),
    INDEX idx_users_status (status)
) ENGINE=InnoDB COMMENT='系统用户表';


-- ============================================================
-- 2. 耗材类别表 (categories)
-- ============================================================
DROP TABLE IF EXISTS categories;
CREATE TABLE categories (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY   COMMENT '主键',
    name            VARCHAR(50)  NOT NULL                COMMENT '类别名称',
    parent_id       BIGINT       DEFAULT NULL            COMMENT '父类别ID（NULL=一级类别）',
    sort_order      INT          NOT NULL DEFAULT 0      COMMENT '排序序号',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY uk_name_parent (name, parent_id),
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL,
    INDEX idx_parent (parent_id)
) ENGINE=InnoDB COMMENT='耗材类别表（树形结构）';


-- ============================================================
-- 3. 耗材信息表 (materials) — 核心表
-- ============================================================
DROP TABLE IF EXISTS materials;
CREATE TABLE materials (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY   COMMENT '主键',
    material_code   VARCHAR(20)  NOT NULL UNIQUE         COMMENT '耗材编号，规则：HC+年月日+4位流水号',
    name            VARCHAR(100) NOT NULL                COMMENT '耗材名称',
    spec            VARCHAR(100) NOT NULL                COMMENT '规格型号',
    category_id     BIGINT       NOT NULL                COMMENT '耗材类别ID',
    unit            VARCHAR(20)  NOT NULL DEFAULT '个'   COMMENT '计量单位',
    unit_price      DECIMAL(12,2) NOT NULL DEFAULT 0.00  COMMENT '参考单价（元）',
    stock_qty       INT          NOT NULL DEFAULT 0      COMMENT '当前库存数量（触发器自动维护）',
    safety_stock_min INT         DEFAULT NULL            COMMENT '安全库存下限（低于此值预警）',
    safety_stock_max INT         DEFAULT NULL            COMMENT '安全库存上限（高于此值预警）',
    location        VARCHAR(100) NOT NULL DEFAULT ''     COMMENT '存放位置',
    supplier_id     BIGINT       DEFAULT NULL            COMMENT '主要供应商ID',
    fund_source     VARCHAR(100) DEFAULT NULL            COMMENT '经费来源（预算项目名称）',
    remark          VARCHAR(500) DEFAULT NULL            COMMENT '备注',
    status          TINYINT      NOT NULL DEFAULT 1      COMMENT '状态：1=正常, 0=停用',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    UNIQUE KEY uk_name_spec (name, spec),                -- 同名称+同规格=同一耗材
    INDEX idx_category (category_id),
    INDEX idx_name (name),
    INDEX idx_stock (stock_qty),
    INDEX idx_status (status),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='耗材信息主表';


-- ============================================================
-- 4. 供应商表 (suppliers)
-- ============================================================
DROP TABLE IF EXISTS suppliers;
CREATE TABLE suppliers (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    supplier_code       VARCHAR(20)  NOT NULL UNIQUE      COMMENT '供应商编号',
    name                VARCHAR(200) NOT NULL             COMMENT '供应商全称',
    credit_code         VARCHAR(50)  DEFAULT NULL         COMMENT '统一社会信用代码',
    contact_person      VARCHAR(50)  NOT NULL             COMMENT '联系人',
    contact_phone       VARCHAR(30)  NOT NULL             COMMENT '联系电话',
    address             VARCHAR(300) DEFAULT NULL         COMMENT '地址',
    business_scope      VARCHAR(500) DEFAULT NULL         COMMENT '经营范围',
    coop_status         ENUM('active','inactive') NOT NULL DEFAULT 'active' COMMENT '合作状态',
    remark              VARCHAR(500) DEFAULT NULL         COMMENT '备注',
    deleted_at          DATETIME     DEFAULT NULL         COMMENT '软删除时间',
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_name (name),
    INDEX idx_coop_status (coop_status)
) ENGINE=InnoDB COMMENT='供应商信息表';


-- ============================================================
-- 5. 入库记录表 (inbound_records)
-- ============================================================
DROP TABLE IF EXISTS inbound_records;
CREATE TABLE inbound_records (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY   COMMENT '主键',
    inbound_code    VARCHAR(20)  NOT NULL UNIQUE         COMMENT '入库单号，规则：RK+年月日+4位流水号',
    material_id     BIGINT       NOT NULL                COMMENT '耗材ID',
    batch_no        VARCHAR(30)  NOT NULL                COMMENT '采购批次号',
    quantity        INT          NOT NULL                COMMENT '入库数量（必须为正数）',
    unit_price      DECIMAL(12,2) NOT NULL               COMMENT '入库单价（元）',
    total_amount    DECIMAL(14,2) NOT NULL               COMMENT '入库总金额 = quantity × unit_price',
    supplier_id     BIGINT       NOT NULL                COMMENT '供应商ID',
    purchase_date   DATE         DEFAULT NULL            COMMENT '采购日期',
    inbound_date    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入库日期',
    fund_source     VARCHAR(100) DEFAULT NULL            COMMENT '经费来源',
    operator_id     BIGINT       NOT NULL                COMMENT '入库操作人ID',
    remark          VARCHAR(500) DEFAULT NULL            COMMENT '备注',
    deleted_at      DATETIME     DEFAULT NULL            COMMENT '软删除（红冲标记）',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_material (material_id),
    INDEX idx_supplier (supplier_id),
    INDEX idx_inbound_date (inbound_date),
    INDEX idx_batch_no (batch_no),
    FOREIGN KEY (material_id) REFERENCES materials(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
    FOREIGN KEY (operator_id) REFERENCES users(id),

    CONSTRAINT chk_inbound_qty CHECK (quantity > 0),
    CONSTRAINT chk_inbound_price CHECK (unit_price >= 0)
) ENGINE=InnoDB COMMENT='入库记录表';


-- ============================================================
-- 6. 领用申请表 (requisitions)
-- ============================================================
DROP TABLE IF EXISTS requisitions;
CREATE TABLE requisitions (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY   COMMENT '主键',
    req_code        VARCHAR(20)  NOT NULL UNIQUE         COMMENT '申请编号，规则：LY+年月日+4位流水号',
    applicant_id    BIGINT       NOT NULL                COMMENT '申请人ID（教师/管理员）',
    purpose         VARCHAR(300) NOT NULL                COMMENT '用途说明',
    use_date        DATE         DEFAULT NULL            COMMENT '预计使用日期',
    total_amount    DECIMAL(14,2) NOT NULL DEFAULT 0.00  COMMENT '申请总金额',
    status          ENUM('draft','pending','approved','rejected',
                         'returned','delivered','signed','returned_stock')
                                NOT NULL DEFAULT 'draft' COMMENT '状态：
                                  draft=草稿, pending=待审批, approved=已审批,
                                  rejected=已驳回, returned=退回修改,
                                  delivered=已出库, signed=已签收, returned_stock=已归还',
    approver_id     BIGINT       DEFAULT NULL            COMMENT '审批人ID',
    approval_comment VARCHAR(300) DEFAULT NULL           COMMENT '审批意见/驳回理由',
    approved_at     DATETIME     DEFAULT NULL            COMMENT '审批时间',
    deliverer_id    BIGINT       DEFAULT NULL            COMMENT '出库操作人ID',
    delivered_at    DATETIME     DEFAULT NULL            COMMENT '出库时间',
    signed_at       DATETIME     DEFAULT NULL            COMMENT '签收时间',
    remark          VARCHAR(500) DEFAULT NULL            COMMENT '备注',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_applicant (applicant_id),
    INDEX idx_approver (approver_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at),
    FOREIGN KEY (applicant_id) REFERENCES users(id),
    FOREIGN KEY (approver_id) REFERENCES users(id),
    FOREIGN KEY (deliverer_id) REFERENCES users(id)
) ENGINE=InnoDB COMMENT='领用申请表';


-- ============================================================
-- 7. 领用明细表 (requisition_items)
-- ============================================================
DROP TABLE IF EXISTS requisition_items;
CREATE TABLE requisition_items (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY   COMMENT '主键',
    item_code       VARCHAR(20)  NOT NULL UNIQUE         COMMENT '明细编号',
    requisition_id  BIGINT       NOT NULL                COMMENT '领用申请ID',
    material_id     BIGINT       NOT NULL                COMMENT '耗材ID',
    req_quantity    INT          NOT NULL                COMMENT '申请数量',
    actual_quantity INT          DEFAULT NULL            COMMENT '实际出库数量',
    return_quantity INT          DEFAULT 0               COMMENT '已归还数量',
    returned_at     DATETIME     DEFAULT NULL            COMMENT '归还时间',

    INDEX idx_requisition (requisition_id),
    INDEX idx_material (material_id),
    FOREIGN KEY (requisition_id) REFERENCES requisitions(id) ON DELETE CASCADE,
    FOREIGN KEY (material_id) REFERENCES materials(id),

    CONSTRAINT chk_req_qty CHECK (req_quantity > 0)
) ENGINE=InnoDB COMMENT='领用明细表（子表）';


-- ============================================================
-- 8. 操作日志表 (audit_logs) — 只追加，不删除
-- ============================================================
DROP TABLE IF EXISTS audit_logs;
CREATE TABLE audit_logs (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY   COMMENT '主键',
    user_id         BIGINT       DEFAULT NULL            COMMENT '操作人ID（NULL=系统操作）',
    username        VARCHAR(50)  NOT NULL                COMMENT '操作人用户名（冗余，防用户删除后丢失）',
    action_type     VARCHAR(30)  NOT NULL                COMMENT '操作类型：login/logout/inbound/outbound/apply/approve/reject/adjust/edit/delete/backup',
    action_detail   VARCHAR(1000) NOT NULL               COMMENT '操作详情描述',
    target_type     VARCHAR(50)  DEFAULT NULL            COMMENT '操作目标类型：material/requisition/supplier/user',
    target_id       BIGINT       DEFAULT NULL            COMMENT '操作目标ID',
    ip_address      VARCHAR(45)  DEFAULT NULL            COMMENT '客户端IP地址',
    created_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_user (user_id),
    INDEX idx_action_type (action_type),
    INDEX idx_created (created_at),
    INDEX idx_target (target_type, target_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='操作日志表（审计用，只追加不可删除）';


-- ============================================================
-- 触发器 (Triggers)
-- ============================================================

-- 触发器1：入库后自动更新库存
DROP TRIGGER IF EXISTS trg_inbound_after_insert;
DELIMITER //
CREATE TRIGGER trg_inbound_after_insert
    AFTER INSERT ON inbound_records
    FOR EACH ROW
BEGIN
    UPDATE materials
    SET stock_qty = stock_qty + NEW.quantity,
        unit_price = CASE WHEN NEW.unit_price > 0 THEN NEW.unit_price ELSE unit_price END,
        supplier_id = COALESCE(supplier_id, NEW.supplier_id),
        updated_at = NOW()
    WHERE id = NEW.material_id;
END//
DELIMITER ;

-- 触发器2：库存低于安全下限时自动记录日志
DROP TRIGGER IF EXISTS trg_stock_low_alert;
DELIMITER //
CREATE TRIGGER trg_stock_low_alert
    AFTER UPDATE ON materials
    FOR EACH ROW
BEGIN
    IF NEW.stock_qty < COALESCE(NEW.safety_stock_min, 0)
       AND (OLD.stock_qty >= COALESCE(OLD.safety_stock_min, 0) OR OLD.stock_qty IS NULL)
    THEN
        INSERT INTO audit_logs (user_id, username, action_type, action_detail, target_type, target_id, ip_address)
        VALUES (NULL, 'SYSTEM', 'alert',
                CONCAT('库存预警：耗材 [', NEW.name, ' ', NEW.spec, '] 当前库存 ', NEW.stock_qty,
                       NEW.unit, '，低于安全下限 ', NEW.safety_stock_min, NEW.unit),
                'material', NEW.id, '127.0.0.1');
    END IF;
END//
DELIMITER ;


-- ============================================================
-- 存储过程 (Stored Procedures)
-- ============================================================

-- 存储过程1：确认出库（事务内完成：扣库存 + 更新申请状态 + 记日志）
DROP PROCEDURE IF EXISTS sp_confirm_delivery;
DELIMITER //
CREATE PROCEDURE sp_confirm_delivery(
    IN p_req_id       BIGINT,
    IN p_deliverer_id BIGINT,
    IN p_items_json   JSON,      -- [{item_id:1, actual_qty:10}, ...] 实际出库数量
    OUT p_result      INT        -- 0=成功, -1=库存不足, -2=状态错误
)
BEGIN
    DECLARE v_status VARCHAR(20);
    DECLARE v_item_id BIGINT;
    DECLARE v_material_id BIGINT;
    DECLARE v_actual_qty INT;
    DECLARE v_current_stock INT;
    DECLARE v_done INT DEFAULT 0;
    DECLARE v_cur CURSOR FOR
        SELECT jt.item_id, jt.material_id, jt.actual_qty
        FROM JSON_TABLE(p_items_json, '$[*]' COLUMNS(
            item_id BIGINT PATH '$.item_id',
            material_id BIGINT PATH '$.material_id',
            actual_qty INT PATH '$.actual_qty'
        )) AS jt;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;

    -- 检查申请状态
    SELECT status INTO v_status FROM requisitions WHERE id = p_req_id;
    IF v_status != 'approved' THEN
        SET p_result = -2;
    ELSE
        START TRANSACTION;

        -- 逐个校验库存
        OPEN v_cur;
        check_loop: LOOP
            FETCH v_cur INTO v_item_id, v_material_id, v_actual_qty;
            IF v_done THEN LEAVE check_loop; END IF;

            SELECT stock_qty INTO v_current_stock FROM materials WHERE id = v_material_id FOR UPDATE;
            IF v_current_stock < v_actual_qty THEN
                SET p_result = -1;
                ROLLBACK;
                CLOSE v_cur;
                LEAVE check_loop;
            END IF;
        END LOOP;
        CLOSE v_cur;

        IF p_result IS NULL THEN
            -- 库存充足，执行出库
            OPEN v_cur;
            SET v_done = 0;
            update_loop: LOOP
                FETCH v_cur INTO v_item_id, v_material_id, v_actual_qty;
                IF v_done THEN LEAVE update_loop; END IF;

                UPDATE materials SET stock_qty = stock_qty - v_actual_qty, updated_at = NOW()
                WHERE id = v_material_id;

                UPDATE requisition_items SET actual_quantity = v_actual_qty
                WHERE id = v_item_id;
            END LOOP;
            CLOSE v_cur;

            -- 更新申请状态
            UPDATE requisitions
            SET status = 'delivered', deliverer_id = p_deliverer_id, delivered_at = NOW()
            WHERE id = p_req_id;

            -- 记录日志
            INSERT INTO audit_logs (user_id, username, action_type, action_detail, target_type, target_id, ip_address)
            SELECT p_deliverer_id, u.real_name, 'outbound',
                   CONCAT('确认出库：申请编号 ', r.req_code, '，操作人 ', u.real_name),
                   'requisition', p_req_id, '127.0.0.1'
            FROM requisitions r
            JOIN users u ON u.id = p_deliverer_id
            WHERE r.id = p_req_id;

            SET p_result = 0;
            COMMIT;
        END IF;
    END IF;
END//
DELIMITER ;

-- 存储过程2：红冲入库记录（负数冲正+新记录）
DROP PROCEDURE IF EXISTS sp_reverse_inbound;
DELIMITER //
CREATE PROCEDURE sp_reverse_inbound(
    IN p_original_id BIGINT,
    IN p_operator_id BIGINT,
    IN p_reason      VARCHAR(500)
)
BEGIN
    DECLARE v_material_id BIGINT;
    DECLARE v_qty INT;
    DECLARE v_code VARCHAR(20);

    SELECT material_id, quantity, inbound_code
    INTO v_material_id, v_qty, v_code
    FROM inbound_records WHERE id = p_original_id AND deleted_at IS NULL;

    -- 标记原记录为红冲
    UPDATE inbound_records SET deleted_at = NOW() WHERE id = p_original_id;

    -- 插入冲正记录（负数）
    INSERT INTO inbound_records (inbound_code, material_id, batch_no, quantity, unit_price,
        total_amount, supplier_id, purchase_date, operator_id, remark)
    SELECT CONCAT(v_code, '-R'), material_id, batch_no, -quantity, unit_price,
           -total_amount, supplier_id, purchase_date, p_operator_id,
           CONCAT('红冲：', p_reason)
    FROM inbound_records WHERE id = p_original_id;

    -- 更新库存
    UPDATE materials SET stock_qty = stock_qty - v_qty, updated_at = NOW()
    WHERE id = v_material_id;

    -- 记录日志
    INSERT INTO audit_logs (user_id, username, action_type, action_detail, target_type, target_id, ip_address)
    SELECT p_operator_id, u.real_name, 'reverse',
           CONCAT('红冲入库记录：', v_code, '，原因：', p_reason),
           'inbound', p_original_id, '127.0.0.1'
    FROM users u WHERE u.id = p_operator_id;
END//
DELIMITER ;


-- ============================================================
-- 视图 (Views)
-- ============================================================

-- 视图1：库存概览（含类别名称、供应商名称、预警状态）
DROP VIEW IF EXISTS v_stock_overview;
CREATE VIEW v_stock_overview AS
SELECT
    m.id,
    m.material_code,
    m.name,
    m.spec,
    c.name AS category_name,
    m.unit,
    m.unit_price,
    m.stock_qty,
    (m.stock_qty * m.unit_price) AS stock_value,
    m.safety_stock_min,
    m.safety_stock_max,
    m.location,
    s.name AS supplier_name,
    m.fund_source,
    CASE
        WHEN m.stock_qty < COALESCE(m.safety_stock_min, 0) THEN 'low'
        WHEN m.safety_stock_max IS NOT NULL AND m.stock_qty > m.safety_stock_max THEN 'high'
        ELSE 'normal'
    END AS alert_status,
    m.status,
    m.updated_at
FROM materials m
LEFT JOIN categories c ON c.id = m.category_id
LEFT JOIN suppliers s ON s.id = m.supplier_id;

-- 视图2：领用申请完整信息
DROP VIEW IF EXISTS v_requisition_full;
CREATE VIEW v_requisition_full AS
SELECT
    r.id,
    r.req_code,
    r.applicant_id,
    a.real_name AS applicant_name,
    r.purpose,
    r.use_date,
    r.total_amount,
    r.status,
    r.approver_id,
    ap.real_name AS approver_name,
    r.approval_comment,
    r.approved_at,
    r.deliverer_id,
    d.real_name AS deliverer_name,
    r.delivered_at,
    r.signed_at,
    r.remark,
    r.created_at,
    r.updated_at,
    COUNT(ri.id) AS item_count,
    SUM(ri.req_quantity) AS total_quantity
FROM requisitions r
LEFT JOIN users a ON a.id = r.applicant_id
LEFT JOIN users ap ON ap.id = r.approver_id
LEFT JOIN users d ON d.id = r.deliverer_id
LEFT JOIN requisition_items ri ON ri.requisition_id = r.id
GROUP BY r.id;

-- ============================================================
-- 8. 归还记录表 (return_records)
-- ============================================================
DROP TABLE IF EXISTS return_records;
CREATE TABLE return_records (
    id                  BIGINT AUTO_INCREMENT PRIMARY KEY   COMMENT '主键',
    return_code         VARCHAR(20)  NOT NULL UNIQUE         COMMENT '归还编号：GH + YYYYMMDD + 4位流水',
    requisition_id      BIGINT       NOT NULL                COMMENT '领用申请ID',
    requisition_item_id BIGINT       NOT NULL                COMMENT '领用明细ID',
    material_id         BIGINT       NOT NULL                COMMENT '耗材ID',
    return_quantity     INT          NOT NULL                COMMENT '归还数量',
    return_date         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '归还日期',
    return_condition    ENUM('good','damaged','lost') NOT NULL DEFAULT 'good' COMMENT '归还状态',
    overdue_days        INT          DEFAULT 0               COMMENT '逾期天数',
    fine_rate           DECIMAL(10,2) DEFAULT 0              COMMENT '罚金标准（元）',
    fine_amount         DECIMAL(14,2) DEFAULT 0              COMMENT '罚款金额（元）',
    fine_paid           TINYINT      DEFAULT 0               COMMENT '罚款状态：0未缴 1已缴',
    handler_id          BIGINT       NOT NULL                COMMENT '经手人ID',
    remark              VARCHAR(500) DEFAULT NULL             COMMENT '备注',
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    INDEX idx_requisition (requisition_id),
    INDEX idx_material    (material_id),
    INDEX idx_return_date (return_date),

    CONSTRAINT fk_return_req   FOREIGN KEY (requisition_id)      REFERENCES requisitions(id),
    CONSTRAINT fk_return_item  FOREIGN KEY (requisition_item_id) REFERENCES requisition_items(id),
    CONSTRAINT fk_return_mat   FOREIGN KEY (material_id)         REFERENCES materials(id),
    CONSTRAINT fk_return_user  FOREIGN KEY (handler_id)          REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='物品归还记录表';
