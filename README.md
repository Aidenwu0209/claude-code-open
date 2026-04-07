# Claude Code Open

<p align="center">
  <strong>一个可本地运行、可继续开发、带完整工程结构与文档资源的 Claude Code 工作区。</strong>
</p>

<p align="center">
  <a href="./README.en.md">English</a> ·
  <a href="./docs/fusion-notes.md">融合说明</a> ·
  <a href="./docs/introduction/architecture-overview.mdx">架构概览</a>
</p>

<p align="center">
  <img src="./docs/fusion-assets/readme-hero.png" alt="Claude Code Open Hero" width="100%" />
</p>

## 项目定位

这个仓库把“可直接本地运行的入口”和“完整工程结构”放在了一起：

- 保留 `src/`、`packages/`、`scripts/`、`docs/` 等完整目录
- 保留本地启动脚本、恢复模式和环境模板
- 保留终端交互、命令系统、工具系统、MCP、插件与 Skills 能力
- 保留架构文档、截图和仓库门面资源，便于继续维护公开页面

## 主要能力

- 完整 CLI / Ink TUI 交互界面
- `--print` 非交互输出模式
- 本地启动脚本 `./bin/claude-local`
- Recovery CLI 降级模式
- 自定义 API 端点与模型配置
- MCP / 插件 / Skills / 命令系统

## 界面预览

<p align="center">
  <img src="./docs/fusion-assets/readme-preview.png" alt="Preview Wall" width="100%" />
</p>

完整运行截图保留在 [`docs/runtime-snapshots/`](./docs/runtime-snapshots/) 目录中，`docs/fusion-assets/` 同时保留 README 展示图和 SVG 源文件。

## 快速开始

### 1. 安装 Bun

```bash
curl -fsSL https://bun.sh/install | bash
bun --version
```

### 2. 安装依赖

```bash
bun install
```

### 3. 配置环境变量

```bash
cp .env.example .env
```

推荐本地配置：

```env
ANTHROPIC_BASE_URL=https://api.example.com/anthropic
ANTHROPIC_API_KEY=sk-your-api-key
ANTHROPIC_AUTH_TOKEN=
ANTHROPIC_MODEL=your-default-model
ANTHROPIC_DEFAULT_SONNET_MODEL=your-default-model
ANTHROPIC_DEFAULT_HAIKU_MODEL=your-default-model
API_TIMEOUT_MS=3000000
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
DISABLE_TELEMETRY=1
```

## API 与隐私

当前仓库在 API 和隐私处理上，默认做法基本是安全的：

- API 凭证通过环境变量读取，例如 `ANTHROPIC_API_KEY` 和 `ANTHROPIC_AUTH_TOKEN`，没有写死在源码里。
- `.env` 已经被 `.gitignore` 忽略，本地密钥不会被设计成直接提交到仓库。
- `.env.example` 默认包含 `DISABLE_TELEMETRY=1` 和 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`。
- 第三方 telemetry 不是默认开启，只有显式设置 `CLAUDE_CODE_ENABLE_TELEMETRY=1` 才会启用。
- `src/utils/privacyLevel.ts` 负责隐私级别判断，会限制 telemetry 和非必要流量。
- `src/utils/auth.ts` 与 `src/localRecoveryCli.ts` 会从环境变量读取凭证，并在缺失时直接报错，而不是静默降级。

建议保持下面这些做法：

- 真实密钥只放在本地 `.env`
- 不要提交 `.env`、日志、截图或包含 token 的终端输出
- 除非你明确需要，否则保留 `DISABLE_TELEMETRY=1` 和 `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`
- 需要接入代理或兼容服务时，优先改 `ANTHROPIC_BASE_URL`，不要改源码

## 使用方式

完整 TUI：

```bash
bun run dev
```

默认 CLI 入口：

```bash
bun run start
```

本地附加入口：

```bash
./bin/claude-local
```

单次输出模式：

```bash
./bin/claude-local -p "explain this repository"
```

恢复模式：

```bash
CLAUDE_CODE_FORCE_RECOVERY_CLI=1 ./bin/claude-local
```

## 常用命令

```bash
bun run dev
bun run start
bun run build
bun run health
./bin/claude-local --help
CLAUDE_CODE_FORCE_RECOVERY_CLI=1 ./bin/claude-local --help
```

## 目录结构

```text
bin/                    # 本地启动入口
docs/                   # 文档、架构说明、图片资源
docs/fusion-assets/     # 首页图片与 SVG 源文件
docs/runtime-snapshots/ # 运行截图
packages/               # workspace 内部包
scripts/                # 构建与维护脚本
src/                    # 主代码区
preload.ts              # 本地启动预加载
```

## 推荐阅读

- [docs/fusion-notes.md](./docs/fusion-notes.md)
- [docs/introduction/architecture-overview.mdx](./docs/introduction/architecture-overview.mdx)
- [docs/conversation/the-loop.mdx](./docs/conversation/the-loop.mdx)
- [docs/tools/what-are-tools.mdx](./docs/tools/what-are-tools.mdx)
- [docs/safety/permission-model.mdx](./docs/safety/permission-model.mdx)
