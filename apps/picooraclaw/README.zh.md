<div align="center">
  <img src="assets/new_logo.png" alt="PicoOraClaw" width="512">

  <h1>PicoOraClaw: 基于 Go + Oracle AI Database 的超高效 AI 助手</h1>

  <h3>$10 硬件 · 10MB 内存 · 1秒启动 · Oracle AI 向量检索</h3>

  <p>
    <img src="https://img.shields.io/badge/Go-1.24+-00ADD8?style=flat&logo=go&logoColor=white" alt="Go">
    <img src="https://img.shields.io/badge/Arch-x86__64%2C%20ARM64%2C%20RISC--V-blue" alt="Hardware">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  </p>

 **中文** | [日本語](README.ja.md) | [English](README.md)
</div>

---

PicoOraClaw 是 [PicoClaw](https://github.com/jasperan/picooraclaw) 的分支版本，新增了 **Oracle AI Database** 作为持久化存储和语义向量检索的后端。Agent 使用数据库内置 ONNX 嵌入模型，根据语义意义记忆和回忆信息 —— 无需外部嵌入 API。

注意：中文文档与英文文档可能略有滞后，请优先查看[英文文档](README.md)。

<table align="center">
  <tr align="center">
    <td align="center" valign="top">
      <p align="center">
        <img src="assets/picoclaw_mem.gif" width="360" height="240">
        <br><sub>内存占用低于 10MB — 可在 $10 硬件上运行</sub>
      </p>
    </td>
    <td align="center" valign="top">
      <p align="center">
        <img src="assets/compare.jpg" width="400" height="240">
      </p>
    </td>
  </tr>
</table>

## 🦾 演示

### 🛠️ 标准 AI 工作流

<table align="center">
  <tr align="center">
    <th><p align="center">🧩 全栈工程</p></th>
    <th><p align="center">🧠 Oracle AI 记忆</p></th>
    <th><p align="center">🔎 网络搜索与学习</p></th>
  </tr>
  <tr>
    <td align="center"><p align="center"><img src="assets/picoclaw_code.gif" width="240" height="180"></p></td>
    <td align="center"><p align="center"><img src="assets/picoclaw_memory.gif" width="240" height="180"></p></td>
    <td align="center"><p align="center"><img src="assets/picoclaw_search.gif" width="240" height="180"></p></td>
  </tr>
  <tr>
    <td align="center">开发 · 部署 · 扩展</td>
    <td align="center">记忆 · 回忆 · 持久化</td>
    <td align="center">发现 · 洞察 · 趋势</td>
  </tr>
</table>

### ⏰ 定时任务与提醒

<p align="center">
  <img src="assets/picoclaw_scedule.gif" width="600">
</p>

设置提醒、运行定期任务、自动化工作流 —— 所有定时任务均以完整 ACID 保证持久化存储在 Oracle AI Database 中。

---

## 快速开始（5分钟）

所需环境：**Go 1.24+**、**Ollama**、**Docker**（用于 [Oracle AI Database 26ai Free](https://www.oracle.com/database/free/)）。

### 第一步：构建

```bash
git clone https://github.com/jasperan/picooraclaw.git
cd picooraclaw
make build
```

### 第二步：初始化

```bash
./build/picooraclaw onboard
```

### 第三步：启动 Ollama 并拉取模型

```bash
# 安装 Ollama: https://ollama.com/download
ollama pull qwen3:latest
```

### 第四步：配置 Ollama

编辑 `~/.picooraclaw/config.json`:

```json
{
  "agents": {
    "defaults": {
      "provider": "ollama",
      "model": "qwen3:latest",
      "max_tokens": 8192,
      "temperature": 0.7
    }
  },
  "providers": {
    "ollama": {
      "api_key": "",
      "api_base": "http://localhost:11434/v1"
    }
  }
}
```

### 第五步：开始对话

```bash
# 单次对话
./build/picooraclaw agent -m "你好！"

# 交互模式
./build/picooraclaw agent
```

无需 API Key，无需云端依赖 —— 2分钟内即可拥有可用的 AI 助手。

---

## 添加 Oracle AI 向量检索

Oracle 提供持久化存储、语义记忆（根据语义意义记忆和回忆）以及 ACID 事务保证。

运行一键安装脚本：

```bash
./scripts/setup-oracle.sh [可选: 密码]
```

该脚本自动完成：
1. 拉取并启动 Oracle AI Database 26ai Free 容器
2. 等待数据库就绪
3. 创建具有所需权限的 `picooraclaw` 数据库用户
4. 将 Oracle 连接配置写入 `~/.picooraclaw/config.json`
5. 运行 `picooraclaw setup-oracle` 初始化 Schema 并加载 ONNX 嵌入模型

### 测试语义记忆

```bash
# 存储事实
./build/picooraclaw agent -m "我最喜欢的编程语言是 Go"

# 根据语义回忆（不是关键词匹配）
./build/picooraclaw agent -m "我喜欢什么编程语言？"
```

第二条命令通过 384 维向量的余弦相似度检索存储的记忆。

### 查看 Oracle 中存储的数据

```bash
picooraclaw oracle-inspect [表名] [选项]
```

**表名:** `memories`, `sessions`, `transcripts`, `state`, `notes`, `prompts`, `config`, `meta`

```bash
# 全局概览仪表板
./build/picooraclaw oracle-inspect

# 语义搜索
./build/picooraclaw oracle-inspect memories -s "用户喜欢什么"

# 查看系统提示词
./build/picooraclaw oracle-inspect prompts IDENTITY
```

---

## Oracle 存储架构

<p align="center">
  <img src="assets/arch.jpg" alt="PicoOraClaw 架构" width="680">
</p>

```
                           ┌──────────────────────────────────────────┐
                           │         Oracle AI Database               │
                           │                                          │
  picooraclaw 二进制       │  ┌──────────────┐  ┌──────────────────┐ │
  ┌───────────────────┐    │  │ PICO_MEMORIES │  │ PICO_DAILY_NOTES │ │
  │  AgentLoop        │    │  │  + 向量索引   │  │  + 向量索引      │ │
  │  ├─ SessionStore ──────│──│──────────────┐│  └──────────────────┘ │
  │  ├─ StateStore   ──────│──│ PICO_SESSIONS││                       │
  │  ├─ MemoryStore  ──────│──│ PICO_STATE   ││  ┌──────────────────┐ │
  │  ├─ PromptStore  ──────│──│ PICO_PROMPTS ││  │ ALL_MINILM_L12_V2│ │
  │  └─ Tools:       │    │  │ PICO_META    ││  │   (ONNX 模型)    │ │
  │     ├─ remember  ──────│──└──────────────┘│  │  384维向量       │ │
  │     └─ recall    │    │   go-ora v2.9.0  │  └──────────────────┘ │
  └───────────────────┘    │   (纯 Go 驱动)  │                       │
         (纯 Go)           └──────────────────────────────────────────┘
```

| 表名 | 用途 |
|---|---|
| `PICO_MEMORIES` | 含 384 维向量嵌入的长期记忆 |
| `PICO_SESSIONS` | 各渠道的聊天历史 |
| `PICO_TRANSCRIPTS` | 完整对话审计日志 |
| `PICO_STATE` | Agent 键值状态 |
| `PICO_DAILY_NOTES` | 含向量嵌入的每日笔记 |
| `PICO_PROMPTS` | 系统提示词（IDENTITY.md, SOUL.md 等） |
| `PICO_CONFIG` | 运行时配置 |
| `PICO_META` | Schema 版本元数据 |

---

## CLI 命令参考

| 命令 | 说明 |
|---|---|
| `picooraclaw onboard` | 初始化配置和工作区 |
| `picooraclaw agent -m "..."` | 单次对话 |
| `picooraclaw agent` | 交互式聊天模式 |
| `picooraclaw gateway` | 启动含渠道的长驻服务 |
| `picooraclaw status` | 显示状态 |
| `picooraclaw setup-oracle` | 初始化 Oracle Schema + ONNX 模型 |
| `picooraclaw oracle-inspect` | 查看 Oracle 中存储的数据 |
| `picooraclaw oracle-inspect memories -s "查询"` | 对记忆进行语义搜索 |
| `picooraclaw cron list` | 列出定时任务 |
| `picooraclaw skills list` | 列出已安装技能 |

---

## 使用云端 LLM（代替 Ollama）

<details>
<summary><b>OpenRouter（访问所有模型）</b></summary>

```json
{
  "agents": {
    "defaults": {
      "provider": "openrouter",
      "model": "anthropic/claude-opus-4-5"
    }
  },
  "providers": {
    "openrouter": {
      "api_key": "sk-or-v1-xxx",
      "api_base": "https://openrouter.ai/api/v1"
    }
  }
}
```

在 [openrouter.ai/keys](https://openrouter.ai/keys) 获取 Key（每月 200K 免费 Token）。

</details>

<details>
<summary><b>智谱（Zhipu，中国用户推荐）</b></summary>

```json
{
  "agents": {
    "defaults": {
      "provider": "zhipu",
      "model": "glm-4.7"
    }
  },
  "providers": {
    "zhipu": {
      "api_key": "your-key",
      "api_base": "https://open.bigmodel.cn/api/paas/v4"
    }
  }
}
```

在 [bigmodel.cn](https://open.bigmodel.cn/usercenter/proj-mgmt/apikeys) 获取 Key。

</details>

<details>
<summary><b>所有支持的提供商</b></summary>

| 提供商 | 用途 | 获取 API Key |
|---|---|---|
| `ollama` | 本地推理（推荐） | [ollama.com](https://ollama.com) |
| `openrouter` | 访问所有模型 | [openrouter.ai](https://openrouter.ai/keys) |
| `zhipu` | 智谱/GLM 模型 | [bigmodel.cn](https://open.bigmodel.cn/usercenter/proj-mgmt/apikeys) |
| `anthropic` | Claude 模型 | [console.anthropic.com](https://console.anthropic.com) |
| `openai` | GPT 模型 | [platform.openai.com](https://platform.openai.com) |
| `gemini` | Gemini 模型 | [aistudio.google.com](https://aistudio.google.com) |
| `deepseek` | DeepSeek 模型 | [platform.deepseek.com](https://platform.deepseek.com) |
| `groq` | 高速推理 + 语音转录 | [console.groq.com](https://console.groq.com) |

</details>

---

## 聊天渠道

通过 `gateway` 命令将 PicoOraClaw 连接到 Telegram、Discord、Slack、QQ、钉钉、LINE、飞书。

<details>
<summary><b>Telegram</b>（推荐）</summary>

1. 在 Telegram 向 `@BotFather` 发送 `/newbot` → 复制 Token
2. 添加到 `~/.picooraclaw/config.json`:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allow_from": ["YOUR_USER_ID"]
    }
  }
}
```

> 在 Telegram 上向 `@userinfobot` 查询您的用户 ID。

3. 运行 `picooraclaw gateway`

</details>

<details>
<summary><b>Discord</b></summary>

1. 在 [discord.com/developers](https://discord.com/developers/applications) 创建 Bot，启用 MESSAGE CONTENT INTENT
2. 添加配置:

```json
{
  "channels": {
    "discord": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allow_from": ["YOUR_USER_ID"]
    }
  }
}
```

3. 以 `Send Messages` + `Read Message History` 权限邀请 Bot
4. 运行 `picooraclaw gateway`

</details>

<details>
<summary><b>QQ, 钉钉, LINE, 飞书, Slack</b></summary>

参考 `config/config.example.json`。所有渠道遵循相同配置模式：

```json
{
  "channels": {
    "<渠道名>": {
      "enabled": true,
      "<认证信息>": "...",
      "allow_from": []
    }
  }
}
```

配置完成后运行 `picooraclaw gateway`。

</details>

---

## Oracle on Autonomous AI Database（云端，可选）

<details>
<summary><b>ADB 无钱包 TLS 连接</b></summary>

```json
{
  "oracle": {
    "enabled": true,
    "mode": "adb",
    "dsn": "(description=(retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.us-ashburn-1.oraclecloud.com))(connect_data=(service_name=xxx_myatp_low.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))",
    "user": "picooraclaw",
    "password": "YourPass123"
  }
}
```

</details>

<details>
<summary><b>Oracle 配置参考</b></summary>

| 字段 | 环境变量 | 默认值 | 说明 |
|---|---|---|---|
| `enabled` | `PICO_ORACLE_ENABLED` | `false` | 启用 Oracle 后端 |
| `mode` | `PICO_ORACLE_MODE` | `freepdb` | `freepdb` 或 `adb` |
| `host` | `PICO_ORACLE_HOST` | `localhost` | Oracle 主机 |
| `port` | `PICO_ORACLE_PORT` | `1521` | 监听端口 |
| `service` | `PICO_ORACLE_SERVICE` | `FREEPDB1` | 服务名 |
| `user` | `PICO_ORACLE_USER` | `picooraclaw` | 数据库用户名 |
| `password` | `PICO_ORACLE_PASSWORD` | — | 数据库密码 |
| `onnxModel` | `PICO_ORACLE_ONNX_MODEL` | `ALL_MINILM_L12_V2` | 嵌入用 ONNX 模型 |
| `agentId` | `PICO_ORACLE_AGENT_ID` | `default` | 多 Agent 隔离键 |

</details>

---

## 故障排查

<details>
<summary><b>Oracle：连接拒绝 / ORA-12541</b></summary>

```bash
docker ps | grep oracle          # 容器是否在运行？
docker logs oracle-free          # 等待 "DATABASE IS READY"
ss -tlnp | grep 1521            # 端口 1521 是否在监听？
```

</details>

<details>
<summary><b>Oracle：ORA-01017 用户名/密码无效</b></summary>

```bash
docker exec -it oracle-free sqlplus sys/YourPass123@localhost:1521/FREEPDB1 as sysdba
SQL> ALTER USER picooraclaw IDENTIFIED BY NewPassword123;
```

</details>

<details>
<summary><b>Oracle：VECTOR_EMBEDDING() 返回 ORA-04063</b></summary>

ONNX 模型未加载。运行 `picooraclaw setup-oracle`。

</details>

<details>
<summary><b>Agent 回退到文件模式</b></summary>

Oracle 已启用但启动时连接失败。检查：
- Oracle 容器是否健康？（`docker ps`）
- 配置文件与 `ORACLE_PWD` 中的密码是否一致？
- 服务名应为 `FREEPDB1`（不是 `FREE` 或 `XE`）

</details>

---

## 构建目标

```bash
make build          # 为当前平台构建
make build-all      # 交叉编译: linux/{amd64,arm64,riscv64}, darwin/arm64, windows/amd64
make install        # 构建 + 安装到 ~/.local/bin
make test           # go test ./...
make fmt            # go fmt ./...
make vet            # go vet ./...
```

## Docker Compose

```bash
# 含 Oracle 的完整栈
PICO_ORACLE_PASSWORD=YourPass123 docker compose --profile oracle --profile gateway up -d

# 不含 Oracle
docker compose --profile gateway up -d

# 单次 Agent 运行
docker compose run --rm picooraclaw-agent -m "你好！"
```

## 功能列表

- 单一静态二进制文件（约 10MB 内存），支持 RISC-V/ARM64/x86_64
- Ollama、OpenRouter、Anthropic、OpenAI、Gemini、Zhipu、DeepSeek、Groq 提供商
- Oracle AI Database + AI 向量检索（384 维 ONNX 嵌入）
- 聊天渠道：Telegram、Discord、Slack、QQ、钉钉、LINE、飞书、WhatsApp
- 通过 cron 表达式定时任务
- 心跳定期任务
- 技能系统（工作区、全局、GitHub 托管）
- 工作区限制安全沙箱
- Oracle 不可用时优雅回退到文件存储