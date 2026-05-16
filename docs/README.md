# Docs

Astro static site deployed to GitHub Pages for `rinha4-lb-yolo-mode`.

## Commands

Run from this directory (`docs/`):

| Command | Action |
|---|---|
| `bun install` | Install dependencies |
| `bun run dev` | Start dev server |
| `bun run build` | Build to `./out/` |
| `bun run preview` | Preview production build locally |

## Data sources

| Path | Description |
|---|---|
| `public/comparison/latest.json` | Latest LB comparison summary copied from `comparison-results/latest.json` before Pages build |
| `wiki/*.md` | Long-form docs rendered under `/docs/` |

The site mirrors the same repo layout used by the Rinha4 API repos: a home page, a markdown-backed wiki under `/docs/`, and a report page under `/reports/`.
