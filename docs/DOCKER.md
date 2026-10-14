# Run the project with Docker

Docker Compose builds and runs three images: the upstream records service, the project editor API, and the static React UI. Only the UI is published to the host. It serves the app and proxies `/api` to the backend; the backend alone calls the upstream service.

## Start

From the repository root, with Docker Desktop running:

```sh
docker compose config
docker compose up --build --detach
docker compose ps
```

Open `http://localhost:8082`. The browser API is available through `http://localhost:8082/api/projects`. Backend and upstream ports stay on the Compose network. Set `APP_PORT` to change the host port. The challenge upstream uses a fixed local API key.

The default Compose settings disable the upstream's random slow reads and timeout responses so a local walkthrough is predictable. Set `UPSTREAM_SLOW_RATE=0.1` or `UPSTREAM_TIMEOUT_RATE=0.1` in the shell or a Compose `.env` file to enable those challenge behaviors.

Run the repeatable end-to-end check against the running stack:

```sh
uv run --project backend python docker/smoke_test.py --base-url http://localhost:8082
```

## Stop and inspect

```sh
docker compose logs --follow
docker compose down
```

The upstream stores records in memory. Edits reset when its container is recreated. Use `docker compose down --volumes` only if you later add persistent Compose volumes.

## Images and boundaries

Compose builds `cms2-project-editor-frontend`, `cms2-project-editor-backend`, and `cms2-project-editor-upstream` from the Dockerfiles under `docker/`. Python dependencies come from the checked-in lockfiles; the frontend uses `npm ci`. Python and Nginx runtime images run as non-root users. The Nginx image serves the built SPA and forwards relative `/api/` requests to the API container. The upstream and backend do not publish host ports.

This is a local challenge stack. The default API key is the upstream's documented local key, data is ephemeral, and no production secret management or persistent database is configured.
