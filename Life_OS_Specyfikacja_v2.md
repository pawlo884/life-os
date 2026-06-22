# Osobisty Asystent "Life OS" - Pełna Specyfikacja Projektowa

**Główny cel:** Stworzenie bezkompromisowego, dedykowanego systemu do zarządzania czasem, nawykami, nauką oraz procesem przebranżowienia. System ma pełnić rolę osobistego asystenta i "bata" motywacyjnego.

**Stack technologiczny:** * **Backend:** FastAPI, PostgreSQL, SQLAlchemy (asynchronicznie)
* **Frontend:** React (Vite) + Tailwind CSS
* **Interfejsy:** Bot Discord, Dashboard Webowy
* **Integracje:** Strava API (webhooki), Google Calendar API
* **Infrastruktura:** Docker, Docker Compose, Nginx (wdrożenie na domowym serwerze z Ubuntu)

---

## 1. Główne Moduły Systemu

### 1.1. Tracker Treningów i Aktywności (Strava + Custom)
Moduł automatycznie logujący aktywność fizyczną w celu utrzymania ciągłości (tzw. "streak").
* **Automatyzacja:** Integracja ze Stravą dla automatycznego logowania treningów (basen, rower, bieganie).
* **Manualne logowanie (przez Discord):** Szybkie wprowadzanie treningów siłowych i sesji core, które nie zawsze są logowane przez GPS/zegarek.
* **Grywalizacja:** Generowanie "heatmapy" (wzór z GitHuba) na dashboardzie oraz alerty na Discordzie o ryzyku przerwania ciągłości.

### 1.2. Moduł Nauki i Rozwoju
Zarządzanie postępami w przyswajaniu wiedzy.
* **Tracker Kursów:** Rozbijanie dużych kursów (np. Data Science, Machine Learning, Big Data) na moduły i lekcje. Wyliczanie procentowego ukończenia.
* **Tracker Czytania:** Wprowadzanie liczby przeczytanych stron. System sam wylicza średnie tempo i estymuje datę zakończenia książki na podstawie obecnej rutyny.

### 1.3. Lejek Szukania Pracy (Job Hunt CRM)
Podejście procesowe do zmiany kariery na stanowiska Python Developer / DevOps Engineer.
* Tablica Kanban z etapami: *Do zaaplikowania*, *Wysłane CV*, *Rozmowa (HR)*, *Rozmowa (Tech)*, *Zadanie rekrutacyjne*, *Odrzucone*, *Oferta*.
* System powiadomień i statystyk: Wskaźniki informujące, czy w danym tygodniu wysłano wystarczającą liczbę aplikacji ("KPI" szukania pracy).

### 1.4. Integracja z Kalendarzem Google (Terminy i SLA)
Zarządzanie terminami (np. lekarz, dentysta, spotkania) oraz time-blocking.
* Komendy na Discordzie automatycznie tworzą eventy w Google Calendar.
* Zastosowanie nawyków z logistyki (SLA): określanie priorytetów i nieprzekraczalnych terminów dla kluczowych zadań z alertami o zbliżającym się "deadlinie".

---

## 2. Architektura i Baza Danych (SQLAlchemy)

Projekt organizujemy jako monorepo z podziałem na kontenery.

### Relacyjne Modele Danych (PostgreSQL)

#### `tasks` (Zadania życiowe i kalendarz)
* `id`: Integer (PK)
* `title`: String(255)
* `due_date`: DateTime
* `status`: String (TODO, IN_PROGRESS, DONE)
* `is_sla_critical`: Boolean (Oznaczanie zadań absolutnie krytycznych)
* `google_event_id`: String (Do synchronizacji)

#### `job_applications` (CRM Rekrutacyjny)
* `id`: Integer (PK)
* `company`: String(255)
* `role`: String(255) (np. Python Developer, DevOps)
* `status`: String
* `tech_stack`: String (Wyłapane słowa kluczowe z ogłoszenia)
* `notes`: Text
* `applied_date`: Date

#### `learning_progress` (Kursy i Książki)
* `id`: Integer (PK)
* `resource_type`: String (COURSE, BOOK)
* `title`: String(255)
* `total_units`: Integer (Całkowita liczba stron / lekcji)
* `completed_units`: Integer
* `status`: String

#### `fitness_logs` (Treningi)
* `id`: Integer (PK)
* `source`: String (STRAVA, DISCORD_MANUAL)
* `activity_type`: String (SWIM, GYM, CORE, RUN)
* `duration_minutes`: Integer
* `date`: Date
* `streak_impact`: Boolean (Czy zalicza się do dziennego streaka)

---

## 3. Komendy Osobistego Bota (Discord)

Bot pełni rolę błyskawicznego interfejsu (CLI w komunikatorze). 

* `/task [zadanie] [data/czas]` 
  * *Przykład:* `/task Dentysta jutro 15:00` (Dodaje do DB i Google Calendar).
* `/trening [typ] [czas]` 
  * *Przykład:* `/trening silownia 60` lub `/trening core 30` (Aktualizuje streak).
* `/czytam [strony]` 
  * *Przykład:* `/czytam 45` (Loguje strony i podaje wyliczoną estymację ukończenia).
* `/nauka [kurs] [modul]`
  * *Przykład:* `/nauka data_science modul_4` (Przesuwa pasek postępu kursu).
* `/job [firma] [stanowisko] [status]` 
  * *Przykład:* `/job RST_Software Python_Dev wyslane` (Dodaje kartę do CRM).
* `/raport` 
  * *Działanie:* Bot generuje szybki zrzut dnia: "Dzisiaj: 1x aplikacja wysłana. Streak treningowy: 12 dni. Zostało 150 stron książki."

---

## 4. Wdrożenie i Infrastruktura (Self-Hosted)

Całość jest przystosowana do wdrożenia na własnym, domowym sprzęcie.

1. **Docker Compose:** Definiuje 4 usługi: `api` (FastAPI), `bot` (Discord Python), `frontend` (React/Nginx), `db` (Postgres).
2. **Reverse Proxy:** Nginx (skonfigurowany na głównym systemie Ubuntu, np. na Twoim mini PC), który kieruje ruch po sieci lokalnej lub przez wystawioną domenę (z certyfikatami Let's Encrypt).
3. **Backup:** Automatyczne zrzuty (dump) bazy Postgres cronem do bezpiecznego folderu.

---

## 5. Roadmapa Wdrożenia (Fazy MVP)

* **Faza 1 (Fundamenty backendowe):** Modele SQLAlchemy, API w FastAPI, baza PostgreSQL w Dockerze.
* **Faza 2 (Centrum dowodzenia):** Podpięcie bota na Discordzie i oprogramowanie logiki dodawania zadań i treningów przez czat.
* **Faza 3 (Świat zewnętrzny):** Autoryzacja i integracja z Google Calendar API oraz obsługa webhooków ze Stravy.
* **Faza 4 (Wizualizacja):** Zbudowanie SPA w React + Tailwind do wyświetlania heatmap, pasków postępu kursów i tablicy Kanban dla rekrutacji.
