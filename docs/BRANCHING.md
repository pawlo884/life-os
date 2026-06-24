# Git branching workflow

## Branches

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready releases only |
| `develop` | Integration branch — merge features here first |
| `feature/*` | One feature or module per branch |
| `chore/*` | Infrastructure, tooling, Docker, CI |
| `fix/*` | Bug fixes |

## Module branches (Life OS)

| Branch | Module |
|--------|--------|
| `feature/reading-module` | **Główny moduł** — books, reading logs, dashboard, AI lookup |
| `feature/workouts-module` | Fitness, Strava, streaks *(planned)* |
| `feature/job-hunt-module` | Applications CRM, Kanban *(planned)* |

## Workflow

1. Branch from `develop`:
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/my-feature
   ```
2. Commit in small, logical chunks (one concern per commit).
3. Open PR: `feature/*` → `develop`
4. After testing: `develop` → `main`

## Commit message format

```
feat(reading): add AI book enrichment endpoint
fix(docker): hardcode local DATABASE_URL in compose
chore: update seed script for books
```

Prefixes: `feat`, `fix`, `chore`, `docs`, `refactor`
