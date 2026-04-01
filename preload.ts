const version = process.env.CLAUDE_CODE_LOCAL_VERSION ?? '1.0.0-fusion';
const packageUrl = process.env.CLAUDE_CODE_LOCAL_PACKAGE_URL ?? 'claude-code-fusion';
const buildTime =
  process.env.CLAUDE_CODE_LOCAL_BUILD_TIME ?? new Date().toISOString();

process.env.CLAUDE_CODE_LOCAL_SKIP_REMOTE_PREFETCH ??= '1'

const existingMacro =
  typeof globalThis.MACRO === 'object' && globalThis.MACRO
    ? globalThis.MACRO
    : {}

Object.assign(globalThis, {
  MACRO: {
    FEEDBACK_CHANNEL: 'local',
    ISSUES_EXPLAINER: '',
    VERSION_CHANGELOG: '',
    VERSION: version,
    PACKAGE_URL: packageUrl,
    NATIVE_PACKAGE_URL: packageUrl,
    BUILD_TIME: buildTime,
    ...existingMacro,
  },
})

globalThis.BUILD_TARGET ??= 'external'
globalThis.BUILD_ENV ??= 'production'
globalThis.INTERFACE_TYPE ??= 'stdio'
