# Security Policy

## Security boundary

This repository is a distribution package. It contains workflow instructions, public interface names, package metadata, and the remote Iris MCP endpoint. It does not contain the MCP implementation, deployment configuration, credentials, customer data, or authorization policy.

Possession of the package does not grant access. Iris enforces identity, scopes, available tools, validation, confirmation, and mutations on the server for every request.

Distribution artifacts must be produced from repository-tracked contents. Do not package an arbitrary development checkout: local marketplace installation copies ignored working files as well as tracked files.

## Reporting a vulnerability

Report vulnerabilities privately through the repository's **Security** tab. Do not open a public issue containing credentials, customer data, certificate data, asset information, or reproducible bypass details.

Include the affected package version, the relevant file or flow, the observed impact, and minimal reproduction steps. Revoke or rotate any exposed credential before reporting it.

## Supported versions

Security fixes are applied to the latest released `1.x` version. Older package versions should be upgraded before further investigation unless the report concerns the upgrade path itself.
