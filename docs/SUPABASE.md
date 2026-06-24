# Supabase — konfiguracja bazy Life OS

## 1. Projekt w Supabase

1. Wejdź na [supabase.com](https://supabase.com) → **New project**.
2. Wybierz region (np. `eu-central-1`), ustaw hasło do bazy — **zapisz je**.
3. Poczekaj aż projekt się utworzy.

## 2. Connection string

**Dashboard → Project Settings → Database → Connection string**

Wybierz:
- **URI**
- **Session pooler** (port `5432`) — zalecane dla FastAPI

Skopiuj URL w formacie:
```
postgresql://postgres.[PROJECT_REF]:[YOUR_PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
```

## 3. Plik `.env`

Zamień lokalny `DATABASE_URL` na Supabase (zakomentuj linię z `db:5432`):

```env
# DATABASE_URL=postgresql+asyncpg://lifeos:lifeos@db:5432/lifeos
DATABASE_URL=postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
```

Aplikacja sama zamieni `postgresql://` na `postgresql+asyncpg://` i włączy SSL.

> **Transaction pooler** (port `6543`): jeśli używasz tego portu, connection string też zadziała — aplikacja wyłączy statement cache.

## 4. Utworzenie tabel

### Opcja A — SQL Editor (jednorazowo)

1. Supabase → **SQL Editor** → New query
2. Wklej zawartość pliku `backend/scripts/supabase_schema.sql`
3. **Run**

### Opcja B — skrypt Python (zalecane)

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml run --rm api python -m scripts.init_db
```

Tabele powstaną też automatycznie przy pierwszym starcie API (`create_all` w `lifespan`).

## 5. Uruchomienie stacku na Supabase

Bez lokalnego Postgresa:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml up -d --build
```

Opcjonalnie seed demo:

```bash
docker compose -f docker-compose.yml -f docker-compose.supabase.yml --profile seed run --rm seed
```

## 6. Weryfikacja

- API: `http://localhost:8002/health` → `{"status":"ok"}`
- Supabase → **Table Editor** — powinny być tabele `books`, `reading_logs`, …
- Frontend: `http://localhost:5173`

## 7. Lokalny Postgres (dev offline)

Gdy chcesz wrócić do Dockera bez chmury:

```env
DATABASE_URL=postgresql+asyncpg://lifeos:lifeos@db:5432/lifeos
```

```bash
docker compose up -d
```

## Uwagi

- Nie commituj `.env` z hasłem — jest w `.gitignore`.
- Backup: Supabase Dashboard → Database → Backups (plan darmowy: ograniczenia).
- Produkcja na domowym serwerze: ten sam `DATABASE_URL` w `.env` na hoście.
