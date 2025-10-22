#!/bin/bash

# 教材精简工具自动运行脚本
# 功能：安装依赖 -> 后台运行 -> 实时显示日志

set -e  # 遇到错误立即退出

echo "================================================"
echo "  教材精简工具 (Textbook Refiner) 启动脚本"
echo "================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}[1/5] 检查 Python 环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 Python3，请先安装 Python3${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ 找到 Python: $PYTHON_VERSION${NC}"
echo ""

echo -e "${BLUE}[2/5] 检查虚拟环境...${NC}"
if [ ! -d "pdfplumber_env" ]; then
    echo -e "${YELLOW}未找到虚拟环境，正在创建...${NC}"
    python3 -m venv pdfplumber_env
    echo -e "${GREEN}✓ 虚拟环境创建成功${NC}"
else
    echo -e "${GREEN}✓ 虚拟环境已存在${NC}"
fi
echo ""

echo -e "${BLUE}[3/5] 激活虚拟环境并安装依赖...${NC}"
source pdfplumber_env/bin/activate

# 升级 pip
echo "  → 升级 pip..."
pip install --upgrade pip -q

# 安装必需的包
echo "  → 安装 requests..."
pip install requests -q

echo "  → 安装 python-dotenv..."
pip install python-dotenv -q

echo -e "${GREEN}✓ 所有依赖安装完成${NC}"
echo ""

echo -e "${BLUE}[4/5] 检查必需文件...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}错误: 未找到 .env 文件${NC}"
    echo -e "${YELLOW}提示: 请复制 .env.example 为 .env 并填入你的 API 密钥${NC}"
    exit 1
fi
echo -e "${GREEN}✓ .env 文件存在${NC}"

if [ ! -f "textbook.txt" ]; then
    echo -e "${YELLOW}警告: 未找到 textbook.txt 文件${NC}"
    echo -e "${YELLOW}提示: 请确保输入文件存在或使用 --input 参数指定${NC}"
fi
echo ""

echo -e "${BLUE}[5/5] 启动精简程序...${NC}"
echo -e "${GREEN}程序将在后台运行，日志会实时显示${NC}"
echo -e "${YELLOW}按 Ctrl+C 可以安全停止程序（进度会保存）${NC}"
echo "================================================"
echo ""

# 后台运行并实时显示日志
nohup python3 refiner_v2.py "$@" > /dev/null 2>&1 &
PID=$!

echo -e "${GREEN}✓ 程序已启动 (PID: $PID)${NC}"
echo -e "${BLUE}实时日志输出:${NC}"
echo "================================================"
echo ""

# 实时显示日志
tail -f refiner.log &
TAIL_PID=$!

# 等待主进程结束
wait $PID
EXIT_CODE=$?

# 停止 tail
kill $TAIL_PID 2>/dev/null

echo ""
echo "================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ 程序执行完成！${NC}"
else
    echo -e "${RED}✗ 程序异常退出 (退出码: $EXIT_CODE)${NC}"
fi
echo "================================================"

exit $EXIT_CODE
