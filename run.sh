#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export PATH="$HOME/.bun/bin:$PATH"

# 1) 启动代理
if ! pgrep -f "python.*proxy.py" > /dev/null 2>&1; then
    echo "🚀 启动 GLM 代理..."
    nohup python3 proxy.py > /tmp/proxy.log 2>&1 &
    sleep 2
    if curl -s http://127.0.0.1:4000/health | grep -q "ok"; then
        echo "✅ 代理已启动"
    else
        echo "❌ 代理启动失败，查看日志: cat /tmp/proxy.log"
        exit 1
    fi
else
    echo "✅ 代理已在运行"
fi

# 2) 导出环境变量
export ANTHROPIC_API_KEY=dummy
export ANTHROPIC_BASE_URL=http://127.0.0.1:4000
export ANTHROPIC_MODEL=glm-5
export ANTHROPIC_DEFAULT_SONNET_MODEL=glm-5
export ANTHROPIC_DEFAULT_HAIKU_MODEL=glm-5
export ANTHROPIC_DEFAULT_OPUS_MODEL=glm-5
export DISABLE_TELEMETRY=1
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
export ANTHROPIC_API_BASE_URL=http://127.0.0.1:4000

# 3) 启动 CLI（--bare 跳过登录，不用 --print）
echo "🚀 启动 Claude Code Open (GLM-5 via ZhiPu)..."
echo ""
exec bun run src/entrypoints/cli.tsx --bare "$@"
