---
name: resume-dev
description: 回到用本地 Markdown spec/issue 管理工作的仓库继续开发时用：扫描 spec/issue、MR、分支和工作区，展示状态表，提出文档更新和清理计划，用户确认后执行。
disable-model-invocation: true
---

# resume-dev

四步按顺序走。第 3 步结束时停下，等用户确认执行范围。扫描和计划都是只读的；只有第 4 步会修改文件、git 或 GitLab，而且只做用户确认过的那部分。

## 1. 扫描

```powershell
[Console]::OutputEncoding=[Text.Encoding]::UTF8; python -X utf8 "$HOME\.agents\skills\resume-dev\scan.py"
```

在仓库根目录运行。脚本以当前目录所在的 git 仓库为扫描对象。

spec 和 issue 放在哪、文件叫什么，以仓库自己的 issue tracker 文档为准（通常由 `AGENTS.md` 指向）。脚本不预设位置：凡是含 `issues/*.md`、`spec.md`、`requirements.md` 或 `tasks.md` 的目录都当作 spec 目录，表里显示的是相对仓库根的完整路径。主干（`main` 或 `master`）也由脚本识别，打印在第一行。

脚本大约 30 秒跑完，会输出这几块：工作区里的 spec 表（spec 状态、`tasks.md` 未勾项、每张 issue 的状态、未勾项/总项和 Blocked by）、只存在于其他远端分支上的 spec、开着的 MR（`spec=` 是该 MR 相对目标分支改动的 spec 目录，`NONE` 表示没有，要在 MR 表里提醒补 spec）、工作区列表（HEAD 是否已在主干、对应的 MR）、`.git/worktrees` 残留目录、本地分支表（是否已在主干、领先主干几个提交、对应的 MR、被哪些 ref 包含），以及远端分支、tag 和 stash。

**完成标准：** 拿到完整的脚本输出，并且 spec 表里的目录和仓库 issue tracker 文档写的位置一致。如果某一节出现 `<timeout`、`git fetch failed` 或 `glab api failed`，或者 spec 表的目录和文档对不上，把这个情况告诉用户，不要用猜测补上那一节。

## 2. 状态展示

用中文输出，按下面的格式。第一句直接给结论。

```markdown
还有 N 个 spec、M 张 issue 没完成，其中 K 张能直接让 agent 开工（`ready-for-agent` 且没有未完成的 blocker）。<已开发完、只等合并的 spec 一句话>

| MR | 对应 spec | 功能 | 结论 |
|---|---|---|---|
| [!8](<web_url>) `<源分支>` → `<目标分支>` | <spec 编号和名称> | <这个 MR 交付什么，1–3 句> | <要不要合并、状态是否可合并、有没有冲突> |

| Spec | 状态 | 未完成的 issue | 卡在哪里 |
|---|---|---|---|
| 050 中国产品价格指标 | Draft | 1 张：01 <slug>，状态 `needs-info` | 等业务补充计算口径 |

其余 N 个历史 spec 都已经结束（完成、关闭、wontfix 或被取代）。

建议接下来先做 <spec>，原因是 <一句话>。
```

- MR 表列出每一个开着的 MR。"对应 spec"和"功能"来自 MR 标题、描述和源分支里的 spec 目录。
- Spec 表每个 spec 占一行，只要它还有状态不是 `done`/`wontfix` 的 issue，或者它只存在于其他远端分支上，就要列出来。
- "卡在哪里"一栏写阻塞原因，信息来自 issue 的状态和最后一条 Comments。

**完成标准：** 扫描结果里每一张未结束的 issue、每一个开着的 MR 都出现在表里。

## 3. 计划

逐行检查扫描结果。每一行最后只能归为四类之一：保留、A 文档更新、B MR 操作、清理（C 现在可清理或 D MR 合并后可清理）。然后按下面的格式写计划，写完就停，问用户要执行哪些部分。

### A：文档状态漂移

spec 文件的格式和状态词表，以仓库的 issue tracker 文档和 triage 标签文档为准（通常由 `AGENTS.md` 指向）。下文的“spec 文件”指 spec 目录里的 `spec.md` 或 `requirements.md`。逐条检查：

- **issue 全部结束：** 如果 spec 的 `Status:` 还是 Proposed、Ready 这类没完成的状态，改成 `Implemented (MR !N, <日期>)`。
- **过时的等待语句：** spec 状态里写着"waits on X"之类的话，但 X 已经完成，就删掉这句。
- **未勾项属于别的 spec：** issue 唯一剩下的未勾项其实是别的 spec 的工作时，把它移出验收清单，改写成 `Transferred to spec NNN rule X (<日期>): ...`，然后把状态改为 `done`。不要把这一项勾成 `[x]`。
- **done/wontfix 的 issue 还有未勾项：** 先读这一项的原文。写着 deferred 或 transferred 的，按上一条处理。wontfix 的 issue 留着未勾项是正常的，保留不动。
- **历史 spec（有 `tasks.md`）缺 `Status:`：** 如果 `tasks.md` 里的顶层项都已勾选，就在 spec 文件里加 `Status: Implemented`。`tasks.md` 本身永远保持原样。
- **负责人已暂停的 spec：** 状态写成 `Paused (owner deferred <日期>)`，其下 issue 的状态保持不变。
- **保持原样的：** `_template`、历史 spec 不统一的状态用词、只存在于另一个开着 MR 分支上的 spec。

### B：MR 操作

- **被另一个 MR 取代的旧 MR：** 先给旧分支的末端提交打 `archive/<name>-v1` tag 并推送，再在旧 MR 留言说明被谁取代、归档在哪个 tag，然后关闭旧 MR，最后用 `git branch -D` 删掉本地和远端分支。
- **等合并的 MR：** 写清合并前还差什么（业务签字、needs-info 的 issue 等）。

### 清理候选

候选项：

- **已完全并入主干的本地分支：** 用 `git branch -d` 删除。
- **`t/*` 这类子分支：** 如果已经被某个归档 tag 包含（看分支表"contained in"一栏），删掉，归档 tag 会保留它们。
- **没有未提交改动的工作区：** 用 `git worktree remove` 删掉。只有缓存文件（`__pycache__`、`.pytest_cache`）算未提交改动时，先删缓存再删工作区。`.codex/` 下的工作区要加一句提醒：它可能正被 Codex 会话使用。
- **`.git/worktrees` 里的残留目录：** 删掉。
- **以下保留：** 当前分支、主干。

每个候选项按它是否依赖开着的 MR，归入两节之一：

- **C. 现在可清理：** 不依赖任何开着的 MR。包括：已在主干的分支；HEAD 已在主干的工作区（看工作区列表的“HEAD in <主干>”，比如停在主干旧提交上的对照工作区）；残留目录；已被归档 tag 包含的分支。
- **D. MR 合并后可清理：** 依赖某个开着的 MR。包括：MR 的源分支（本地和远端），删了远端分支 MR 就没有源分支了；检出这个源分支的工作区，合并前还要在上面改 issue 状态；HEAD 不在主干、只被 MR 分支包含的工作区。每条写明等哪个 MR。

`git fetch --prune` 和 `git worktree prune` 两节末尾各跑一次。

### 计划格式（ASD-STE100）

写法规则：

- 用中文写。每条只写一个动作，用主动祈使句开头（"把…改为…""删除…"）。
- 写出完整的路径、分支名、提交号和日期。
- 动作后面写"原因：…"，一句话说明。
- 有风险的条目，加一句以"注意："开头的提醒。

```markdown
结论：<一句话，说清有几个 MR 开着、需要用户决定的是哪个>。下面的计划都还没执行。

## A. 文档更新（现在提交到 <分支>，合并时一起进主干）

- **A1.** 把 `<path>` 的 `Status: X` 改为 `Status: Y`。原因：<…>。
- **An.** 运行契约校验和 `git diff --check`，通过后提交一次，推送到 <分支>。

## B. MR 操作（<什么时候执行>）

- **B1.** …

## C. 现在可清理

- **C1.** …
- **Cn.** 运行 `git fetch --prune` 和 `git worktree prune`。确认最后只剩 <分支和工作区列表>。

## D. MR 合并后可清理（等 !N 合并）

- **D1.** …
- **Dn.** 运行 `git fetch --prune` 和 `git worktree prune`。确认最后只剩 <分支和工作区列表>。

另外检查过：<不需要处理的项>。

请回复你确认的范围，比如"A 全部 + C"。
```

**完成标准：** 扫描结果的每一行都已归类，计划已经发给用户，并且停在等用户确认的状态。

## 4. 执行用户确认的范围

- **A 文档更新：**
  - 按 `AGENTS.md` 的提交规则：一次提交，只放这些 spec 文件，提交信息用祈使句说明原因。
  - 提交前运行 `git diff --check`；仓库有 `scripts/validate_output_contract.py` 时，也运行 `python scripts/validate_output_contract.py --check-cleaning-lineage`。
  - 带破折号等非 ASCII 字符的行，改之前先读原文，按原文精确替换。
- **B 打 tag：** 先用 `git merge-base --is-ancestor <分支> <tag>` 确认每个要删的分支都被 tag 包含，再推送 tag，并用 `git ls-remote --tags origin "archive/*"` 确认远端已经有了。
- **B 关闭 MR：**
  - 先关闭目标分支是另一个旧分支的 MR，再关它的上游 MR。
  - 用 `glab mr note <iid> -m "..."` 留言，再执行 `glab mr close <iid>`。
- **推送和删远端分支：** `git push` 卡住不动、或报 `could not read Username`，说明 git 没有 HTTPS 凭据。改用 glab 的登录：`git -c credential.helper= -c "credential.helper=!glab auth git-credential" push ...`，并告诉用户可以运行 `glab auth setup-git` 一劳永逸。
- **D 的前提：** 用户说 MR 已合并后才执行。执行前先 `git fetch`，再用 `git merge-base --is-ancestor <分支> origin/<主干>` 确认分支已在主干里。
- **C/D 删工作区：**
  - 删之前再确认一次没有未提交的改动：`git -C <path> status --porcelain --untracked-files=all` 输出为空。
  - 仓库在 OneDrive 下时，`git worktree remove` 和 `git worktree prune` 常会对 `.git/worktrees/<name>` 报 "Permission denied"。遇到时，对每个目录单独执行 `Remove-Item -LiteralPath '<绝对路径>' -Recurse -Force`，再用 `Test-Path` 确认已删除。
- **C/D 删分支：** 先删工作区，再删分支，因为被工作区检出的分支删不掉。远端分支用 `git push origin --delete <分支>` 删除。
- **最后：** 重新运行第 1 步的脚本，用新的输出写汇报。

### 汇报格式

第一句给结论，比如"A 部分已推送到 !8，C 的分支和工作区已清理完"。然后按 A、清理、"现在剩下的"三个部分各写一个小节，每条说明做了什么、确认了什么（提交号、tag、MR 链接）。最后写清还要用户做的事，以及 D 里等哪个 MR 合并后才能做的清理。

**完成标准：** 确认的每一项都已执行并验证，重新扫描的结果和汇报一致。
