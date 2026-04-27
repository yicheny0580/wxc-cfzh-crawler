# GitHub Actions Deploy Config Automation

## Goal

Make the existing manual GitHub Actions deployment more self-contained by
moving production deploy configuration into GitHub variables/secrets, generating
the VPS Compose environment during deployment, adding pinned SSH host trust, and
verifying the deployed app after `docker compose up`.

## Context

- Source of truth: [../../deployment.md](../../deployment.md) and
  [../../operations.md](../../operations.md).
- Implementation targets: [../../../.github/workflows/deploy.yml](../../../.github/workflows/deploy.yml),
  [../../../docker-compose.yml](../../../docker-compose.yml), and
  [../../../Caddyfile](../../../Caddyfile).
- Current deploy already builds a GHCR image, uploads Compose/Caddy files, and
  runs `docker compose pull/up` over SSH.
- `git status --short` before implementation: none.
- This active plan was created as the first tracked implementation artifact
  after implementation approval.

## Plan

- Update stable deployment docs with the GitHub variables/secrets contract,
  generated VPS `.env` behavior, pinned `known_hosts`, and verification steps.
- Update Compose so scheduler interval/pages are configurable through
  environment values while preserving `120` and `2` defaults.
- Refactor the deploy workflow into build/deploy jobs, read config from
  `vars.*` and SSH material from `secrets.*`, generate the VPS `.env`, run
  Compose config validation, deploy, and run local/public health checks.
- Validate workflow/Compose syntax and run the repo checks that cover the
  changed surface.

## Decisions

- Keep deployment manually triggered with `workflow_dispatch`; do not add a
  production approval gate.
- Use GitHub repository variables/secrets as the config source so no GitHub
  environment approval gate is involved.
- Keep DigitalOcean and Cloudflare resource provisioning manual.
- Keep `just ops-*` as local operator commands; do not add GitHub Actions admin
  workflows in this iteration.

## Validation

- `docker compose config` with representative deployment environment values.
- `just lint-just`
- `just lint`
- `just lint-lines`
- `just test-root`
- `just check` before handoff if feasible.

## Progress

- Created active exec-plan first: `20260427-github-actions-deploy-config.md`.
- Promoted deploy-config, pinned-host-key, scheduler override, and verification
  behavior into stable deployment/operations docs.
- Updated Compose scheduler command to use generated environment defaults.
- Refactored deploy workflow into build/deploy jobs with GitHub vars/secrets,
  generated VPS `.env`, pinned SSH trust, Compose validation, and health checks.
- Validation passed: representative `docker compose config`, `just lint-just`,
  `just lint-lines`, `just check`, and `git diff --check`.
- `actionlint` was not available in this workspace.
