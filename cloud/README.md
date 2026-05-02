# Mirage Cloud (scaffolding)

Early-stage commercial scaffolding for the Mirage hosted control
plane. **Not yet wired to a backend.** The OSS runtime gateway under
`mirage/` is the source of truth for policy decisions; this control
plane is the multi-tenant management surface that ships on top of it.

## What this directory is

A Next.js 15 app with three placeholder routes:

- `/policies` (policy authoring stub)
- `/fleet` (multi-agent fleet view stub)
- `/audit-log` (audit log export stub)

There is no backend, no auth, no database, and no API client. Each
route renders a static description of what it will do and an unchecked
list of the surfaces it will expose. The intent is to mark the
commercial layer's shape so the OSS repo's structure makes the split
visible.

## Why it lives here

Two reasons:

1. **Single source of truth on the boundary.** The brief separation
   between OSS core (`mirage/`, `examples/`, `benchmarks/`, `ui/`,
   `demo_ui/`) and commercial layer (`cloud/`) is easier to enforce
   when both live in the same repo. Reviewers can see at a glance
   which side of the line a change lands on.
2. **No vendor lock-in pretence.** Anyone forking the OSS code can
   ignore `cloud/` entirely. The OSS gateway runs without it.

## Why it is not in `mirage/`

`mirage/` is the importable Python package shipped on PyPI as
`mirage-ci`. The hosted control plane is not part of that package. It
runs as a separate process, in a separate language, with a separate
deployment story. Keeping them visually separate now avoids surprises
when the commercial layer grows past stubs.

## Running the scaffolding (optional)

```bash
cd cloud
npm install
npm run dev
```

The scaffolding is just static stubs; nothing useful happens beyond
clicking between routes.

## What ships here next

When the commercial layer ships beyond scaffolding, expect:

- backend (FastAPI or similar) wired to a managed Postgres for tenant
  metadata, policy versions, and audit log
- per-environment auth, RBAC, SSO
- the three stub routes wired to real data
- billing + plan management
- a CLI (`mirage cloud login`, `mirage cloud push policies.yaml`) so
  operators can manage policies without leaving the terminal

None of that is in this directory yet. This is scaffolding, not a
product.
