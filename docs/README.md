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
