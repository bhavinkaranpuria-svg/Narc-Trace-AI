# Deploying NARC-TRACE AI

Two services to get live: the FastAPI backend (which owns a SQLite evidence
ledger and an RSA signing key on local disk) and the Next.js frontend
(stateless).

**The one thing that matters more here than in a typical app:** the backend
writes state to disk (`backend/data/`) that the whole point of this project
depends on — the hash-chained evidence records and the signing key. Deploy
it somewhere that gives that directory a real, persistent volume, or be
explicit with yourself that you're accepting a demo that can lose its
ledger.

---

## Path A — Docker Compose on a VPS (recommended)

Real persistence, full control, ~$4–6/month (a small Hetzner or
DigitalOcean box). This repo already has the Dockerfiles and compose file
you need.

1. **Get a VPS** with Docker available (most providers offer a
   "Docker" or "Docker on Ubuntu" base image — pick that and you can skip
   installing Docker yourself).

2. **Copy the project to the server** (`git clone` your repo, or `scp` the
   folder) and configure it:
   ```bash
   cd narc-trace-ai
   cp .env.example .env
   ```
   Edit `.env`:
   ```
   NEXT_PUBLIC_API_URL=http://<your-server-ip>:8000
   ALLOWED_ORIGINS=http://<your-server-ip>:3000
   ```

3. **Build and start both services:**
   ```bash
   docker compose up --build -d
   ```
   The backend's data volume (`narctrace_data`) persists across restarts
   and redeploys — `docker compose up --build` again later will not wipe
   your evidence ledger or signing key.

4. **Open the ports** in your provider's firewall (3000 and 8000), then
   visit `http://<your-server-ip>:3000`.

5. **Optional, for a real domain + HTTPS:** put Caddy or nginx in front —
   Caddy in particular is a one-line reverse proxy with automatic TLS
   (`yourdomain.com { reverse_proxy localhost:3000 }`,
   `api.yourdomain.com { reverse_proxy localhost:8000 }`). Then rebuild the
   frontend with `NEXT_PUBLIC_API_URL=https://api.yourdomain.com` and set
   `ALLOWED_ORIGINS=https://yourdomain.com` on the backend. This isn't
   wired up in the repo — it's a couple of lines in a Caddyfile if you want
   it.

To update after a code change: `docker compose up --build -d` again — the
named volume is untouched.

---

## Path B — Render (backend) + Vercel (frontend)

Fastest way to a public link — good for a demo video or a link in your PPT.
Read the caveat first.

> **Caveat:** Render's free web-service tier runs on an **ephemeral
> filesystem** — anything written to disk after boot, including this app's
> SQLite ledger and RSA key, is lost whenever the instance is recycled, and
> a persistent disk is a paid-plan feature, not something the free tier
> offers. Free instances also spin down after ~15 minutes idle and take
> 30–50 seconds to wake on the next request. For a "click the link, poke
> around for five minutes" demo this is fine. If you want the ledger to
> actually survive between judging sessions, use Render's Starter plan
> (~$7/month per service) and attach a paid persistent disk mounted at
> `/app/data` — or just use Path A, which costs about the same and gives
> you full persistence by default.

### 1. Backend → Render

1. Push this repo to GitHub.
2. On Render: **New → Web Service**, connect the repo, set **Root
   Directory** to `backend`.
3. Render will detect the `Dockerfile` automatically (Environment:
   Docker) — no build/start commands needed.
4. Deploy. Note the resulting URL, e.g. `https://narc-trace-api.onrender.com`.
5. *(Only if you upgraded to a paid plan)* add a persistent disk mounted at
   `/app/data`.

### 2. Frontend → Vercel

1. On Vercel: **Add New → Project**, import the same repo, set **Root
   Directory** to `frontend`.
2. Add an environment variable: `NEXT_PUBLIC_API_URL` =
   `https://narc-trace-api.onrender.com` (the URL from step above).
3. Deploy. Vercel gives you something like
   `https://narc-trace-ai.vercel.app`.

### 3. Lock down CORS

Back on Render, add an environment variable on the backend service:
`ALLOWED_ORIGINS=https://narc-trace-ai.vercel.app` (your actual Vercel
URL), then redeploy the backend so it stops accepting requests from `*`.

Vercel's free Hobby plan is fine for this — it's non-commercial personal
use, which a hackathon prototype is.

---

## Environment variables reference

| Variable | Where | Meaning |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | frontend, build time | Backend URL the **browser** calls. Baked in at build — changing it needs a rebuild, not just a restart. |
| `ALLOWED_ORIGINS` | backend, runtime | Comma-separated exact frontend origin(s) allowed by CORS. `*` for local dev only. |

## If you lose the signing key

If `backend/data/keys/` is ever wiped (e.g. a Render free-tier recycle),
the app just generates a fresh RSA keypair on next boot — but every record
signed under the old key will fail `POST /api/verify`'s signature check
against the new public key fingerprint. That's not a bug, it's the
tamper-evidence working correctly: a signature only verifies against the
key that made it. Back up `backend/data/keys/` alongside the database if
you need signatures to stay verifiable long-term.
