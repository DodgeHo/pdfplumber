#!/bin/bash

# 教材智能二次精简工具启动脚本
# 功能：智能评估 -> 选择性精简

set -e

echo "================================================"
echo "  智能二次精简工具 (Smart Refiner) v3.0"
echo "================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}[1/4] 检查虚拟环境...${NC}"
if [ ! -d "pdfplumber_env" ]; then
    echo -e "${RED}错误: 未找到虚拟环境 pdfplumber_env${NC}"
    echo -e "${YELLOW}请先运行 ./run_refiner.sh 创建虚拟环境${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 虚拟环境已存在${NC}"
echo ""

echo -e "${BLUE}[2/4] 激活虚拟环境...${NC}"
source pdfplumber_env/bin/activate
echo -e "${GREEN}✓ 虚拟环境已激活${NC}"
echo ""

echo -e "${BLUE}[3/4] 检查必需文件...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${RED}错误: 未找到 .env 文件${NC}"
    exit 1
fi
echo -e "${GREEN}✓ .env 文件存在${NC}"

if [ ! -f "refined_textbook.txt" ]; then
    echo -e "${YELLOW}警告: 未找到 refined_textbook.txt 文件${NC}"
    echo -e "${YELLOW}提示: 请确保输入文件存在或使用 --input 参数指定${NC}"
fi
echo ""

echo -e "${BLUE}[4/4] 启动智能精简程序...${NC}"
echo ""

# 过滤参数
DAEMON_MODE=false
PYTHON_ARGS=()
for arg in "$@"; do
    if [ "$arg" == "--daemon" ] || [ "$arg" == "-d" ]; then
        DAEMON_MODE=true
    else
        PYTHON_ARGS+=("$arg")
    fi
done

if [ "$DAEMON_MODE" == "true" ]; then
    # 守护进程模式
    echo -e "${GREEN}以守护进程模式启动（SSH 断开后继续运行）${NC}"
    echo -e "${CYAN}🤖 智能模式: AI会先评估每段是否需要精简${NC}"
    echo -e "${YELLOW}提示: 使用以下命令查看进度${NC}"
    echo "  查看日志: tail -f refiner_v3.log"
    echo "  查看评估: tail -f refiner_v3_evaluation.log"
    echo "  查看状态: ./check_refiner_v3.sh"
    echo "  停止进程: ./stop_refiner_v3.sh"
    echo "================================================"
    echo ""
    
    nohup python3 refiner_v3_smart.py "${PYTHON_ARGS[@]}" >> refiner_v3.log 2>&1 &
    PID=$!
    echo $PID > .refiner_v3.pid
    
    echo -e "${GREEN}✓ 程序已启动 (PID: $PID)${NC}"
    echo -e "${BLUE}进程 ID 已保存到 .refiner_v3.pid${NC}"
    echo ""
    echo "最近的日志输出:"
    echo "------------------------------------------------"
    sleep 2
    tail -n 20 refiner_v3.log 2>/dev/null || echo "等待日志生成..."
    echo "------------------------------------------------"
    echo ""
    echo -e "${GREEN}程序正在后台运行，可以安全关闭 SSH 连接${NC}"
    
else
    # 前台模式
    echo -e "${GREEN}以前台模式启动（实时显示日志）${NC}"
    echo -e "${CYAN}🤖 智能模式: AI会先评估每段是否需要精简${NC}"
    echo -e "${YELLOW}按 Ctrl+C 可以安全停止程序（进度会保存）${NC}"
    echo -e "${YELLOW}提示: 如需 SSH 断开后继续运行，请使用 --daemon 参数${NC}"
    echo "================================================"
    echo ""
    
    nohup python3 refiner_v3_smart.py "${PYTHON_ARGS[@]}" > /dev/null 2>&1 &
    PID=$!
    echo $PID > .refiner_v3.pid
    
    echo -e "${GREEN}✓ 程序已启动 (PID: $PID)${NC}"
    echo -e "${BLUE}实时日志输出:${NC}"
    echo "================================================"
    echo ""
    
    # 实时显示日志
    tail -f refiner_v3.log &
    TAIL_PID=$!
    
    # 捕获 Ctrl+C
    trap "echo ''; echo -e '${YELLOW}正在停止...${NC}'; kill $TAIL_PID 2>/dev/null; exit 0" INT
    
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
    
    rm -f .refiner_v3.pid
    
    exit $EXIT_CODE
fi
