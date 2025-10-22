#!/bin/bash

# 查看精简程序运行状态

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "================================================"
echo "  教材精简工具 - 状态查看"
echo "================================================"
echo ""

# 检查 PID 文件
if [ ! -f ".refiner.pid" ]; then
    echo -e "${YELLOW}未找到运行中的进程${NC}"
    echo ""
    echo "提示: 使用以下命令启动程序"
    echo "  前台模式: ./run_refiner.sh"
    echo "  后台模式: ./run_refiner.sh --daemon"
    exit 0
fi

PID=$(cat .refiner.pid)

# 检查进程是否存在
if ps -p $PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 程序正在运行${NC}"
    echo -e "${BLUE}进程 ID: $PID${NC}"
    echo ""
    
    # 显示进程信息
    echo "进程详情:"
    echo "------------------------------------------------"
    ps -p $PID -o pid,ppid,%cpu,%mem,etime,cmd
    echo "------------------------------------------------"
    echo ""
    
    # 显示进度信息
    if [ -f ".refiner_progress.json" ]; then
        echo "处理进度:"
        echo "------------------------------------------------"
        python3 -c "
import json
try:
    with open('.refiner_progress.json', 'r') as f:
        data = json.load(f)
    current = data.get('current_index', 0)
    total = data.get('total_chunks', 0)
    percent = (current / total * 100) if total > 0 else 0
    print(f'  已完成: {current}/{total} 段 ({percent:.1f}%)')
    if 'stats' in data:
        stats = data['stats']
        print(f'  成功: {stats.get(\"processed_chunks\", 0)} 段')
        print(f'  失败: {stats.get(\"failed_chunks\", 0)} 段')
        print(f'  API调用: {stats.get(\"api_calls\", 0)} 次')
except:
    print('  无法读取进度信息')
"
        echo "------------------------------------------------"
        echo ""
    fi
    
    # 显示最近日志
    echo "最近的日志 (最后 10 行):"
    echo "------------------------------------------------"
    tail -n 10 refiner.log
    echo "------------------------------------------------"
    echo ""
    
    echo "可用命令:"
    echo "  查看完整日志: tail -f refiner.log"
    echo "  停止程序: ./stop_refiner.sh"
    
else
    echo -e "${RED}✗ 进程已停止 (PID: $PID)${NC}"
    echo ""
    echo "检查日志获取更多信息:"
    echo "  tail -n 50 refiner.log"
    
    # 清理 PID 文件
    rm -f .refiner.pid
fi

echo ""
