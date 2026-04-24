# Memory Enhancer - AI 记忆增强技能

让 AI 拥有持久、智能的记忆能力。

---

## 🚀 功能特性

### 1️⃣ 自动归档
**会话结束时自动总结并保存关键信息**

触发词：
- "今天先到这"
- "下次再聊"
- "明天继续"
- "再见/拜拜"
- "结束/总结"

---

### 2️⃣ 关键词触发
**提到"记住"时自动存档**

支持关键词：
- `记住` / `记一下` / `记下来`
- `存档` / `保存这个`
- `别忘了` / `重要` / `标记`
- `remember` / `save this`

**用法示例**：
```
记住：我持仓 002709，成本 45 元
记一下：我的止损位是 -15%
重要：偏好短线操作，持仓周期 2-4 周
```

---

### 3️⃣ 定期整理
**每周自动整理记忆文件**

- **时间**：每周日凌晨 2 点
- **内容**：提取本周重要信息到 `MEMORY.md`
- **过滤**：自动识别"重要"、"成本"、"持仓"、"偏好"等关键词

---

## 📁 文件结构

```
/home/admin/.openclaw/workspace/
├── MEMORY.md              # 长期记忆（永久保存）
├── memory/
│   ├── 2026-03-30.md      # 今日记忆
│   ├── 2026-03-29.md      # 昨日记忆
│   └── ...
└── skills/memory-enhancer/
    ├── memory_enhancer.py # 核心脚本
    └── SKILL.md           # 本文档
```

---

## 🔧 使用方法

### 方法 1：对话中直接使用（推荐）

**在对话中说**：
```
凯文，记住：我持仓 002709 成本 45 元，止损 -15%
```

**AI 会自动**：
1. 检测关键词"记住"
2. 提取记忆内容
3. 保存到记忆文件
4. 回复确认

---

### 方法 2：命令行测试

```bash
cd /home/admin/.openclaw/workspace/skills/memory-enhancer

# 测试关键词触发
python3 memory_enhancer.py "记住：我持仓 002709 成本 45 元"

# 执行周度整理
python3 memory_enhancer.py --weekly

# 查看记忆状态
python3 memory_enhancer.py --status
```

---

### 方法 3：集成到对话流程

在 AI 回复前调用 `process_memory_request()`：

```python
from memory_enhancer import process_memory_request

# 处理用户消息
result = process_memory_request(user_message, conversation_history)

if result['saved']:
    print(f"✅ {result['message']}")
```

---

## 📊 记忆分级

| 级别 | 保存位置 | 有效期 | 加载条件 |
|------|---------|--------|---------|
| **普通信息** | `memory/今日.md` | 永久 | 自动加载 |
| **重要信息** | `MEMORY.md` | 永久 | 主会话加载 |
| **会话摘要** | `memory/今日.md` | 永久 | 按需加载 |
| **周度整理** | `MEMORY.md` | 永久 | 主会话加载 |

---

## 🎯 识别规则

### 重要信息自动升级

以下内容自动保存到 `MEMORY.md`（长期记忆）：

- 包含"重要"关键词
- 包含"成本"、"持仓"、"价格"
- 包含"偏好"、"喜欢"、"习惯"
- 用户明确说"这个很重要"

### 普通信息

其他信息保存到 `memory/今日.md`（短期记忆）

---

## 📋 配置选项

编辑 `memory_enhancer.py` 配置区域：

```python
# 自定义关键词
MEMORY_KEYWORDS = [
    '记住',
    '记一下',
    # 添加你的关键词...
]

# 自定义归档触发词
ARCHIVE_TRIGGER = [
    '今天先到这',
    # 添加你的触发词...
]

# 自定义周度整理时间
WEEKLY_ORGANIZE_DAY = 6  # 周日 (0=周一，6=周日)
WEEKLY_ORGANIZE_HOUR = 2  # 凌晨 2 点
```

---

## 🔍 查看记忆

### 查看今日记忆
```bash
cat /home/admin/.openclaw/workspace/memory/$(date +%Y-%m-%d).md
```

### 查看长期记忆
```bash
cat /home/admin/.openclaw/workspace/MEMORY.md
```

### 查看记忆状态
```bash
python3 memory_enhancer.py --status
```

---

## 💡 最佳实践

### ✅ 推荐做法

1. **明确说明**：
   > "记住：[具体内容]"

2. **分类信息**：
   > "重要：我的投资风格是稳健型"

3. **定期回顾**：
   > "凯文，你记得我什么？"

---

### ❌ 避免做法

1. **模糊表达**：
   > "记住这个"（没有具体内容）

2. **过度依赖**：
   每条消息都说"记住"（会产生噪音）

3. **敏感信息**：
   密码、身份证号等（不应保存）

---

## 🧪 测试示例

```bash
# 测试 1：普通记忆
python3 memory_enhancer.py "记住：明天开会"

# 测试 2：重要记忆
python3 memory_enhancer.py "重要：我持仓 002709 成本 45 元"

# 测试 3：归档触发
python3 memory_enhancer.py "今天先到这，明天继续"

# 测试 4：周度整理
python3 memory_enhancer.py --weekly

# 测试 5：查看状态
python3 memory_enhancer.py --status
```

---

## 📝 记忆文件示例

### `memory/2026-03-30.md`
```markdown
## [2026-03-30 12:06:00] 用户记忆

- 我持仓 002709，成本 45 元，止损 -15%

## [2026-03-30 12:10:00] 对话记录

- 偏好短线操作，持仓周期 2-4 周
```

### `MEMORY.md`
```markdown
## 用户记忆 (2026-03-30)

- 重要：持仓 002709，成本 45 元，止损 -15%
- 投资偏好：短线操作，持仓周期 2-4 周

## 周度整理 (2026-03-30)

- 成本 45 元
- 持仓 002709
- 止损 -15%
```

---

## 🔄 自动化建议

### 添加到 HEARTBEAT.md

```markdown
# 每日检查
- [ ] 检查是否有未归档的重要对话
- [ ] 执行周度整理（如果是周日）
```

### 添加定时任务（可选）

```bash
# 每周日凌晨 2 点执行周度整理
0 2 * * 0 cd /home/admin/.openclaw/workspace/skills/memory-enhancer && python3 memory_enhancer.py --weekly
```

---

## ⚠️ 注意事项

1. **隐私保护**：不保存敏感个人信息
2. **去重机制**：自动检测重复内容
3. **容量管理**：定期清理旧记忆文件（手动）
4. **主会话限制**：`MEMORY.md` 仅在私聊中加载

---

## 📞 故障排除

### 问题：记忆没有保存

**检查**：
1. 是否包含关键词？
2. 文件权限是否正确？
3. 磁盘空间是否充足？

```bash
# 检查权限
ls -la /home/admin/.openclaw/workspace/memory/

# 检查磁盘
df -h
```

---

## 📄 许可证

本技能遵循 OpenClaw 技能规范

---

**版本**: 1.0  
**创建日期**: 2026-03-30  
**作者**: 凯文 (AI Assistant)
