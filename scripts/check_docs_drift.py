#!/usr/bin/env python3
"""Source-backed drift checks for README/wiki facts.

This is intentionally small and repo-specific: it asserts that the public docs keep
tracking the current image-tag contract, runtime env knobs, test targets, Pages
inputs, and wiki navigation model.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def fail(message: str) -> None:
    print(f"docs drift: {message}", file=sys.stderr)
    sys.exit(1)


def require(text: str, needle: str, where: str) -> None:
    if needle not in text:
        fail(f"missing {needle!r} in {where}")


def forbid(text: str, needle: str, where: str) -> None:
    if needle in text:
        fail(f"stale {needle!r} remains in {where}")


def main() -> None:
    readme = read("README.md")
    home = read("docs/wiki/home.md")
    contracts = read("docs/wiki/contracts.md")
    getting_started = read("docs/wiki/getting-started.md")
    performance = read("docs/wiki/performance.md")
    comparison = read("docs/wiki/comparison.md")
    docs_readme = read("docs/README.md")
    build_workflow = read(".github/workflows/build.yml")
    benchmark_workflow = read(".github/workflows/benchmark.yml")
    pages_workflow = read(".github/workflows/pages.yml")
    makefile = read("Makefile")
    c_source = read("src/yolo_lb.c")
    asm_source = read("src/yolo_lb_fdpass.S")
    sidebar = read("docs/src/config/sidebar.config.ts")

    # Image contract from build workflow.
    for tag in ["asm-ci-${{ github.sha }}", "c-ci-${{ github.sha }}", "c-latest", "${{ steps.semver.outputs.version }}"]:
        require(build_workflow, tag, ".github/workflows/build.yml")
    require(benchmark_workflow, "lb_c_image", ".github/workflows/benchmark.yml")
    require(benchmark_workflow, "lb_asm_image", ".github/workflows/benchmark.yml")
    forbid(benchmark_workflow, ":ci-${{ inputs.lb_sha || github.sha }}", ".github/workflows/benchmark.yml")
    for doc_name, text in {
        "README.md": readme,
        "docs/wiki/home.md": home,
        "docs/wiki/contracts.md": contracts,
        "docs/wiki/getting-started.md": getting_started,
        "docs/wiki/performance.md": performance,
        "docs/wiki/comparison.md": comparison,
    }.items():
        require(text, "asm-ci-<sha>", doc_name)
        require(text, "c-ci-<sha>", doc_name)

    # Runtime/env contract from C + ASM entrypoints.
    for source_name, source in {"src/yolo_lb.c": c_source, "src/yolo_lb_fdpass.S": asm_source}.items():
        for env in ["LB_MODE", "PORT", "BACKLOG", "UPSTREAMS", "LB_FDPASS_SOCKET_TYPE"]:
            require(source, env, source_name)
    require(c_source, "env_or(\"LB_MODE\", env_or(\"MODE\", \"proxy\"))", "src/yolo_lb.c")
    require(c_source, "streq_ci(mode, \"unix-proxy\")", "src/yolo_lb.c")
    require(asm_source, "mode_scm: .asciz \"scm_rights\"", "src/yolo_lb_fdpass.S")
    require(contracts, "MODE", "docs/wiki/contracts.md")
    require(contracts, "unix-proxy", "docs/wiki/contracts.md")
    require(contracts, "scm_rights", "docs/wiki/contracts.md")

    # Build/test targets from Makefile.
    for target in ["test-c", "test-asm", "make c", "make asm", "make clean test"]:
        if target.startswith("test-"):
            require(makefile, target, "Makefile")
        else:
            require(readme + getting_started, target, "README/getting-started docs")
    require(makefile, "docs-drift", "Makefile")
    for doc_name, text in {
        "README.md": readme,
        "docs/wiki/getting-started.md": getting_started,
        "docs/README.md": docs_readme,
    }.items():
        require(text, "make docs-drift", doc_name)

    # Container/runtime implementation facts that are easy to omit from user docs.
    dockerfile = read("Dockerfile")
    require(dockerfile, "ARG LB_IMPL=asm", "Dockerfile")
    require(dockerfile, "USER rinha", "Dockerfile")
    require(dockerfile, "EXPOSE 9999", "Dockerfile")
    for doc_name, text in {
        "README.md": readme,
        "docs/wiki/contracts.md": contracts,
        "docs/wiki/getting-started.md": getting_started,
    }.items():
        require(text, "linux/amd64", doc_name)
        require(text, "rinha", doc_name)
    require(readme + contracts, "65535", "README/contracts docs")
    require(asm_source, "cmp edx, 6553", "src/yolo_lb_fdpass.S")
    require(asm_source, "cmp edx, 107", "src/yolo_lb_fdpass.S")

    # Active comparison-branch participants from the workflow must appear in comparison docs.
    participants = re.findall(r"^\s*-?\s*name: ([a-z0-9-]+)$", benchmark_workflow, re.MULTILINE)
    if not participants:
        fail("could not parse benchmark workflow participants")
    for participant in participants:
        require(comparison, f"`{participant}`", "docs/wiki/comparison.md")

    # Pages docs should track production build knobs.
    for needle in ["node-version: '22'", "PUBLIC_GA_ID: G-VN29JG8MTG", "path: docs/out"]:
        require(pages_workflow, needle, ".github/workflows/pages.yml")
    for needle in ["Node 22", "PUBLIC_GA_ID=G-VN29JG8MTG", "docs/out"]:
        require(docs_readme, needle, "docs/README.md")

    # Every sidebar wiki slug must have a page and every page should be listed.
    listed: list[str] = []
    for ids_expr in re.findall(r"ids:\s*\[([^\]]*)\]", sidebar):
        listed.extend(re.findall(r"'([^']+)'", ids_expr))
    wiki_slugs = sorted(p.stem for p in (ROOT / "docs/wiki").glob("*.md"))
    missing = sorted(set(listed) - set(wiki_slugs))
    hidden = sorted(set(wiki_slugs) - set(listed))
    if missing:
        fail(f"sidebar references missing wiki pages: {missing}")
    if hidden:
        fail(f"wiki pages missing from sidebar: {hidden}")

    print("README/wiki drift checks passed")


if __name__ == "__main__":
    main()
