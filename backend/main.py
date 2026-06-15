"""
zachary · 耗材管理系统 — FastAPI 主入口
一键启动：python main.py
系统界面：http://localhost:8000
API 文档：http://localhost:8000/docs
"""
import os, sys
# 确保 backend 目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import engine, Base
from models import *  # noqa: 确保所有模型被注册

# ─── 创建表 ───
Base.metadata.create_all(bind=engine)

# ─── 初始化种子数据（首次运行） ───
def init_seed_data():
    """首次运行时自动创建演示数据"""
    from database import SessionLocal
    from passlib.context import CryptContext
    from datetime import datetime

    db = SessionLocal()
    try:
        # 检查是否已有数据
        if db.query(User).count() > 0:
            return

        pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

        # 用户
        users_data = [
            ("admin",      "张管理", "admin",     "13800006789", "admin@example.edu.cn",   "管"),
            ("teacher01",  "李老师", "teacher",   "13900001234", "lisi@example.edu.cn",    "李"),
            ("teacher02",  "赵老师", "teacher",   "13900005678", "zhaowu@example.edu.cn",  "赵"),
            ("teacher03",  "陈老师", "teacher",   "13600002345", "chenliu@example.edu.cn", "陈"),
            ("approver01", "王主任", "approver",   "13700004567", "wangba@example.edu.cn",  "王"),
            ("sysadmin",   "刘工",   "sysadmin",   "13500007890", "liugong@example.edu.cn", "刘"),
        ]
        users = {}
        for uname, rname, role, phone, email, av in users_data:
            u = User(username=uname, password_hash=pwd.hash("123456"), real_name=rname,
                     role=role, phone=phone, email=email, avatar_initials=av)
            db.add(u)
            db.flush()
            users[uname] = u

        # 类别
        cat_data = [(1,"电子元器件",None,1),(2,"焊接材料",None,2),(3,"连接线缆",None,3),
                    (4,"开发板配件",None,4),(5,"测试耗材",None,5),(6,"打印耗材",None,6),
                    (7,"实训工具",None,7),(8,"其他",None,99)]
        for cid, cn, pid, so in cat_data:
            db.add(Category(id=cid, name=cn, parent_id=pid, sort_order=so))
        db.flush()

        # 供应商
        sup_data = [
            ("SUP2024001","深圳华强电子科技有限公司","王经理","0755-88886666","active"),
            ("SUP2024002","南京鼎盛仪器有限公司","刘经理","025-66667777","active"),
            ("SUP2024003","合肥科仪商贸有限公司","赵经理","0551-77778888","active"),
            ("SUP2024005","广州天河电子城","陈经理","020-88889999","active"),
        ]
        suppliers = {}
        for sc, sn, cp, cph, st in sup_data:
            s = Supplier(supplier_code=sc, name=sn, contact_person=cp, contact_phone=cph, coop_status=st)
            db.add(s)
            db.flush()
            suppliers[sc] = s

        # 耗材
        mat_data = [
            ("HC2025010101","电阻 1KΩ","1/4W ±5%",1,"个",0.02,1200,500,None,"A栋302-柜1-层1",suppliers["SUP2024001"].id),
            ("HC2025010201","电容 100μF","25V 铝电解",1,"个",0.15,800,200,None,"A栋302-柜1-层1",suppliers["SUP2024001"].id),
            ("HC2025010501","STM32F103C8T6","LQFP48",1,"片",8.50,150,50,None,"A栋302-柜1-层2",suppliers["SUP2024001"].id),
            ("HC2025020001","焊锡丝 0.8mm","0.8mm/500g",2,"卷",30.00,5,20,None,"A栋302-柜1-层2",suppliers["SUP2024002"].id),
            ("HC2025030001","杜邦线 公对母","20cm/40pin",3,"根",0.30,200,500,None,"A栋302-柜2-层3",suppliers["SUP2024001"].id),
            ("HC2025030004","水晶头 RJ45","超五类",3,"个",0.50,350,100,None,"A栋302-柜2-层3",suppliers["SUP2024001"].id),
            ("HC2025040001","STM32F407开发板","V3.0",4,"块",180.00,3,15,None,"A栋302-柜3-层1",suppliers["SUP2024005"].id),
            ("HC2025040002","Arduino UNO R3","原装",4,"块",95.00,25,10,None,"A栋302-柜3-层1",suppliers["SUP2024005"].id),
            ("HC2025060001","打印纸 A4","70g/500张",6,"包",25.00,2,10,None,"B栋101-储物间",suppliers["SUP2024003"].id),
            ("HC2025070001","面包板 830孔","16.5×5.5cm",7,"块",5.00,45,10,100,"A栋302-柜2-层2",suppliers["SUP2024003"].id),
        ]
        for mc, mn, ms, cid, u, up, sq, smin, smax, loc, sid in mat_data:
            db.add(Material(material_code=mc, name=mn, spec=ms, category_id=cid, unit=u,
                           unit_price=up, stock_qty=sq, safety_stock_min=smin,
                           safety_stock_max=smax, location=loc, supplier_id=sid))

        db.commit()
        print("[OK] Seed data initialized")
        print("   Demo accounts: admin / teacher01 / approver01  (password: 123456)")
    except Exception as e:
        db.rollback()
        print(f"[WARN] Seed init failed: {e}")
    finally:
        db.close()

# 确保上传目录存在
os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads", "avatars"), exist_ok=True)

init_seed_data()

# ─── FastAPI App ───
app = FastAPI(
    title="zachary · 耗材管理系统",
    description="""
## API 接口文档

基于学院《实训耗材采购使用管理办法》开发的信息化耗材管理系统后端 API。

### 核心功能
- **认证**：JWT 登录认证，角色权限控制
- **耗材管理**：CRUD + 库存调整 + 预警
- **入库管理**：采购入库 + 库存自动更新
- **领用申请**：提交 → 审批 → 出库 → 签收 完整闭环
- **物品归还**：归还登记 + 逾期罚款 + 状态恢复 + Excel导出
- **供应商管理**：信息维护 + 供货统计
- **报表导出**：库存报表、消耗趋势、入库汇总
- **操作日志**：全程审计、不可删除

### 使用说明
1. 先调用 `/api/auth/login` 获取 Token
2. 将 Token 填入右上角 **Authorize** 按钮（格式：`Bearer <token>`）
3. 即可调用所有有权限的接口

### 演示账号
| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | 123456 | 耗材管理员（全部权限） |
| teacher01 | 123456 | 教师（只能看库存+申请） |
| approver01 | 123456 | 系部负责人（审批权限） |
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 注册路由 ───
from routers import auth_router, material_router, inbound_router
from routers import requisition_router, approval_router, supplier_router
from routers import report_router, log_router, return_router, user_router, config_router

app.include_router(auth_router.router)
app.include_router(material_router.router)
app.include_router(inbound_router.router)
app.include_router(requisition_router.router)
app.include_router(approval_router.router)
app.include_router(supplier_router.router)
app.include_router(report_router.router)
app.include_router(log_router.router)
app.include_router(return_router.router)
app.include_router(user_router.router)
app.include_router(config_router.router)


@app.get("/")
def root():
    """返回系统前端界面"""
    proto_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prototype", "index.html")
    if os.path.exists(proto_path):
        return FileResponse(proto_path, media_type="text/html")
    return {
        "app": "zachary·耗材管理系统",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "运行中",
    }


@app.get("/api/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ─── 启动入口 ───
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  Electronic Info Dept - Material Mgmt V1.0")
    print("  API Docs: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
