# 企业微信配置指南

**配置企业微信接收消息功能**

---

## 📋 配置前准备

### 需要准备的信息

在企业微信管理后台获取以下信息：

| 信息 | 说明 | 获取位置 |
|------|------|---------|
| **CorpID** | 企业 ID | 企业微信管理后台 → 我的企业 → 企业信息 |
| **AgentId** | 应用 ID | 应用管理 → 应用 → 自建应用详情 |
| **Secret** | 应用密钥 | 应用管理 → 应用 → 自建应用详情 → 可见范围 |
| **Token** | 接收消息 Token | 应用管理 → 应用 → 接收消息 → 设置 API 接收 |
| **EncodingAESKey** | 消息加密密钥 | 应用管理 → 应用 → 接收消息 → 设置 API 接收 |

---

## 🔧 配置步骤

### 步骤 1：企业微信管理后台配置

#### 1.1 创建自建应用

1. 访问：https://work.weixin.qq.com/
2. 使用管理员账号登录
3. 进入：**应用管理** → **应用** → **自建** → **创建应用**
4. 填写应用信息：
   ```
   应用名称：OpenClaw 助手
   应用图标：任选
   应用可见范围：选择你自己
   ```
5. 点击 **创建**

#### 1.2 记录关键信息

创建后，记录以下信息：
```
CorpID: wwxxxxxxxxxxxxxx
AgentId: 1000001
Secret: xxxxxxxxxxxxxxxxxxxxxxxx
```

#### 1.3 配置接收消息

1. 在应用详情页，找到 **接收消息** 部分
2. 点击 **设置 API 接收**
3. 填写配置：
   ```
   URL: http://172.25.24.92:18965/wechat
   Token: openclaw2026
   EncodingAESKey: （点击随机生成，复制保存）
   ```
4. 点击 **保存**
5. 记录 Token 和 EncodingAESKey

---

### 步骤 2：OpenClaw 配置

#### 2.1 运行配置命令

在终端中运行：
```bash
openclaw china setup
```

#### 2.2 填写配置信息

按提示填写企业微信配置：

```
请选择要配置的渠道：
  1. 企业微信
  2. 钉钉
  3. QQ
  4. 退出

选择：1

企业微信配置:
  CorpID: wwxxxxxxxxxxxxxx
  AgentId: 1000001
  Secret: xxxxxxxxxxxxxxxxxxxxxxxx
  Token: openclaw2026
  EncodingAESKey: （上面生成的 AESKey）
```

#### 2.3 保存配置

配置完成后保存，系统会提示配置成功。

---

### 步骤 3：重启网关

配置完成后重启网关：
```bash
openclaw gateway restart
```

查看网关状态：
```bash
openclaw gateway status
```

查看网关日志：
```bash
openclaw gateway logs --tail 50
```

---

### 步骤 4：测试消息

#### 4.1 发送测试消息

1. 打开企业微信
2. 找到 "OpenClaw 助手" 应用
3. 发送消息："你好"

#### 4.2 查看响应

- 如果配置成功，我应该能收到你的消息
- 并可以回复你

#### 4.3 查看日志确认

```bash
openclaw gateway logs --tail 100 --follow
```

查看是否有企业微信消息接收日志。

---

## ⚠️ 常见问题

### 问题 1：URL 验证失败

**现象：** 企业微信提示 URL 验证失败

**原因：** OpenClaw 网关未正确配置 Webhook 路径

**解决：**
1. 确认网关运行在 18965 端口
2. 检查 URL 是否正确：`http://172.25.24.92:18965/wechat`
3. 确认防火墙允许访问

### 问题 2：收不到消息

**检查：**
1. 企业微信应用可见范围是否包含你
2. URL 是否可访问
3. Token 和 AESKey 是否匹配
4. 网关是否正常运行

**调试：**
```bash
# 查看网关状态
openclaw gateway status

# 查看网关日志
openclaw gateway logs --tail 100 --follow

# 测试 URL 是否可访问
curl http://172.25.24.92:18965/wechat
```

### 问题 3：推送正常但接收不正常

**可能原因：**
- 企业微信接收配置未生效
- OpenClaw 插件未正确加载

**解决：**
```bash
# 重启网关
openclaw gateway restart

# 查看插件状态
openclaw status | grep -i wechat
```

---

## 📋 配置检查清单

配置完成后，请确认：

- [ ] 已创建自建应用
- [ ] 已记录 CorpID
- [ ] 已记录 AgentId
- [ ] 已记录 Secret
- [ ] 已配置接收消息 URL
- [ ] 已生成 Token
- [ ] 已生成 EncodingAESKey
- [ ] 已在 OpenClaw 中配置
- [ ] 已重启网关
- [ ] 已测试发送消息
- [ ] 可以接收消息

---

## 🎯 配置完成后

配置成功后，你就可以：

1. **在企业微信中直接发送消息**
   - 打开企业微信
   - 找到 "OpenClaw 助手"
   - 发送消息

2. **接收推送报告**
   - 市场分析报告
   - 消息监控报告
   - 股票分析报告

---

## 📞 需要帮助？

如果配置过程中遇到问题，请提供：
1. 错误信息截图
2. 网关日志
3. 企业微信配置截图（敏感信息打码）

---

**最后更新：2026-03-18**

**⚠️ 配置完成后请妥善保管 Secret 和 AESKey**
