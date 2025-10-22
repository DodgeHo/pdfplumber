#!/bin/bash

# 停止精简程序

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "================================================"
echo "  教材精简工具 - 停止程序"
echo "================================================"
echo ""

# 检查 PID 文件
if [ ! -f ".refiner.pid" ]; then
    echo -e "${YELLOW}未找到运行中的进程${NC}"
    exit 0
fi

PID=$(cat .refiner.pid)

# 检查进程是否存在
if ps -p $PID > /dev/null 2>&1; then
    echo -e "${YELLOW}正在停止进程 (PID: $PID)...${NC}"
    
    # 发送 SIGTERM 信号（优雅停止）
    kill $PID
    
    # 等待进程结束（最多等待 10 秒）
    for i in {1..10}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            echo -e "${GREEN}✓ 进程已停止${NC}"
            rm -f .refiner.pid
            echo ""
            echo "进度已保存，下次运行时可以继续"
            exit 0
        fi
        sleep 1
    done
    
    # 如果进程还没停止，强制结束
    echo -e "${YELLOW}进程未响应，强制结束...${NC}"
    kill -9 $PID 2>/dev/null
    rm -f .refiner.pid
    echo -e "${GREEN}✓ 进程已强制停止${NC}"
else
    echo -e "${YELLOW}进程已停止 (PID: $PID)${NC}"
    rm -f .refiner.pid
fi

echo ""
