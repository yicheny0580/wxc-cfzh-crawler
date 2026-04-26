# Documentation Index

This directory is the root knowledge map. It follows the harness-engineering pattern of a thin index that points to smaller sources of truth instead of duplicating the whole repository in one file.

## Maps

- [../justfile](../justfile): canonical root command harness.
- [architecture.md](architecture.md): repo structure, workspace model, and code ownership boundaries.
- [operations.md](operations.md): local commands for crawl, export, inspect, and verification.
- [quality.md](quality.md): tests, linting, docs checks, and quality expectations.
- [exec-plans/index.md](exec-plans/index.md): first-class checked-in plans for larger work.

## Source Of Truth

- [design-docs/index.md](design-docs/index.md): engineering design docs, agent workflow, project invariants, harness setup, and code unit design.
- [product-specs/index.md](product-specs/index.md): product principles and supported crawler/inspector workflows.
- [references/index.md](references/index.md): external references and target-site sample URLs.

## Domain Sources

- [../crawler/docs/index.md](../crawler/docs/index.md): crawler package map and package-local behavior notes.
- [../inspector/docs/index.md](../inspector/docs/index.md): inspector package map and package-local behavior notes.
- [../README.md](../README.md): short human-facing quick start.
- [../AGENTS.md](../AGENTS.md): short agent-facing entry point.

## Placement Rule

Root docs own durable cross-domain knowledge: invariants, product intent,
architecture, command harness behavior, quality policy, references, and
supported workflows. Child docs stay package-local: source maps, local config,
package behavior, package checks, and links back to root sources of truth.

Use [design-docs/agent-workflow.md](design-docs/agent-workflow.md) for the
canonical agent workflow: planning, implementation approval, checked-in
execution plans, validation, human review, and commit rules.

## External Reference

- OpenAI harness-engineering article: https://openai.com/index/harness-engineering/
