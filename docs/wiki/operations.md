# Operations Runbook

Use this page when changing the load balancer contract, publishing images, running comparisons, or validating the GitHub Pages docs.

## Local release gate

Run from the repository root before pushing contract or docs changes:

```sh
git diff --check
make clean test
cd docs
bun install --frozen-lockfile
NODE_ENV=production bun run build
```

`make clean test` runs `docs-drift`, builds both implementations, then executes the C and ASM integration checks. The C path covers proxy and fdpass behavior. The ASM path additionally covers unsupported `LB_MODE`, invalid `UPSTREAMS`, decimal fallback parsing, and both `seqpacket`/`stream` fdpass control sockets.

## Source-backed docs drift

```sh
make docs-drift
```

The drift checker compares public docs against source and workflow truth:

- published image tag families from `.github/workflows/build.yml`;
- runtime environment knobs from `src/yolo_lb.c` and `src/yolo_lb_fdpass.S`;
- Makefile build/test targets;
- active benchmark participants from `.github/workflows/benchmark.yml`;
- Pages build knobs from `.github/workflows/pages.yml`;
- every `docs/wiki/*.md` page listed in the sidebar.

When adding a new public runtime knob, image tag, benchmark participant, Pages build input, or wiki page, update both the docs and `scripts/check_docs_drift.py` in the same change.

## Workflow map

| Workflow | Trigger | What it verifies or publishes |
| --- | --- | --- |
| `Build and publish LB images` | push/PR to `main`, manual dispatch | Runs `make clean test`, then builds linux/amd64 ASM and C images. Pushes `latest`, release tags, `asm-ci-<sha>`, Docker metadata `sha-<short-sha>`, `c-ci-<sha>`, and `c-latest` outside PRs. |
| `Deploy GitHub Pages` | docs/comparison/main workflow changes, manual dispatch | Installs docs dependencies with Bun, uses Node 22, builds with `NODE_ENV=production` and `PUBLIC_GA_ID=G-VN29JG8MTG`, uploads `docs/out`, and deploys GitHub Pages. |
| `LB Comparison Benchmark` | push to `comparison`, manual dispatch | Runs pinned comparison compose files, archives artifacts, and writes `comparison-results/latest.json` for Pages. |
| `CodeQL` | default GitHub code scanning triggers | Static analysis for the repository. |

If `actions/deploy-pages` fails after artifact upload with a transient GitHub Pages deployment error, prefer a fresh manual dispatch for the same `main` head. Rerunning only the failed deploy job can leave multiple `github-pages` artifacts in the same run and make the rerun fail before deployment starts.

## Benchmark dispatch checklist

Run real comparison benchmarks from the `comparison` branch. The copy of the workflow on `main` exists for Actions discovery and manual dispatch.

Important inputs:

- `compose_file`: use `all-comparison` for the active matrix, or a single `competitor-compose/.../docker-compose.yml` participant.
- `official_ref`: official Rinha repo ref cloned for the benchmark runner.
- `lb_c_image` and `lb_asm_image`: optional image overrides; use `c-ci-<sha>` and `asm-ci-<sha>` for repeatable evidence.
- `lb_fdpass_sndbuf`: compose-level fdpass socket buffer value used by comparison participants that honor it.
- `benchmark_repetitions`: repeat count; use more than one when chasing noisy p99 deltas.
- `benchmark_k6_mode`: `native` for runner-installed k6, `docker` for the configured k6 image.
- `benchmark_runner`: `matrix` runs participants separately, `sequential` runs all participants on the same runner and captures runner metadata.

Reject benchmark results with false positives, false negatives, HTTP errors, or readiness failures before comparing p99.

## Live smoke checklist

After a docs or workflow change reaches `main`:

1. Watch `Build and publish LB images`, `Deploy GitHub Pages`, and CodeQL for the pushed head.
2. Fetch key Pages routes and assert HTTP 200:
   - `/rinha4-lb-yolo-mode/`
   - `/rinha4-lb-yolo-mode/docs/`
   - `/rinha4-lb-yolo-mode/docs/contracts/`
   - `/rinha4-lb-yolo-mode/docs/getting-started/`
   - `/rinha4-lb-yolo-mode/docs/operations/`
   - `/rinha4-lb-yolo-mode/reports/`
3. Check that newly documented markers are present in generated/live HTML.
4. Confirm `git status --short --branch` is clean and `HEAD...origin/main` is `0 0`.

## Runtime troubleshooting quick reference

| Symptom | Likely check |
| --- | --- |
| Container exits with unsupported mode | Confirm `LB_MODE` is `proxy`, `fdpass`, `fd`, `fd-pass`, or `scm_rights`. The C baseline also accepts `MODE`, `uds-proxy`, and `unix-proxy`; the ASM image does not use `MODE`. |
| ASM exits with invalid configuration | Confirm `UPSTREAMS` has exactly two non-empty Unix socket paths, each shorter than the Linux `sun_path` limit. |
| fdpass backend receives no request | Match `LB_FDPASS_SOCKET_TYPE` with the backend control socket type and make sure both control sockets exist before the LB starts. |
| fdpass backend sees immediate EOF/EAGAIN-like behavior | The LB intentionally passes blocking accepted client FDs. Recheck backend socket handling before changing LB accept flags. |
| Proxy mode returns intermittently | Confirm both Unix stream HTTP upstreams are mounted at the documented paths and can accept raw HTTP over UDS. |
