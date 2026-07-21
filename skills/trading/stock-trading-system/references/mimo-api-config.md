# 小米mimo API配置（替代DeepSeek）

## 特殊处理

### 1. reasoning模型识别
mimo模型名称是 `mimo-v2.5-pro`，不包含 `"reasoner"`。

如果代码中有类似判断：
```python
if "reasoner" in model_name.lower():
```
必须同时加入 `"mimo"`：
```python
if ("reasoner" in model_name.lower() or "mimo" in model_name.lower()):
```

### 2. reasoning_content字段
mimo返回的响应中，`content` 可能为空，推理过程在 `reasoning_content` 字段中。

```python
# 必须检查两个字段
if hasattr(message, 'reasoning_content') and message.reasoning_content:
    result += message.reasoning_content
if message.content:
    result += message.content
```

### 3. max_tokens
mimo reasoning模型需要更大的max_tokens（建议8000），否则推理过程会截断，content为空。

## API配置

```env
DEEPSEEK_API_KEY=<从 ~/.hermes/profiles/eastmoney-bot/.env 读取>
DEEPSEEK_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
DEFAULT_MODEL_NAME=mimo-v2.5-pro
```

## 测试命令

```bash
curl -s https://token-plan-cn.xiaomimimo.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <API_KEY>" \
  -d '{
    "model": "mimo-v2.5-pro",
    "messages": [{"role": "user", "content": "你好"}],
    "max_tokens": 100
  }'
```

正常响应应包含 `reasoning_content` 字段。
