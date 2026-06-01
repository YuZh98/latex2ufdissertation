# Security policy

## Supported versions

Only the latest minor release receives security updates. The pre-1.0 series is treated as best-effort.

| Version | Supported |
|---|---|
| 0.1.x | yes |

## Reporting a vulnerability

If you find a security issue in `latex2ufdissertation`, please report it privately rather than opening a public issue. Open a [GitHub Security Advisory](https://github.com/YuZh98/latex2ufdissertation/security/advisories/new) on this repository — GitHub keeps the report private until a fix is published.

Please include:

- A clear description of the issue and its impact.
- A minimal reproduction (input file, command line, observed behavior).
- The version (`latex2ufdissertation --version`) and Python version you tested.

## Security / trusted input

This tool compiles LaTeX and clones git repos. **Only run it on dissertation sources you trust.** Compiling untrusted LaTeX can execute arbitrary code: `\directlua` (the LuaTeX built-in Lua interpreter) is always active and cannot be disabled by the host process. The tool mitigates the risk with `-no-shell-escape` (disables `\write18`), restricted file-access env vars (`openin_any=p`, `openout_any=p`, `shell_escape=f`), and a git-URL allowlist limited to GitHub and GitLab — but these controls do not prevent a malicious document from using `\directlua` to run arbitrary Lua code. Treat the input the same way you would treat an executable you are about to run.

## What counts as a vulnerability

This is a local-only CLI tool with no network calls in its default code path. The realistic security surface is narrow but non-empty:

- **Path traversal or unsafe extraction.** Zip inputs are extracted to a working directory; a crafted zip with absolute paths or `../` entries should not escape the workspace.
- **Subprocess injection.** The compile path invokes LuaLaTeX via `subprocess`. A crafted project filename or argument should not lead to shell injection.
- **Resource exhaustion.** Pathological inputs (deeply nested directories, enormous `.tex` files, zip bombs) should fail cleanly rather than wedge the host.
- **Information leakage.** JSON output should not embed system-dependent paths or other host metadata.

Bugs in formatting-rule detection are not security issues — open a regular issue for those.

## Response

You will receive an acknowledgement within 7 days. Fix timelines depend on severity; security-flagged dependency updates and confirmed exploits are same-day priority. Once a fix lands, the advisory is published with credit to the reporter unless you ask to remain anonymous.
