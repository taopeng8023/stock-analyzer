# 🧠 记忆增强系统 - 快速启动

三大功能已就绪！

---

## ✅ 已安装功能

| 功能 | 状态 | 说明 |
|------|------|------|
| 1️⃣ 自动归档 | 🟢 就绪 | 会话结束自动保存摘要 |
| 2️⃣ 关键词触发 | 🟢 就绪 | 说"记住"自动存档 |
| 3️⃣ 定期整理 | 🟢 就绪 | 每周日自动整理 |

---

## 🚀 立即使用

### 在对话中直接说：

**普通记忆**：
```
凯文，记住：明天 10 点开会
```

**重要记忆**（自动保存到长期记忆）：
```
重要：我持仓 002709 成本 45 元
```

**查看记忆**：
```
凯文，你记得我什么？
```

---

## 📁 文件位置

```
/home/admin/.openclaw/workspace/
├── MEMORY.md                    # 长期记忆
├── memory/
│   └── 2026-03-30.md           # 今日记忆
└── skills/memory-enhancer/
    ├── memory_enhancer.py       # 核心脚本
    ├── SKILL.md                 # 技能文档
    └── README.md                # 本文件
```

---

## ⚙️ 自动化配置（可选）

### 添加周度整理定时任务

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每周日凌晨 2 点执行）
0 2 * * 0 cd /home/admin/.openclaw/workspace/skills/memory-enhancer && python3 memory_enhancer.py --weekly
```

---

## 📋 测试命令

```bash
cd /home/admin/.openclaw/workspace/skills/memory-enhancer

# 查看记忆状态
python3 memory_enhancer.py --status

# 测试关键词触发
python3 memory_enhancer.py "记住：测试内容"

# 测试重要记忆
python3 memory_enhancer.py "重要：测试重要信息"

# 手动执行周度整理
python3 memory_enhancer.py --weekly
```

---

## 💡 使用技巧

### 1. 记忆分级

| 你说 | 保存到 | 有效期 |
|------|--------|--------|
| "记住：..." | `memory/今日.md` | 永久 |
| "重要：..." | `MEMORY.md` | 永久 |
| "别忘了：..." | `memory/今日.md` | 永久 |

### 2. 自动归档

对话结束时说：
- "今天先到这"
- "明天继续"
- "再见"

我会自动保存本次会话摘要

### 3. 定期整理

每周日凌晨 2 点自动执行（需配置 cron）
- 提取本周重要信息
- 合并到 `MEMORY.md`
- 去重过滤

---

## 🔍 查看记忆

### 今日记忆
```bash
cat /home/admin/.openclaw/workspace/memory/$(date +%Y-%m-%d).md
```

### 长期记忆
```bash
cat /home/admin/.openclaw/workspace/MEMORY.md
```

### 记忆状态
```bash
python3 memory_enhancer.py --status
```

---

## 📝 示例对话

**用户**：凯文，记住我持仓 002709，成本 45 元，止损 -15%

**凯文**：✅ 已保存到今日记忆

---

**用户**：重要：我的投资风格是稳健型，偏好短线操作

**凯文**：✅ 已保存到长期记忆（下次会话也会记得）

---

**用户**：今天先到这

**凯文**：📦 已自动归档本次会话摘要

---

## ⚠️ 注意事项

1. **隐私**：不要保存密码、身份证号等敏感信息
2. **去重**：相同内容自动检测不重复保存
3. **主会话**：`MEMORY.md` 仅在私聊中加载
4. **清理**：定期手动清理 `memory/` 目录的旧文件

---

## 🐛 故障排除

### 记忆没有保存？

```bash
# 检查文件权限
ls -la /home/admin/.openclaw/workspace/memory/

# 检查磁盘空间
df -h

# 测试脚本
python3 memory_enhancer.py "记住：测试"
```

### 周度整理不执行？

```bash
# 检查是否是周日
date +%A  # 应显示 Sunday

# 手动测试
python3 memory_enhancer.py --weekly
```

---

## 📞 需要帮助？

```bash
# 查看完整文档
cat SKILL.md

# 查看脚本帮助
python3 memory_enhancer.py
```

---

**版本**: 1.0  
**创建日期**: 2026-03-30  
**状态**: ✅ 已安装并测试通过
