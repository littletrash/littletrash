#!/bin/bash
# 电子信息系耗材管理系统 — 生产部署脚本
set -e

echo "=== 耗材管理系统 - 生产部署 ==="

# 检查 .env
if [ ! -f .env ]; then
    echo "[INFO] 创建 .env 配置文件..."
    cp .env.example .env
    echo "[WARN] 请编辑 .env 文件，修改 SECRET_KEY 和数据库密码！"
fi

# 构建并启动
echo "[INFO] 构建 Docker 镜像..."
docker-compose build

echo "[INFO] 启动服务..."
docker-compose up -d

echo ""
echo "=== 部署完成 ==="
echo "  系统地址: http://localhost:8000"
echo "  API文档:  http://localhost:8000/docs"
echo "  查看日志: docker-compose logs -f app"
echo "  停止服务: docker-compose down"
echo ""
echo "  演示账号: admin / teacher01 / approver01 / sysadmin"
echo "  默认密码: 123456"
