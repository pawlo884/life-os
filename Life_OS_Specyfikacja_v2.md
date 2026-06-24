# Osobisty Asystent "Life OS" - Pełna Specyfikacja Projektowa

**Główny cel:** Stworzenie bezkompromisowego, dedykowanego systemu do zarządzania czasem, nawykami, czytaniem oraz procesem przebranżowienia. System ma pełnić rolę osobistego asystenta i "bata" motywacyjnego.

**Moduł główny:** Czytanie książek — reszta systemu budowana wokół tego rdzenia.

**Stack technologiczny:**
* **Backend:** FastAPI, PostgreSQL, SQLAlchemy (asynchronicznie)
* **Frontend:** React (Vite) + Tailwind CSS
* **Interfejsy:** Bot Discord, Dashboard Webowy
* **Integracje:** Strava API (webhooki), Google Calendar API
* **Infrastruktura:** Docker, Docker Compose, Nginx (wdrożenie na domowym serwerze z Ubuntu)

---

## 1. Główne Moduły Systemu

### 1.1. Moduł Czytania *(główny, pierwszy)*
Rdzeń Life OS — półka książek, śledzenie postępu i motywacja do regularnej lektury.
* **Półka książek:** Tabela `books` — tytuł, autor, okładka, liczba stron, status, jedna aktywna książka.
* **Logowanie postępu:** Użytkownik podaje **bieżącą stronę** (nie liczy ręcznie delty). System wylicza tempo i estymuje datę ukończenia.
* **Historia i heatmapa:** Tabela `reading_logs` — dzienne wpisy stron (delta) pod wykres aktywności (wzór z GitHuba).
* **AI enrich:** Wyszukiwanie metadanych książki (tytuł, autor, strony, okładka) przez Gemini + Lubimyczytac.pl dla polskich wydań.
* **Interfejsy:** Dashboard (React), komendy Discord (`/read`, `/book`, `/books`, …).

### 1.2. Tracker Treningów i Aktywności (Strava + Custom)
Moduł automatycznie logujący aktywność fizyczną w celu utrzymania ciągłości (tzw. "streak").
* **Automatyzacja:** Integracja ze Stravą dla automatycznego logowania treningów (basen, rower, bieganie).
* **Manualne logowanie (przez Discord):** Szybkie wprowadzanie treningów siłowych i sesji core.
* **Grywalizacja:** Heatmapa na dashboardzie oraz alerty na Discordzie o ryzyku przerwania ciągłości.

### 1.3. Lejek Szukania Pracy (Job Hunt CRM)
Podejście procesowe do zmiany kariery na stanowiska Python Developer / DevOps Engineer.
* Tablica Kanban z etapami: *Do zaaplikowania*, *Wysłane CV*, *Rozmowa (HR)*, *Rozmowa (Tech)*, *Zadanie rekrutacyjne*, *Odrzucone*, *Oferta*.
* KPI tygodniowe — czy wysłano wystarczającą liczbę aplikacji.

### 1.4. Integracja z Kalendarzem Google (Terminy i SLA)
Zarządzanie terminami (lekarz, dentysta, spotkania) oraz time-blocking.
* Komendy na Discordzie tworzą eventy w Google Calendar.
* SLA: priorytety i alerty o zbliżających się deadline'ach zadań krytycznych.

---

## 2. Architektura i Baza Danych (SQLAlchemy)

Projekt organizujemy jako monorepo z podziałem na kontenery.

**PostgreSQL** — jedna baza, single-user (bez tabeli `users`).  
**Schemat:** SQLAlchemy 2.x (async), tabele tworzone przy starcie API (`create_all`). Nowe kolumny na istniejących tabelach dodawane przez `ALTER TABLE … IF NOT EXISTS` w `lifespan`. Planowane: migracje **Alembic**.

### Diagram relacji

```
books 1───* reading_logs

tasks, job_applications, fitness_logs  — tabele niezależne (moduły poboczne)
```

### Relacyjne Modele Danych (PostgreSQL)

#### `books` (Półka książek) — **moduł główny**
| Kolumna | Typ | Opis |
|---------|-----|------|
| `id` | Integer (PK) | |
| `title` | String(255) | Tytuł |
| `author` | String(255), nullable | Autor |
| `total_pages` | Integer | Liczba stron wydania |
| `current_page` | Integer, default 0 | Bieżąca strona |
| `status` | String(32), default `READING` | `READING`, `COMPLETED`, `PAUSED`, `QUEUED` |
| `is_active` | Boolean, default false | Jedna aktywna książka na raz |
| `cover_url` | String(512), nullable | URL okładki |
| `created_at` | DateTime | Data dodania |

#### `reading_logs` (Historia czytania)
| Kolumna | Typ | Opis |
|---------|-----|------|
| `id` | Integer (PK) | |
| `book_id` | Integer (FK → `books.id`, CASCADE) | |
| `pages_read` | Integer | Delta stron w danym dniu (wyliczana z `current_page`) |
| `log_date` | Date | Dzień wpisu |
| `note` | Text, nullable | Opcjonalna notatka |
| `created_at` | DateTime | Czas wpisu |

#### `tasks` (Zadania życiowe i kalendarz)
| Kolumna | Typ | Opis |
|---------|-----|------|
| `id` | Integer (PK) | |
| `title` | String(255) | |
| `due_date` | DateTime, nullable | Termin |
| `status` | String(32), default `TODO` | `TODO`, `IN_PROGRESS`, `DONE` |
| `is_sla_critical` | Boolean, default false | Zadanie krytyczne (SLA) |
| `google_event_id` | String(255), nullable | ID eventu w Google Calendar |

#### `job_applications` (CRM rekrutacyjny)
| Kolumna | Typ | Opis |
|---------|-----|------|
| `id` | Integer (PK) | |
| `company` | String(255) | Firma |
| `role` | String(255) | Stanowisko (np. Python Developer) |
| `status` | String(64) | Etap lejka (Kanban) |
| `tech_stack` | String(512), nullable | Technologie z ogłoszenia |
| `notes` | Text, nullable | Notatki |
| `applied_date` | Date, nullable | Data aplikacji |

#### `fitness_logs` (Treningi)
| Kolumna | Typ | Opis |
|---------|-----|------|
| `id` | Integer (PK) | |
| `source` | String(32) | `STRAVA`, `DISCORD_MANUAL` |
| `activity_type` | String(32) | `SWIM`, `GYM`, `CORE`, `RUN`, … |
| `duration_minutes` | Integer | Czas trwania |
| `date` | Date | Dzień aktywności |
| `streak_impact` | Boolean, default true | Czy liczy się do dziennego streaka |

> **Uwaga:** Tabela `learning_progress` w kodzie jest **legacy** (pozostałość wcześniejszego pomysłu trackerów kursów). **Nie jest częścią specyfikacji** — do usunięcia z kodu i bazy.

### API — główne prefixy
| Moduł | Endpointy | Status |
|-------|-----------|--------|
| **Czytanie** | `/api/v1/books`, `/books/read`, `/books/enrich` | ✅ wdrożone (główny) |
| Zadania | `/api/v1/tasks` | model + API |
| Rekrutacja | `/api/v1/jobs` | model + API |
| Fitness | `/api/v1/fitness` | model + API |

---

## 3. Komendy Osobistego Bota (Discord)

Bot pełni rolę błyskawicznego interfejsu (CLI w komunikatorze).

### Czytanie *(główny moduł, wdrożone)*
* `/read [strona] [książka?]` — ustawia bieżącą stronę aktywnej książki.
  * *Przykład:* `/read 120` lub `/read 88 Fenomen poranka`
* `/book [tytuł] [strony] [autor?]` — dodaje książkę na półkę.
* `/books` — lista książek z postępem.
* `/active [tytuł]` — ustawia aktywną książkę.
* `/delete-book [tytuł]` — usuwa książkę z półki.

### Planowane (moduły poboczne)
* `/task [zadanie] [data/czas]` — dodaje do DB i Google Calendar.
* `/trening [typ] [czas]` — loguje trening ręczny (streak).
* `/job [firma] [stanowisko] [status]` — karta w CRM rekrutacyjnym.
* `/raport` — zrzut dnia (czytanie, aplikacje, streak).

---

## 4. Wdrożenie i Infrastruktura (Self-Hosted)

Całość jest przystosowana do wdrożenia na własnym, domowym sprzęcie.

1. **Docker Compose:** `api` (FastAPI), `bot` (Discord), `frontend` (React/Vite), `db` (Postgres).
2. **Reverse Proxy:** Nginx na Ubuntu (sieć lokalna lub domena z Let's Encrypt).
3. **Backup:** Automatyczne dumpy Postgres cronem.

---

## 5. Roadmapa Wdrożenia (Fazy MVP)

* **Faza 1 — Czytanie (główny moduł):** `books` + `reading_logs`, dashboard, heatmapa, AI enrich, okładki, bot Discord. ✅ (`feature/reading-module`)
* **Faza 2 — Fitness:** `fitness_logs`, Strava, streak, heatmapa treningowa.
* **Faza 3 — Job Hunt:** Kanban rekrutacji, KPI aplikacji.
* **Faza 4 — Kalendarz i zadania:** Google Calendar, SLA, `/task`.
* **Faza 5 — Hardening:** Alembic, backupy produkcyjne, wdrożenie na domowy serwer.
