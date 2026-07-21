# GitHub项目搜索与评估

## 触发条件
用户说"去GitHub上找找"、"有没有类似的开源项目"、"找个项目来用"

## 搜索策略

### 关键词组合
根据用户需求选择合适的中英文关键词：

| 需求 | 搜索关键词 |
|------|-----------|
| 量化交易 | `A股 量化`, `stock trading bot python` |
| 监控预警 | `股票 监盘 推送`, `python stock monitor alert` |
| 持仓管理 | `持仓管理 止盈止损`, `portfolio management` |
| AI分析 | `AI stock analysis`, `股票 智能分析` |

### 排序方式
- 按Stars降序（社区认可度）
- 检查最近更新时间（活跃度）

## 评估标准

| 维度 | 权重 | 判断标准 |
|------|------|----------|
| Stars | ⭐⭐⭐ | >500 = 成熟，100-500 = 活跃 |
| 最近提交 | ⭐⭐⭐ | <1个月 = 活跃，>6个月 = 可能停更 |
| 功能匹配 | ⭐⭐⭐⭐⭐ | 是否满足用户核心需求 |
| 技术栈 | ⭐⭐ | Python优先，与现有系统兼容 |
| 部署难度 | ⭐⭐⭐ | Docker优先，依赖少优先 |

## 部署流程

### 1. 克隆项目
```bash
cd /home/jmy
git clone https://github.com/<user>/<repo>.git
```

### 2. 安装依赖
```bash
cd /home/jmy/<repo>
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3. 配置API

**⚠️ 先检查现有环境是否有API配置！**
```bash
# 从Hermes配置读取
cat ~/.hermes/profiles/eastmoney-bot/config.yaml | grep -A 5 "provider\|base_url"
cat ~/.hermes/profiles/eastmoney-bot/.env | grep -i "api_key"
```

用户说"从环境里读"时，不要问用户要密钥，直接读取现有配置。

### 4. 创建.env文件
```bash
cp .env.example .env
# 编辑配置
```

### 5. 启动服务
```bash
# Streamlit项目
streamlit run app.py --server.port 8501 --server.headless true

# Flask项目
python3 app.py

# Docker项目
docker-compose up -d
```

### 6. 验证
```bash
curl -s http://localhost:<port> | head -5
```

## 常见端口分配
| 项目 | 端口 |
|------|------|
| stock-screener (Flask) | 8080 |
| aiagents-stock (Streamlit) | 8501 |

## 注意事项
- 国内环境用清华源安装依赖：`-i https://pypi.tuna.tsinghua.edu.cn/simple`
- 配置文件中的API密钥从环境变量或现有配置读取
- 启动后检查端口占用：`ss -tlnp | grep <port>`
