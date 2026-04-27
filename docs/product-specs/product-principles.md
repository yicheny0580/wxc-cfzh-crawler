# Product Principles

The product is a local-first crawler and SQLite inspector for the Wenxuecity
`财富智汇` forum. It helps a user collect forum discussions, preserve thread and
reply context, and inspect the resulting local database. A small personal
public deployment is supported as a read-only publish mode, not as a hosted
multi-user platform.

## Users

- A local operator who wants repeatable crawls and exports from a personal
  machine.
- A researcher or reader who wants to search posts and replies while preserving
  the original thread context.
- A maintainer who needs a legible system with explicit docs, commands, and
  validation loops.

## Product Priorities

- Local-first operation: data lives in local SQLite files under `data/` by
  default.
- Personal publish mode: public browser access reads SQLite data only; crawl
  writes remain explicit operator actions through SSH/CLI or the scheduler.
- Inspectability: users should be able to understand what was crawled, when it
  was crawled, and how records relate to root posts and replies.
- Thread context: replies should remain connected to root posts and parent
  replies whenever the source page exposes that relationship.
- Conservative operations: crawl controls should be explicit, progress should be
  visible, and refresh actions should not hide writes behind read-only views.
- Maintainer legibility: product behavior should be discoverable from docs,
  commands, tests, and source files inside the repo.

## UX Principles

- Prefer dense, readable inspection workflows over marketing-style presentation.
- Keep search and filters close to result lists.
- Make crawl state visible while a refresh is running or stopping.
- Preserve links back to source pages so users can verify records against the
  forum when needed.
- Show empty, loading, and failure states plainly.

## Non-Goals

- The project is not a hosted multi-user service or scalable public platform.
- The inspector is not an editor for forum content.
- The crawler is not a general Wenxuecity crawler for every forum.
- The UI should not obscure the SQLite-backed nature of the workflow.
