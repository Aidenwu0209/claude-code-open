# Claude Code Fusion

![Fusion Hero](docs/fusion-assets/hero-fusion.svg)

This repository is a unified Claude Code workspace that combines a full engineering layout, a local launcher path, and refreshed visual assets in one place.

The merge strategy is:

- keep the default dev, build, and main CLI flow on one consistent path
- keep a small optional local launcher and recovery layer for quick debugging
- replace the landing visuals with brand-new SVG assets

See [docs/fusion-notes.md](docs/fusion-notes.md) for the merge boundary.

## Included

- full `src/`, `packages/`, `scripts/`, and docs structure
- `bin/claude-local`
- `src/localRecoveryCli.ts`
- `preload.ts`
- `.env.example`
- optional local launcher path
- refreshed repository artwork

## Run

```bash
bun install
cp .env.example .env
bun run dev
```

Optional local launcher:

```bash
./bin/claude-local
```

Recovery mode:

```bash
CLAUDE_CODE_FORCE_RECOVERY_CLI=1 ./bin/claude-local
```
