#!/usr/bin/env python3
"""Repository consistency checks for AETHER.

Deliberately dependency-free (standard library only) so the workflow needs no
package installation. YAML parsing is attempted with PyYAML when the runner
already provides it and is reported as *skipped* (never silently passed) when
it is not available.

Checks performed:
  1. Required foundation files exist.
  2. Forbidden artefacts (model weights, datasets, secrets) are absent.
  3. YAML / issue-template configuration is structurally valid.
  4. CITATION.cff declares the required CFF 1.2.0 keys, with no invented values.
  5. Relative Markdown links and in-document anchors resolve.
  6. Markdown files end with a newline and contain no CRLF line endings.

Exit code is non-zero if any check fails.
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "NOTICE",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "SUPPORT.md",
    "CITATION.cff",
    "AUTHORS",
    ".gitignore",
    ".editorconfig",
    ".gitattributes",
    ".github/FUNDING.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/research_proposal.yml",
    ".github/workflows/repository-checks.yml",
    "docs/PROJECT_VISION.md",
    "docs/ROADMAP.md",
    "docs/GOVERNANCE.md",
    "docs/LICENSE_POLICY.md",
    "docs/DATA_POLICY.md",
    "docs/MODEL_CARD_TEMPLATE.md",
    "docs/SECURITY_MODEL.md",
    "docs/RESEARCH_PRINCIPLES.md",
]

# Directories and extensions that must not be committed: the project states it
# ships no weights, no datasets, and no secrets.
FORBIDDEN_DIRS = {"datasets", "dataset", "weights", "checkpoints", "models", "data"}
FORBIDDEN_EXTS = {".bin", ".safetensors", ".onnx", ".gguf", ".pt", ".pth", ".aet", ".pyc"}
FORBIDDEN_NAMES = {".env", "id_rsa", "credentials.json", "secrets.yml", "secrets.yaml"}

# Build/tooling output that is never committed content and must not be scanned.
IGNORED_DIRS = {"__pycache__", "node_modules", ".venv", "venv"}

ISSUE_TEMPLATE_FORBIDDEN_KEYS = {"assignees"}

failures: list[str] = []
warnings: list[str] = []


def rel(path: str) -> str:
    return os.path.relpath(path, ROOT).replace("\\", "/")


def fail(msg: str) -> None:
    failures.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def read(path: str) -> str:
    with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return handle.read()


# --------------------------------------------------------------------------
# 1. Required files
# --------------------------------------------------------------------------
def check_required_files() -> None:
    for path in REQUIRED_FILES:
        full = os.path.join(ROOT, path)
        if not os.path.isfile(full):
            fail(f"missing required file: {path}")
        elif os.path.getsize(full) == 0:
            fail(f"required file is empty: {path}")
    print(f"[ok] checked {len(REQUIRED_FILES)} required paths")


# --------------------------------------------------------------------------
# 2. Forbidden artefacts
# --------------------------------------------------------------------------
def check_artefacts() -> None:
    problems = 0
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS | {".git"}]
        for name in dirnames:
            if name.lower() in FORBIDDEN_DIRS:
                fail(f"forbidden directory present: {rel(os.path.join(dirpath, name))}/")
                problems += 1
        for name in filenames:
            full = os.path.join(dirpath, name)
            ext = os.path.splitext(name)[1].lower()
            if ext in FORBIDDEN_EXTS:
                fail(f"forbidden artefact: {rel(full)} (model/binary file)")
                problems += 1
            if name in FORBIDDEN_NAMES:
                fail(f"forbidden file: {rel(full)} (possible secret)")
                problems += 1
    if problems == 0:
        print("[ok] no model weights, datasets, or secret files present")


# --------------------------------------------------------------------------
# 3. YAML configuration
# --------------------------------------------------------------------------
def load_yaml(path: str):
    import yaml  # noqa: PLC0415  (import guard is intentional)

    with open(os.path.join(ROOT, path), encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def check_yaml() -> None:
    """Validate YAML syntax where a parser is available, then validate the
    documented structure of GitHub issue templates regardless."""
    if os.environ.get("ALLOW_MISSING_YAML") == "1":
        warn("YAML syntax parsing skipped (ALLOW_MISSING_YAML=1)")
        yaml_ok = False
    else:
        try:
            import yaml  # noqa: F401
        except ImportError:
            fail(
                "PyYAML is required for YAML validation but is not installed. "
                "Install it (pip install pyyaml), or set ALLOW_MISSING_YAML=1 to "
                "run without YAML syntax validation."
            )
            return
        yaml_ok = True

    yaml_files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS | {".git"}]
        for name in filenames:
            if name.endswith((".yml", ".yaml")):
                yaml_files.append(rel(os.path.join(dirpath, name)))

    if yaml_ok:
        for path in sorted(yaml_files):
            try:
                load_yaml(path)
            except Exception as exc:  # noqa: BLE001 - report any parser error
                fail(f"invalid YAML in {path}: {exc}")
        print(f"[ok] parsed {len(yaml_files)} YAML file(s)")

    # Issue templates have a documented structure; check it without a parser.
    template_dir = os.path.join(ROOT, ".github", "ISSUE_TEMPLATE")
    if not os.path.isdir(template_dir):
        fail("missing .github/ISSUE_TEMPLATE directory")
        return

    templates = sorted(f for f in os.listdir(template_dir) if f.endswith((".yml", ".yaml")))
    if not templates:
        fail("no issue templates found")

    allowed_types = {
        "markdown", "input", "textarea", "dropdown", "checkboxes", "upload",
    }

    for name in templates:
        path = f".github/ISSUE_TEMPLATE/{name}"
        text = read(path)

        for key in ("name", "description", "body"):
            if not re.search(rf"^{key}:", text, re.MULTILINE):
                fail(f"{path}: missing top-level key '{key}'")

        if not re.search(r"^title:", text, re.MULTILINE):
            warn(f"{path}: no 'title:' prefix defined")

        for key in ISSUE_TEMPLATE_FORBIDDEN_KEYS:
            if re.search(rf"^{key}:", text, re.MULTILINE):
                warn(f"{path}: '{key}' should not be set in a public template")

        if yaml_ok:
            try:
                data = load_yaml(path)
            except Exception:  # already reported above
                continue
            if not isinstance(data, dict):
                fail(f"{path}: top level is not a mapping")
                continue
            body = data.get("body")
            if not isinstance(body, list) or not body:
                fail(f"{path}: 'body' must be a non-empty list")
                continue
            ids = set()
            for index, item in enumerate(body):
                if not isinstance(item, dict):
                    fail(f"{path}: body item {index} is not a mapping")
                    continue
                item_type = item.get("type")
                if item_type not in allowed_types:
                    fail(f"{path}: body item {index} has invalid type '{item_type}'")
                if item_type != "markdown":
                    ident = item.get("id")
                    if not ident:
                        fail(f"{path}: body item {index} ({item_type}) is missing 'id'")
                    elif ident in ids:
                        fail(f"{path}: duplicate id '{ident}'")
                    else:
                        ids.add(ident)
                attrs = item.get("attributes")
                if not isinstance(attrs, dict) or "label" not in attrs:
                    if item_type != "markdown":
                        fail(f"{path}: body item {index} is missing attributes.label")
                if item_type in {"input", "textarea", "dropdown"}:
                    if not isinstance(attrs, dict) or "description" not in attrs:
                        warn(f"{path}: '{item.get('id')}' has no description")
                if item_type == "dropdown":
                    options = (attrs or {}).get("options")
                    if not isinstance(options, list) or len(options) < 2:
                        fail(f"{path}: dropdown '{item.get('id')}' needs at least 2 options")
                if item_type == "checkboxes":
                    options = (attrs or {}).get("options")
                    if not isinstance(options, list) or not options:
                        fail(f"{path}: checkboxes '{item.get('id')}' needs options")
                    else:
                        for option in options:
                            if not isinstance(option, dict) or "label" not in option:
                                fail(f"{path}: checkbox option in '{item.get('id')}' lacks a label")

    print(f"[ok] checked structure of {len(templates)} issue template(s)")


# --------------------------------------------------------------------------
# 4. CITATION.cff
# --------------------------------------------------------------------------
def check_citation() -> None:
    text = read("CITATION.cff")
    required = ["cff-version", "message", "title", "authors", "license", "type"]
    for key in required:
        if not re.search(rf"^{key}:", text, re.MULTILINE):
            fail(f"CITATION.cff: missing required key '{key}'")

    match = re.search(r"^cff-version:\s*\"?([0-9.]+)\"?", text, re.MULTILINE)
    if not match:
        fail("CITATION.cff: could not parse cff-version")
    elif match.group(1) != "1.2.0":
        fail(f"CITATION.cff: cff-version is '{match.group(1)}', expected 1.2.0")

    for key in ("doi", "version", "date-released"):
        if re.search(rf"^{key}:", text, re.MULTILINE):
            value = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE).group(1)
            warn(f"CITATION.cff: '{key}' is set ({value.strip()}); confirm it is real")

    if re.search(r"^date-released:", text, re.MULTILINE):
        if not re.search(r"^date-released:\s*\"?\d{4}-(0[1-9]|1[012])-(0[1-9]|[12]\d|3[01])\"?",
                         text, re.MULTILINE):
            fail("CITATION.cff: date-released must be YYYY-MM-DD")

    for bad in ("orcid", "given-names", "family-names"):
        if bad in text and "MAINTAINER" not in text:
            warn(f"CITATION.cff: contains '{bad}'; verify it is not invented")

    if "MAINTAINER ACTION REQUIRED" not in text:
        warn("CITATION.cff: no maintainer TODO block found; confirm omitted fields are intentional")

    print("[ok] CITATION.cff basic metadata validated (schema check is not performed offline)")


# --------------------------------------------------------------------------
# 5. Markdown links and anchors
# --------------------------------------------------------------------------
LINK_RE = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)")
FENCE_RE = re.compile(r"^```")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def slugify(heading: str) -> str:
    text = heading.strip().lower()
    text = re.sub(r"`", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)  # links -> text
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", "-", text.strip())


def anchors_of(path: str) -> set[str]:
    anchors: set[str] = set()
    in_fence = False
    for line in read(path).splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(line)
        if match:
            anchors.add(slugify(match.group(2)))
    return anchors


def markdown_files() -> list[str]:
    found = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS | {".git"}]
        for name in filenames:
            if name.endswith(".md"):
                found.append(rel(os.path.join(dirpath, name)))
    return sorted(found)


def check_markdown() -> None:
    files = markdown_files()
    anchor_cache: dict[str, set[str]] = {}
    link_count = 0
    checked_anchors = 0

    for path in files:
        text = read(path)
        full = os.path.join(ROOT, path)

        if "\r\n" in text:
            fail(f"{path}: contains CRLF line endings")
        if not text.endswith("\n"):
            fail(f"{path}: does not end with a newline")
        in_fence = False
        for lineno, line in enumerate(text.splitlines(), start=1):
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for _label, target in LINK_RE.findall(line):
                target = target.strip()
                link_count += 1
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    if target.startswith("#"):
                        anchor = target[1:]
                        if anchor not in anchors_of(path):
                            fail(f"{path}:{lineno}: broken in-page anchor '{target}'")
                        checked_anchors += 1
                    continue
                if target.startswith("<!--"):
                    continue
                file_part = target.split("#", 1)[0]
                anchor_part = target.split("#", 1)[1] if "#" in target else ""
                resolved = os.path.normpath(os.path.join(os.path.dirname(full), file_part))
                if not os.path.exists(resolved):
                    fail(f"{path}:{lineno}: relative link target does not exist: {target}")
                    continue
                if anchor_part and resolved.endswith(".md"):
                    target_rel = rel(resolved)
                    if target_rel not in anchor_cache:
                        anchor_cache[target_rel] = anchors_of(target_rel)
                    if anchor_part not in anchor_cache[target_rel]:
                        fail(f"{path}:{lineno}: anchor '#{anchor_part}' not found in {target_rel}")
                    checked_anchors += 1

    print(f"[ok] checked {len(files)} Markdown file(s), {link_count} link(s), "
          f"{checked_anchors} anchor(s)")


# --------------------------------------------------------------------------
# 6. Placeholder inventory
# --------------------------------------------------------------------------
def report_placeholders() -> None:
    found = []
    for path in markdown_files() + ["CITATION.cff", ".github/FUNDING.yml"]:
        full = os.path.join(ROOT, path)
        if not os.path.isfile(full):
            continue
        for lineno, line in enumerate(read(path).splitlines(), start=1):
            if "MAINTAINER ACTION REQUIRED" in line or "MAINTAINER ACTION" in line:
                found.append(f"  {path}:{lineno}")
    if found:
        print(f"[note] open maintainer placeholders ({len(found)}):")
        print("\n".join(found))
    else:
        print("[ok] no open maintainer placeholders")


def main() -> int:
    print(f"Repository root: {ROOT}\n")
    check_required_files()
    check_artefacts()
    check_yaml()
    check_citation()
    check_markdown()
    report_placeholders()

    print()
    for message in warnings:
        print(f"[warn] {message}")
    for message in failures:
        print(f"[fail] {message}")

    print()
    if failures:
        print(f"RESULT: FAILED ({len(failures)} error(s), {len(warnings)} warning(s))")
        return 1
    print(f"RESULT: PASSED (0 errors, {len(warnings)} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
