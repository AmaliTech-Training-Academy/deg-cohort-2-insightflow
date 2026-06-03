# Frontend Unit Tests

Test files live here. They are **discovered and run by the frontend's Vitest runner** —
not by a separate Node project in this folder. This avoids the dual-React-instance
problem that occurs when `@testing-library/react` and the frontend pages load different
copies of React.

## Structure

```
unit/tests/
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

All imports use `@/*` which resolves to `frontend/src/*` (configured in
`frontend/vitest.config.mts`).

## How to run (from WSL)

```bash
# Run all unit tests (frontend inline + QA unit tests):
cd frontend
npm test

# Watch mode:
npm run test:watch

# Or from this folder (delegates to frontend runner):
npm test
```

## Why here and not in frontend/src?

QA-owned tests live in the `qa/` tree so they are managed alongside the
E2E tests by the QA team, while still sharing the frontend's node_modules
and Vitest setup.
