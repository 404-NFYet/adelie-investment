# Adelie Codex Rules

## Frontend Sync-First Rule

- Always read `lxd/docs/sync-guide.md` before frontend work.
- For any task that touches `frontend/**`, React UI, styling, FE build/test, or FE commits, run sync first:
  - `bash /home/ubuntu/.codex/skills/frontend-sync-first/scripts/sync_frontend.sh`
- If current branch is not `dev/frontend`, stop and ask before switching branches.
- If working tree is dirty, stop and ask before syncing.
- If merge conflict happens during sync, stop and ask; do not auto-resolve.

## Skill Invocation Rule

- Invoke `frontend-sync-first` for frontend-related requests by default.
- Skip sync only when the user explicitly says to skip it.
