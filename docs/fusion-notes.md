# Fusion Notes

这个仓库现在采用的是分层融合策略。

## 主原则

1. 默认开发与构建链路保持统一主 CLI 行为
2. 本地启动与恢复模式作为补充层接入
3. 不让附加层改写默认入口行为

## 当前默认行为

- `bun run dev`
- `bun run start`
- `bun run build`
- `bun run health`

这些都以当前仓库的统一工程结构为核心。

## 当前保留的本地扩展层

### 启动与本地兜底

- `bin/claude-local`
- `src/localRecoveryCli.ts`
- `preload.ts`
- `.env.example`

### 资源与展示

- `docs/runtime-snapshots/*.png`

### 运行修复

- `src/utils/modifiers.ts` 中的修饰键容错逻辑

## 为什么这样融合

主工程层的优势是：

- 工程面更完整
- 文档体系更完整
- packages / scripts / docs site 更成熟
- 构建链路更成型

本地扩展层的优势是：

- 本地启动更直接
- 恢复模式更简单
- 环境模板更容易上手
- 提供了一套有参考价值的运行截图

所以最适合的融合方式不是“双主干”，而是：

- 用统一主链路作为系统骨架
- 用本地扩展层补齐调试与恢复体验

## 当前入口划分

### 主入口

```bash
bun run dev
bun run start
```

### 本地附加入口

```bash
./bin/claude-local
CLAUDE_CODE_FORCE_RECOVERY_CLI=1 ./bin/claude-local
```

## 已验证结果

- `src/entrypoints/cli.tsx --version` 可运行
- `bun run build` 成功
- `bun run health` 成功
- `bin/claude-local --version` 可运行

## 如果继续往下融合

更推荐继续合并这些方向：

1. 继续吸收明确的运行修复
2. 保留默认命令、文档和构建体系
3. 避免把 recovery 分支塞进默认主链路

这样仓库会更稳，也更容易继续公开维护。
