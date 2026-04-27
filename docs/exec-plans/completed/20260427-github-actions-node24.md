# GitHub Actions Node 24 Migration

## Goal

Remove GitHub Actions Node.js 20 deprecation warnings by updating workflow
actions to Node 24-compatible releases and moving the CI frontend runtime to
Node 24.

## Context

- Workflow files: [../../../.github/workflows/ci.yml](../../../.github/workflows/ci.yml)
  and [../../../.github/workflows/deploy.yml](../../../.github/workflows/deploy.yml).
- Stable deployment docs: [../../deployment.md](../../deployment.md).
- `git status --short` before implementation: none.
- This active plan was created as the first tracked implementation artifact
  after user approval.

## Plan

- Update deployment docs with the CI Python and Node runtime note.
- Update CI action versions and set the frontend Node runtime to 24.
- Update deploy checkout action to the current Node 24-compatible release.
- Run the root validation harness.

## Decisions

- Use `extractions/setup-just@v4` per user preference. Its delegated
  `extractions/setup-crate` v2 action declares `runs.using: node24`.
- Use exact latest stable tags for GitHub-owned setup actions and setup-uv:
  `actions/checkout@v6.0.2`, `actions/setup-python@v6.2.0`,
  `actions/setup-node@v6.4.0`, and `astral-sh/setup-uv@v8.1.0`.
- Do not add `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24`; the selected action
  versions are already Node 24-compatible.

## Validation

- Run `just check`.
- Confirm workflow YAML no longer references the warning-listed Node 20 action
  versions.
- Confirm frontend package engine constraints remain compatible with Node 24.

## Progress

- Created active plan as the first tracked implementation artifact.
- Updated deployment docs with the CI Python and Node runtime note.
- Updated CI and deploy workflow action versions for Node 24 compatibility.
- Validation passed: `just check`.
