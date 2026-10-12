"""Read-only scan of spec/issue status, MRs, branches and worktrees. Prints markdown facts."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
os.environ.update(GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                           encoding="utf-8").stdout.strip())
SPEC_FILES = ("spec.md", "requirements.md")
TERMINAL = {"done", "wontfix"}
BOX_RE = re.compile(r"^\s*- \[( |x|X)\]", re.M)


def field(name):
    return re.compile(rf"^\s*\**{name}\**:\**\s*(.+?)\s*$", re.M | re.I)


STATUS_RE, TYPE_RE, BLOCKED_RE = field("Status"), field("Type"), field("Blocked by")


def run(*args, timeout=60):
    try:
        r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           stdin=subprocess.DEVNULL, timeout=timeout)
    except subprocess.TimeoutExpired:
        return f"<timeout after {timeout}s: {' '.join(args)}>", 124
    return r.stdout.strip(), r.returncode


def git(*args):
    return run("git", *args)[0]


def trunk_name():
    head = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if head.startswith("origin/"):
        return head.split("/", 1)[1]
    for b in ("main", "master"):
        if run("git", "rev-parse", "--verify", "-q", f"refs/heads/{b}")[1] == 0:
            return b
    return "main"


def boxes(text):
    marks = BOX_RE.findall(text)
    return sum(m == " " for m in marks), len(marks)


def first(regex, text):
    m = regex.search(text)
    return m.group(1).strip("*` ") if m else "-"


def discover_specs(paths):
    """A spec dir holds an issues/*.md folder or a spec file; its location is whatever the repo uses."""
    dirs = set()
    for p in paths:
        parts = p.split("/")
        if len(parts) >= 3 and parts[-2] == "issues" and p.endswith(".md"):
            dirs.add("/".join(parts[:-2]))
        elif len(parts) >= 2 and parts[-1] in SPEC_FILES + ("tasks.md",):
            dirs.add("/".join(parts[:-1]))
    return sorted(d for d in dirs if not d.rsplit("/", 1)[-1].startswith("_"))


def spec_rows(read, list_issues, dirs):
    rows = []
    for d in dirs:
        spec = next((t for t in (read(f"{d}/{f}") for f in SPEC_FILES) if t is not None), "")
        tasks = read(f"{d}/tasks.md")
        issues = []
        for fname in list_issues(d):
            body = read(f"{d}/issues/{fname}") or ""
            open_, total = boxes(body)
            issues.append((fname[:-3], first(TYPE_RE, body), first(STATUS_RE, body).split()[0],
                           open_, total, first(BLOCKED_RE, body)))
        rows.append((d, first(STATUS_RE, spec), tasks is not None, boxes(tasks)[0] if tasks else 0, issues))
    return rows


def print_specs(rows, title):
    print(f"## {title}\n")
    print("| spec dir | spec Status | tasks.md open | issues (status open/total boxes) |")
    print("|---|---|---|---|")
    for d, status, has_tasks, task_open, issues in rows:
        iss = "; ".join(f"{i[0][:2]}={i[2]} {i[3]}/{i[4]}" for i in issues) or "-"
        print(f"| {d} | {status} | {task_open if has_tasks else '-'} | {iss} |")
    pending = [(d, i) for d, _, _, _, iss in rows for i in iss if i[2].lower() not in TERMINAL]
    print(f"\nNon-terminal issues: {len(pending)}")
    for d, i in pending:
        print(f"- {d}/issues/{i[0]}.md  Type={i[1]}  Status={i[2]}  open boxes {i[3]}/{i[4]}  Blocked by={i[5]}")
    print()


def local_specs():
    dirs = discover_specs(git("ls-files", "--cached", "--others", "--exclude-standard").splitlines())

    def read(rel):
        p = ROOT / rel
        return p.read_text(encoding="utf-8") if p.exists() else None

    def list_issues(d):
        p = ROOT / d / "issues"
        return sorted(f.name for f in p.glob("*.md")) if p.exists() else []

    return dirs, spec_rows(read, list_issues, dirs)


def branch_only_specs(local_dirs, trunk):
    """Specs that exist only on another remote branch (for example, an unmerged MR)."""
    for ref in git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin").splitlines():
        if ref in ("origin", "origin/HEAD", f"origin/{trunk}"):
            continue
        paths = git("ls-tree", "-r", "--name-only", ref).splitlines()
        extra = [d for d in discover_specs(paths) if d not in local_dirs]
        if not extra:
            continue
        files = set(paths)

        def read(rel, ref=ref):
            if rel not in files:
                return None
            out, code = run("git", "show", f"{ref}:{rel}")
            return out if code == 0 else None

        def list_issues(d):
            prefix = f"{d}/issues/"
            return sorted(p[len(prefix):] for p in files
                          if p.startswith(prefix) and p.endswith(".md") and "/" not in p[len(prefix):])

        print_specs(spec_rows(read, list_issues, extra), f"Specs only on {ref}")


def mrs():
    out, code = run("glab", "api", "projects/:id/merge_requests?state=opened&per_page=50")
    print("## Open MRs\n")
    if code:
        print("glab api failed; check `glab auth status`.\n")
        return {}
    data = json.loads(out)
    for m in data:
        diff, diff_code = run("git", "diff", "--name-only", f"origin/{m['target_branch']}...origin/{m['source_branch']}")
        specs = "diff failed" if diff_code else (", ".join(discover_specs(diff.splitlines())) or "NONE")
        print(f"- !{m['iid']} {m['source_branch']} -> {m['target_branch']} | {m['title']} | "
              f"{m.get('detailed_merge_status')} | conflicts={m.get('has_conflicts')} | spec={specs} | {m['web_url']}")
    print()
    return {m["source_branch"]: m["iid"] for m in data}


def worktrees(open_mr, trunk):
    print("## Worktrees\n")
    blocks = git("worktree", "list", "--porcelain").split("\n\n")
    for blk in blocks:
        kv = dict(l.split(" ", 1) if " " in l else (l, "") for l in blk.splitlines())
        path = kv.get("worktree", "")
        branch = kv.get("branch", "").removeprefix("refs/heads/")
        exists = Path(path).exists()
        dirty = len(run("git", "-C", path, "status", "--porcelain", "--untracked-files=all")[0].splitlines()) \
            if exists else "missing"
        head = kv.get("HEAD", "")
        in_trunk = run("git", "merge-base", "--is-ancestor", head, trunk)[1] == 0 if head else "-"
        mr = f"!{open_mr[branch]}" if branch in open_mr else "-"
        print(f"- {path} | {branch or '(detached ' + head[:7] + ')'} | dirty files: {dirty} | "
              f"HEAD in {trunk}: {in_trunk} | open MR: {mr}")
    meta = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir")) / "worktrees"
    stale = [p.name for p in meta.iterdir()] if meta.exists() else []
    stale = [n for n in stale if not (meta / n / "gitdir").exists()
             or not Path((meta / n / "gitdir").read_text(encoding="utf-8").strip()).exists()]
    print(f"\nStale .git/worktrees metadata dirs: {', '.join(stale) or '-'}\n")


def branches(open_mr, trunk):
    print("## Local branches\n")
    print(f"| branch | upstream | in {trunk} | ahead of {trunk} | open MR | contained in (other refs) |")
    print("|---|---|---|---|---|---|")
    current = git("branch", "--show-current")
    refs = git("for-each-ref", "--format=%(refname:short)|%(upstream:short)", "refs/heads").splitlines()
    for line in refs:
        b, up = line.split("|")
        in_trunk = run("git", "merge-base", "--is-ancestor", b, trunk)[1] == 0
        ahead = git("rev-list", "--count", f"{trunk}..{b}")
        holders = ""
        if not in_trunk:
            sha = git("rev-parse", b)
            holders = ", ".join(r for r in git("for-each-ref", "--contains", sha, "--format=%(refname:short)",
                                                "refs/heads", "refs/tags").splitlines() if r != b)
        mark = " (current)" if b == current else ""
        print(f"| {b}{mark} | {up or '-'} | {in_trunk} | {ahead} | {('!' + str(open_mr[b])) if b in open_mr else '-'} "
              f"| {holders or '-'} |")
    print("\nRemote branches: " + ", ".join(git("branch", "-r", "--format=%(refname:short)").splitlines()))
    print("Tags: " + (", ".join(git("tag").splitlines()) or "-"))
    print("Stashes: " + (str(len(git("stash", "list").splitlines())) if git("stash", "list") else "0") + "\n")


if __name__ == "__main__":
    trunk = trunk_name()
    print(f"# Scan of {ROOT.name} on {git('branch', '--show-current')} @ {git('rev-parse', '--short', 'HEAD')}"
          f" (trunk: {trunk})\n")
    out, code = run("git", "fetch", "--prune", "-q", timeout=90)
    if code:
        out, code = run("git", "-c", "credential.helper=", "-c", "credential.helper=!glab auth git-credential",
                        "fetch", "--prune", "-q", timeout=90)
    if code:
        print(f"git fetch failed ({code}): {out or 'no output; check git credentials'}\n")
    dirs, rows = local_specs()
    print_specs(rows, "Specs in working tree")
    branch_only_specs(set(dirs), trunk)
    open_mr = mrs()
    worktrees(open_mr, trunk)
    branches(open_mr, trunk)
