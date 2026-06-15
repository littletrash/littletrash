FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libmariadb-dev && \
    rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    pymysql cryptography gunicorn

# 复制代码
COPY backend/ ./backend/
COPY prototype/ ./prototype/

WORKDIR /app/backend
RUN mkdir -p uploads

EXPOSE 8000

# Gunicorn + Uvicorn (生产推荐)
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
