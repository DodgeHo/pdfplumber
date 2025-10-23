# Git 权限管理说明

## 问题描述
每次 `git pull` 后需要手动 `chmod +x *.sh`，但这会导致 Git 检测到文件被修改。

## 解决方案

### ✅ 方案1：让 Git 追踪可执行权限（推荐）

Git 会记录文件的可执行权限（755）。只需一次设置并提交到仓库：

```bash
# 1. 更新所有脚本的可执行权限
git update-index --chmod=+x *.sh

# 2. 提交权限变更
git add *.sh
git commit -m "chore: 设置脚本可执行权限"

# 3. 推送到远程
git push
```

之后所有人 `git pull` 时会自动获得正确的权限，无需手动 `chmod`。

### ⚠️ 注意事项
- 只有**文件提交者**需要执行此操作一次
- 其他人 `git pull` 后会自动获得可执行权限
- Windows 系统不支持可执行权限，但不影响使用

---

### 方案2：使用 Git Hooks（自动化）

创建本地 Git Hook，每次 pull 后自动 chmod：

```bash
# 创建 post-merge hook
cat > .git/hooks/post-merge << 'EOF'
#!/bin/bash
echo "自动设置脚本权限..."
chmod +x *.sh 2>/dev/null || true
EOF

# 给 hook 添加执行权限
chmod +x .git/hooks/post-merge
```

缺点：每个开发者需要单独配置，不会随仓库分发。

---

### 方案3：在脚本中自检并修复（备用）

在每个脚本开头添加：

```bash
#!/bin/bash

# 自动修复权限（如果没有执行权限）
SCRIPT_PATH="${BASH_SOURCE[0]}"
if [ ! -x "$SCRIPT_PATH" ]; then
    chmod +x "$SCRIPT_PATH" 2>/dev/null && exec "$SCRIPT_PATH" "$@"
fi
```

缺点：需要用 `bash run_refiner.sh` 启动（不能用 `./run_refiner.sh`）。

---

## 当前状态

已为以下脚本设置可执行权限：
- ✅ `run_refiner.sh` - 一次精简工具
- ✅ `run_refiner_v3.sh` - 智能二次精简工具  
- ✅ `check_refiner.sh` - 进程状态检查
- ✅ `stop_refiner.sh` - 停止进程

提交后其他开发者 pull 时会自动获得可执行权限。

---

## 快速参考

```bash
# 检查文件权限状态
git ls-files --stage "*.sh"
# 100755 = 可执行
# 100644 = 普通文件

# 批量设置可执行权限
git update-index --chmod=+x *.sh

# 查看权限变更
git diff --cached *.sh

# 提交权限变更
git commit -m "chore: update shell script permissions"
```
