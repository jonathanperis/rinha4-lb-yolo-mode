# Docs

Astro static site deployed to GitHub Pages for `rinha4-lb-yolo-mode`.

## Commands

Run from this directory (`docs/`):

| Command | Action |
|---|---|
| `bun install --frozen-lockfile` | Install dependencies exactly from `bun.lock` |
| `bun run dev` | Start dev server |
| `NODE_ENV=production bun run build` | Build to `./out/` with the production base path |
| `bun run preview` | Preview production build locally |

## Data sources

| Path | Description |
|---|---|
| `public/comparison/latest.json` | Latest LB comparison summary copied from `comparison-results/latest.json` before Pages build when present |
| `wiki/*.md` | Long-form docs rendered under `/docs/` |
| `src/config/sidebar.config.ts` | Sidebar order; every listed wiki slug must have a matching Markdown file |

The site mirrors the same repo layout used by the Rinha4 API repos: a home page, a markdown-backed wiki under `/docs/`, and a report page under `/reports/`.

The Pages workflow uses Bun, Node 22, `NODE_ENV=production`, and `PUBLIC_GA_ID=G-VN29JG8MTG` before uploading `docs/out`.

## Drift checks

From the repository root, run:

```sh
make docs-drift
```

That script compares README/wiki facts with source and workflow truth: image tag contracts, runtime environment knobs, Makefile targets, benchmark participants, Pages build knobs, and sidebar/wiki coverage. Update the check when adding a new public contract so future docs edits fail fast instead of silently drifting.

The operations runbook lives at `wiki/operations.md`; keep it current when changing workflow behavior, benchmark dispatch inputs, deployment handling, or the live smoke checklist.
