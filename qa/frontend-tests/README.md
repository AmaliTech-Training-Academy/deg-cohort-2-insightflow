# InsightFlow — Frontend Tests

Two test layers live here:

```
qa/frontend-tests/
├── tests/          ← E2E tests (Python + Playwright)
│   ├── test_login.py
│   ├── test_register.py
│   ├── test_forgot_password.py
│   ├── test_dashboard.py
│   ├── test_upload.py
│   ├── test_history.py
│   ├── test_sidebar.py
│   └── test_theme.py
└── unit/           ← Unit tests (Vitest + React Testing Library)
    └── tests/
        ├── components/
        │   ├── StatCard.test.tsx
        │   ├── SourceHealthTable.test.tsx
        │   ├── Button.test.tsx
        │   ├── Input.test.tsx
        │   └── StatusBadge.test.tsx
        └── pages/
            ├── dashboard.test.tsx
            ├── upload.test.tsx
            └── history.test.tsx
```

---

## E2E Tests (Playwright / Python)

### Prerequisites
```bash
cd qa/frontend-tests
pip install -r requirements.txt
playwright install chromium
```

### Run
```bash
# Frontend dev server must be running first:
cd frontend && npm run dev

# Then in another terminal:
cd qa/frontend-tests
pytest                          # all E2E tests
pytest tests/test_dashboard.py  # one file
pytest -k "upload"              # by keyword
```

Set `FRONTEND_URL` in `.env` if the app runs on a non-default port:
```
FRONTEND_URL=http://localhost:3000
```

---

## Unit Tests (Vitest)

Unit test files live in `unit/tests/` but are **run through the frontend's Vitest**
to guarantee a single React instance. No separate `npm install` in the `unit/` folder.

### Run (from WSL)
```bash
# From the frontend directory — discovers both src/ and qa/ unit tests:
cd frontend
npm test

# Or from the unit folder (it delegates automatically):
cd qa/frontend-tests/unit
npm test
```

---

## Test coverage by area

| Area | E2E | Unit |
|---|---|---|
| Login | ✅ | — |
| Register | ✅ | — |
| Forgot password | ✅ | — |
| Dashboard | ✅ | ✅ |
| New upload | ✅ | ✅ |
| Ingestion history | ✅ | ✅ |
| Sidebar navigation | ✅ | — |
| Dark/light theme | ✅ | — |
| StatCard component | — | ✅ |
| SourceHealthTable | — | ✅ |
| Button component | — | ✅ |
| Input component | — | ✅ |
| StatusBadge component | — | ✅ |
