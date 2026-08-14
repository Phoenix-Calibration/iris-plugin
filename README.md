# Iris Calibration Operator

Private distribution package for the Iris calibration operator. The repository combines one canonical operator skill with declarations for the existing remote Iris MCP service. It does not contain or deploy the MCP server.

## Package contents

- `plugin.json` and `mcp.json`: portable Agent Plugins v1 package metadata and MCP connection.
- `skills/calibration-operator/SKILL.md`: the single canonical workflow for calibration requirements, tolerances, manuals, and diagnostic evaluation.
- `.codex-plugin/plugin.json` and `skills/calibration-operator/agents/openai.yaml`: additive metadata for OpenAI clients.
- `.claude-plugin/plugin.json` and `.mcp.json`: additive metadata and connection declaration for Claude clients.
- `.agents/plugins/marketplace.json` and `.claude-plugin/marketplace.json`: private marketplace catalogs that install this same repository root.

All manifests identify the package as `iris-calibration-operator` version `1.0.0`. All MCP declarations use the logical server name `iris` and the same production endpoint.

## Security boundary

Installing or reading this package does not grant access to Iris. The client performs OAuth against the remote MCP service, and Iris remains responsible for identity, scopes, available tools, validation, confirmation, rate limits, auditing, and every mutation.

The package intentionally contains no access token, refresh token, client secret, authorization header, service credential, customer data, or MCP source code.

## Prerequisites

- Access to the private `Phoenix-Calibration/iris-plugin` repository.
- A Phoenix Calibration account authorized for Iris.
- A client that supports remote Streamable HTTP MCP and OAuth.
- Git credentials that can clone the private repository when installing through a marketplace.

Use the GitHub marketplace source shown below for distribution. A local-path marketplace install copies the complete working directory, including ignored development-only files, so local paths are reserved for controlled development checkouts.

## Install

### ChatGPT desktop app and Codex CLI

Register the private marketplace once:

```bash
codex plugin marketplace add Phoenix-Calibration/iris-plugin
```

Restart the ChatGPT desktop app, open the Plugins Directory, select **Phoenix Calibration**, and install **Iris Calibration Operator**. The equivalent CLI installation is:

```bash
codex plugin add iris-calibration-operator@phoenix-calibration
```

### Claude Code CLI and local Desktop sessions

Register the same repository and install the plugin:

```bash
claude plugin marketplace add Phoenix-Calibration/iris-plugin
claude plugin install iris-calibration-operator@phoenix-calibration
```

Claude Desktop local Code sessions share the configured marketplaces. The plugin is available from the Desktop plugin manager after the marketplace is registered.

Account-synced Chat and Cowork surfaces do not inherit a local CLI installation. For those surfaces, an administrator distributes this same package through the organization plugin catalog; no alternate skill or MCP configuration is required.

### Other Agent Plugins v1 clients

Install or clone the repository root as an Agent Plugin. A conforming client discovers:

- package metadata from `plugin.json`;
- the remote server from `mcp.json`;
- the operator workflow from `skills/calibration-operator/SKILL.md`.

## Authentication

No credentials are configured in this repository. On installation or first use, the host connects to the declared endpoint and hands control to the service's OAuth discovery and dynamic client registration flow. Effective read and write capabilities depend on the authenticated actor and granted scopes.

## Validate locally

Run package consistency and secret checks:

```bash
python3 scripts/validate_package.py
```

Validate the portable manifests and skill:

```bash
uvx --from check-jsonschema check-jsonschema \
  --schemafile https://agent-plugins.org/schemas/1.0.0/plugin.schema.json \
  plugin.json
uvx --from check-jsonschema check-jsonschema \
  --schemafile https://agent-plugins.org/schemas/1.0.0/mcp.schema.json \
  mcp.json
uvx --from skills-ref agentskills validate skills/calibration-operator
```

Validate the native Claude package and marketplace:

```bash
claude plugin validate . --strict
```

## Versioning

The package uses Semantic Versioning. Bump the version consistently in every manifest and in the skill metadata whenever the packaged workflow, connection declaration, or published metadata changes.

## License

Apache-2.0. See `LICENSE`.
