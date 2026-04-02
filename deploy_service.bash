#!/bin/bash
# ================================================
# 一键部署 qf_project 开机自启动服务
# 在目标 Linux 设备上以 root 身份运行此脚本
# 用法：sudo bash deploy_service.bash
# ================================================

set -e

# ── 请根据实际情况修改以下变量 ──
SERVICE_NAME="qf_project"
SERVICE_FILE="qf_project.service"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_USER="${SUDO_USER:-$(whoami)}"      # 部署目标用户（默认为当前 sudo 用户）
DEPLOY_HOME="/home/$DEPLOY_USER"
DEPLOY_PATH="$DEPLOY_HOME/qf_project"
SYSTEMD_DIR="/etc/systemd/system"

echo "================================================"
echo " QF Project 服务部署脚本"
echo " 项目来源: $PROJECT_DIR"
echo " 部署用户: $DEPLOY_USER"
echo " 部署路径: $DEPLOY_PATH"
echo "================================================"

# 1. 将项目复制到目标路径（若当前已在目标路径则跳过）
if [ "$PROJECT_DIR" != "$DEPLOY_PATH" ]; then
    echo "[1/5] 复制项目文件到 $DEPLOY_PATH ..."
    rsync -av --exclude='.git' --exclude='__pycache__' \
        "$PROJECT_DIR/" "$DEPLOY_PATH/"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_PATH"
else
    echo "[1/5] 项目已在目标路径，跳过复制。"
fi

# 2. 赋予启动脚本可执行权限
echo "[2/5] 设置 service_start.bash 可执行权限..."
chmod +x "$DEPLOY_PATH/service_start.bash"

# 3. 将 service 文件中的路径替换为实际部署路径
echo "[3/5] 生成 systemd service 文件..."
sed \
    -e "s|/home/pi/qf_project|$DEPLOY_PATH|g" \
    -e "s|User=pi|User=$DEPLOY_USER|g" \
    -e "s|Group=pi|Group=$DEPLOY_USER|g" \
    "$PROJECT_DIR/$SERVICE_FILE" \
    > "$SYSTEMD_DIR/${SERVICE_NAME}.service"

echo "      已写入: $SYSTEMD_DIR/${SERVICE_NAME}.service"

# 4. 重新加载 systemd 并启用服务
echo "[4/5] 注册并启用服务..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# 5. 立即启动服务
echo "[5/5] 启动服务..."
systemctl start "$SERVICE_NAME"

echo ""
echo "================================================"
echo " 部署完成！"
echo ""
echo " 常用管理命令："
echo "   查看状态:  sudo systemctl status $SERVICE_NAME"
echo "   查看日志:  sudo journalctl -u $SERVICE_NAME -f"
echo "   停止服务:  sudo systemctl stop $SERVICE_NAME"
echo "   重启服务:  sudo systemctl restart $SERVICE_NAME"
echo "   取消自启:  sudo systemctl disable $SERVICE_NAME"
echo "================================================"
