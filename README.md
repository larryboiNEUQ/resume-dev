# resume-dev

A skill for coding agents (Claude Code, Cursor and similar). It resumes work in a repository that tracks specs and issues as local Markdown files.

It scans specs, issues, merge requests, branches and worktrees, shows a status table, proposes doc updates and cleanup, and executes only the scope you confirm. The MR table lists the spec each MR delivers, taken from the spec directories the MR changes.

## Files

- `SKILL.md` is the skill. The workflow is written in Chinese.
- `scan.py` is the read-only scanner. It needs Python 3, `git`, and `glab` for GitLab merge requests.

## Install

Put both files in `~/.agents/skills/resume-dev/`. Link it into the agent that reads skills from another folder, for example `~/.claude/skills/resume-dev`.

Run `/resume-dev` from the repository root.

## Notes

- Spec directories are any folder with `issues/*.md`, `spec.md`, `requirements.md` or `tasks.md`. The scanner does not assume a location.
- The scanner uses `glab`. For GitHub you need to adapt the merge request calls in `scan.py`.
