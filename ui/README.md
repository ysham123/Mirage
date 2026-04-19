# Mirage Next.js Console

The `ui/` app is the richer Mirage operator client.

It does not replace `demo_ui/`. The current split is:

- `demo_ui/`: FastAPI console API plus the zero-dependency legacy HTML shell
- `ui/`: Next.js client that consumes that API for a more polished review UX

The current client depends on these shared backend endpoints:

- `/api/metrics/overview`
- `/api/metrics/runs/{run_id}`
- `/api/chat/stream?run_id=...`
- `/api/runs/{run_id}/side-effects/{step_index}/suppress`

## Local dev

Terminal 1: start the shared console API/backend.

```bash
make console-api
```

That serves:

- API + legacy shell on `http://127.0.0.1:5100`

Terminal 2: install UI dependencies.

```bash
make ui-install
```

Terminal 3: start the Next.js client against the local console API.

```bash
make ui-dev-local
```

Then open:

- `http://127.0.0.1:3000` for the Next.js client
- `http://127.0.0.1:5100` for the legacy HTML shell

## Environment

The Next.js client reads:

```bash
NEXT_PUBLIC_MIRAGE_API_BASE_URL=http://127.0.0.1:5100
```

See [.env.example](.env.example) for the local default.

## Verification

```bash
make ui-test
```
