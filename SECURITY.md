# Security Policy

## Secret Handling

- Store API credentials in environment variables such as `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`.
- Keep real secrets only in your local `.env`.
- `.env` is ignored by Git and should never be committed.
- Do not share logs, screenshots, or terminal output that may include tokens, headers, or request payloads.

## Privacy Defaults

The repository ships with privacy-friendly local defaults in `.env.example`:

- `DISABLE_TELEMETRY=1`
- `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`

Third-party telemetry is opt-in and only turns on when `CLAUDE_CODE_ENABLE_TELEMETRY=1` is explicitly set.

## Recommended Local Setup

Use a local `.env` with the minimum required configuration:

```env
ANTHROPIC_BASE_URL=https://api.example.com/anthropic
ANTHROPIC_API_KEY=sk-your-api-key
DISABLE_TELEMETRY=1
CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
```

## Reporting a Vulnerability

If you find a security issue, please avoid opening a public issue with sensitive details.

- Open a private report through GitHub Security Advisories if available.
- Otherwise contact the maintainer directly before publishing technical details.
- Include the affected file or module, a minimal reproduction, and impact scope.
