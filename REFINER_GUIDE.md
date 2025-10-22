# 教材精简工具使用指南

## 快速开始

### 1. 准备输入文件
将需要精简的教材文本放在 `textbook.txt` 文件中

### 2. 运行脚本
```bash
./run_refiner.sh
```

## 使用方法

### 基本用法
```bash
./run_refiner.sh
```
- 自动安装依赖
- 后台运行处理程序
- 实时显示日志输出
- 按 Ctrl+C 可以安全停止（进度会保存）

### 自定义参数
```bash
./run_refiner.sh --input mybook.txt --output result.txt
```

```bash
./run_refiner.sh --chunk-size 2000
```

```bash
./run_refiner.sh --no-resume
```

## 命令行参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input`, `-i` | 输入文件路径 | `textbook.txt` |
| `--output`, `-o` | 输出文件路径 | `refined_textbook.txt` |
| `--chunk-size`, `-c` | 每段字符数 | `1500` |
| `--no-resume` | 不使用断点续传，从头开始 | 否 |

## 输出文件说明

- **refined_textbook.txt** - 精简后的教材文本
- **refiner.log** - 详细的处理日志
- **.refiner_progress.json** - 进度文件（用于断点续传）

## 常见问题

### Q: 如何停止程序？
A: 按 `Ctrl+C`，程序会保存进度并安全退出

### Q: 如何继续上次的处理？
A: 直接再次运行脚本，会提示是否继续上次进度

### Q: 处理需要多长时间？
A: 取决于文本量，每段约2-5秒，脚本会显示预计剩余时间

### Q: 如何查看历史日志？
A: 查看 `refiner.log` 文件
```bash
cat refiner.log
# 或实时查看
tail -f refiner.log
```

### Q: API 密钥在哪里配置？
A: 在 `.env` 文件中配置 `DEEPSEEK_API_KEY`

## 示例

### 完整示例
```bash
# 1. 准备输入文件
echo "这是一段很长很长的教材内容..." > textbook.txt

# 2. 运行脚本
./run_refiner.sh

# 3. 等待处理完成，查看结果
cat refined_textbook.txt
```

### 处理大文件
```bash
# 使用更大的分段大小以减少 API 调用次数
./run_refiner.sh --chunk-size 2000
```

### 重新处理
```bash
# 不使用断点续传，从头开始
./run_refiner.sh --no-resume
```

## 内存使用

脚本采用流式处理，内存占用稳定：
- 小文件（<100页）：约 10-20 MB
- 中等文件（100-500页）：约 20-50 MB  
- 大文件（>500页）：约 50-100 MB

即使处理上千页的教材也不会出现内存问题。

## 故障排除

### 错误：未找到 .env 文件
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥
```

### 错误：API 请求失败
检查：
1. API 密钥是否正确
2. 网络连接是否正常
3. API 配额是否充足

### 程序卡住不动
1. 按 `Ctrl+C` 停止
2. 检查 `refiner.log` 查看错误信息
3. 再次运行会从上次进度继续
