# Agency Agents for Claude

Claude-compatible plugin repo derived from the local Codex `agency-agents` pack and originally sourced from [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents).

## What This Repo Contains

- Claude plugin manifest in `.claude-plugin/plugin.json`
- Full `skills/` inventory from the Codex pack
- Supporting `assets/`, `references/`, and `scripts/` copied from the local source

This repo is intended to preserve the broad specialist roster that existed in Codex while making it portable as a Claude plugin repository.

## Scope

- Full-fidelity skill port
- 142 specialist skill folders
- Skill names preserved so invocation and browsing stay predictable
- Includes a Claude plugin subagent router in `agents/agency-agents-router.md`

## Install for Claude Code

Use the repo directly in development:

```bash
claude --plugin-dir ./agency-agents-claude
```

Then reload plugins if Claude is already open:

```bash
/reload-plugins
```

Skills will be namespaced under:

```text
/agency-agents:<skill-name>
```

Example:

```text
/agency-agents:engineering-frontend-developer
```

Plugin subagent:

```text
@agency-agents:agency-agents-router
```

## Notes

- This repo keeps the original skill content and supporting files as closely as possible.
- Codex-specific metadata was not carried forward into the active Claude manifest unless it mapped cleanly to Claude's public plugin structure.
- Extra source files such as per-skill `agents/openai.yaml` are retained for provenance/reference, but the core Claude behavior is driven by the `skills/` tree.
- A Claude-native router agent was added in the plugin root `agents/` directory so the plugin can expose an explicit specialist router through Claude's subagent system.

## Source

- Original local source: `C:\Users\gavin\.codex\plugins\cache\local-plugins\agency-agents\local`
- Upstream repository named in the original manifest: [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)

## License

MIT, consistent with the original local plugin manifest.
