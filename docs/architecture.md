# Architecture

# Monorepo Structure

\```text
green-log/
├── frontend/
├── backend/
├── docs/
├── specs/
└── infra/
\```

---

# Frontend Architecture

## Stack

- Vue 3
- Vite
- TypeScript
- Tailwind CSS
- PWA

## Structure

\```text
src/
├── api/
├── components/
├── composables/
├── pages/
├── stores/
├── types/
└── utils/
\```

---

# Backend Architecture

## Stack

- FastAPI
- SQLModel
- Alembic

## Layer Structure

\```text
Router
↓
Service
↓
Repository
↓
Database
\```

## Backend Structure

\```text
app/
├── routers/
├── services/
├── repositories/
├── models/
├── schemas/
├── db/
├── core/
└── main.py
\```

---

# Database

## DB

- Turso
- SQLite/libSQL

---

# API Policy

- REST-based
- OpenAPI-first
- Frontend-independent API design

---

# Deployment

## Frontend

- Cloudflare Pages

## Backend

- Render / Fly.io / Railway
