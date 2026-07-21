# GitHub 认证配置

## 问题
GitHub 从 2021 年 8 月起不再支持密码认证，必须使用 Personal Access Token (PAT) 或 SSH Key。

## 方法1: HTTPS + Token（推荐）

### 生成 Token
1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 勾选 `repo` 权限
4. 复制生成的 token（格式：`ghp_xxxxxxxxxxxx`）

### 配置 Remote URL
```bash
# 设置 remote URL（包含 token）
git remote set-url origin https://<username>:<token>@github.com/<username>/<repo>.git

# 示例
git remote set-url origin https://bwadasd123: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@github.com/bwadasd123/stock-trading-plan.git
```

### 验证
```bash
git push --dry-run
```

## 方法2: SSH Key

### 生成 SSH Key
```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 添加到 GitHub
1. 复制公钥：`cat ~/.ssh/id_ed25519.pub`
2. 访问 https://github.com/settings/ssh/new
3. 粘贴公钥

### 修改 Remote URL
```bash
git remote set-url origin git@github.com:<username>/<repo>.git
```

### 添加 GitHub Host Key
```bash
ssh-keyscan github.com >> ~/.ssh/known_hosts
```

## ⚠️ Token 过期问题
Token 可能会过期或被撤销。如果推送失败报 `Invalid username or token`，需要：
1. 生成新 token
2. 更新 remote URL

### 快速恢复技巧
如果用户没时间生成新token，可以检查**其他仓库**是否还有有效的token：
```bash
# 检查其他仓库的remote URL，看是否有可用token
cd /home/jmy/stock-screener && git config --get remote.origin.url
# 输出: https://bwadasd123:<token>@github.com/bwadasd123/stock-screener.git

# 用同一个token更新当前仓库
cd /home/jmy/stock-trading-plan
git remote set-url origin https://bwadasd123:<token_from_other_repo>@github.com/bwadasd123/stock-trading-plan.git
```
**注意**：token是绑定用户的，同一用户的所有仓库可以用同一个token。

## ⚠️ 多仓库同步
如果有多个仓库（如 stock-screener 和 stock-trading-plan），需要同步更新 token：
```bash
# 更新 stock-screener
cd /home/jmy/stock-screener
git remote set-url origin https://bwadasd123:<new_token>@github.com/bwadasd123/stock-screener.git

# 更新 stock-trading-plan
cd /home/jmy/stock-trading-plan
git remote set-url origin https://bwadasd123:<new_token>@github.com/bwadasd123/stock-trading-plan.git
```

## 当前仓库
- stock-screener: https://github.com/bwadasd123/stock-screener
- stock-trading-plan: https://github.com/bwadasd123/stock-trading-plan

## 诊断命令
```bash
# 检查当前 remote URL
git remote -v

# 检查认证状态
gh auth status  # 如果安装了 gh CLI

# 测试推送
git push --dry-run
```
