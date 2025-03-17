FROM python:3.10-slim

# 设置环境变量，避免Python生成.pyc文件和使用缓冲输出
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 设置工作目录
WORKDIR /app

# 升级pip并安装dependencies
RUN pip install --upgrade pip

# 安装Edge浏览器和驱动
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    wget \
    unzip \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && echo "deb [arch=amd64] https://packages.microsoft.com/repos/edge stable main" > /etc/apt/sources.list.d/microsoft-edge-dev.list \
    && apt-get update && apt-get install -y microsoft-edge-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 安装msedgedriver
RUN EDGE_VERSION=$(microsoft-edge-dev --version | awk '{print $3}') \
    && wget -q "https://msedgedriver.azureedge.net/${EDGE_VERSION}/edgedriver_linux64.zip" -O /tmp/edgedriver.zip \
    && unzip /tmp/edgedriver.zip -d /usr/local/bin/ \
    && rm /tmp/edgedriver.zip \
    && chmod +x /usr/local/bin/msedgedriver

# 复制依赖文件
COPY requirements/base.txt /app/requirements/base.txt

# 安装依赖
RUN pip install --no-cache-dir -r requirements/base.txt

# 复制项目文件
COPY . /app/

# 创建日志目录和下载图片目录，并设置权限
RUN mkdir -p /app/logs /app/downloaded_images \
    && chmod -R 755 /app/logs /app/downloaded_images

# 设置启动命令
CMD ["python", "-m", "src.q_plant_spider.main"] 