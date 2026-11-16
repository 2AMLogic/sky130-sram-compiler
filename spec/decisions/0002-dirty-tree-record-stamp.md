# 0002: a record generated from a dirty tree stamps `<sha>-dirty`

Status: recorded (issue #151). Not a spec change.

## Context

`git_short_sha` stamped plain `HEAD` with no check that the working tree matches
it, so a record generated from uncommitted code named a commit that cannot
reproduce it — the commit does not contain the code that produced the record.
The concrete instance is PR #139's `20261115T235702Z-88af0fd.md`: the documented
procedure aborts at `88af0fd` (the `#131` DRC-deck fix is missing there), and
the record was generated with that fix present but uncommitted. Records are
append-only, so once merged the mis-attribution is permanent.

The alternative — raising `ProvenanceError` on a dirty tree, forcing "commit
first, then record" — runs into a chicken-and-egg that every "fix + evidence in
one PR" workflow hits: a record demonstrating a fix can only name a post-fix
commit, which does not exist until after the record would be generated. Refusal
therefore needs an escape hatch flag for no extra honesty.

## Decision

`git_short_sha` stamps a dirty working tree `<sha>-dirty` instead of a bare
sha, in the record title and in the record filename. The stamp is honest about
being un-reproducible from the named commit, and the suffix is visible in the
title at a glance.

"Dirty" means `git status --porcelain` is non-empty:

- tracked modifications count, and untracked non-ignored files count (a new
  source file is a real reproducibility gap);
- gitignored scratch output stays out (default `--porcelain` behaviour);
- every `records/` directory is excluded by pathspec
  (`:(exclude,glob)**/records/**`), so an earlier uncommitted record in the
  same PR does not mark the next one dirty.

A failing `git status` raises `ProvenanceError` — it is never read as "clean"
(the same refusal class as #103).

Rejected: raising on a dirty tree (blocks the fix+evidence workflow above, and
an `--allow-dirty` escape hatch is new CLI surface for no extra honesty); and
excluding untracked files from the check (hides real gaps behind the flag that
gitignore already provides for scratch).
