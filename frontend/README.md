# InsightFlow Frontend Documentation

The frontend is a **Next.js 16 application** using the App Router, TypeScript throughout, Tailwind CSS v4, and TanStack React Query for server-state management. It communicates exclusively with the Django REST API.

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [Pages and Routes](#pages-and-routes)
4. [Component Library](#component-library)
5. [API Layer](#api-layer)
6. [Authentication](#authentication)
7. [State Management](#state-management)
8. [Typography and Theming](#typography-and-theming)
9. [TypeScript Types](#typescript-types)
10. [Environment Variables](#environment-variables)
11. [Testing](#testing)
12. [Development Workflow](#development-workflow)

---

## Tech Stack

| Package | Version | Purpose |
|---|---|---|
| Next.js | 16.2.7 | Framework, App Router, SSR |
| React | 19.2.4 | UI library |
| TypeScript | ^5 | Type safety |
| Tailwind CSS | v4 | Utility-first CSS |
| @tailwindcss/postcss | v4 | PostCSS integration |
| @tanstack/react-query | 5.100.14 | Server state, caching, polling |
| next-themes | 0.4.6 | Dark / light mode |
| Vitest | 4.1.8 | Unit testing |
| @testing-library/react | 16.3.2 | Component tests |
| jsdom | 24.1.3 | DOM environment for tests |

**Fonts** (self-hosted via `next/font/google` — no CDN request at runtime):
- **Space Grotesk** — primary sans-serif for all UI text, headings, labels
- **JetBrains Mono** — monospace for data values, IDs, timestamps, table cells

---

## Project Structure

```
frontend/src/
├── api/                    # HTTP clients, one module per backend resource
│   ├── client.ts           # Base fetch wrapper, error normalisation, 401 redirect
│   ├── auth.ts             # login, register, logout, token refresh
│   ├── dashboard.ts        # getDashboardStats — aggregates multiple sources
│   ├── uploads.ts          # uploadFile, getJobStatus (POS-specific)
│   ├── onlineOrders.ts     # triggerOnlineOrders, getOnlineOrdersJobs
│   ├── feedback.ts         # triggerFeedback, getFeedbackJobs
│   └── history.ts          # getIngestionHistory — merges all three sources
│
├── app/                    # Next.js App Router
│   ├── layout.tsx          # Root layout: font variables, metadata, <Providers>
│   ├── page.tsx            # / → redirect to /dashboard
│   ├── providers.tsx       # React Query + next-themes providers
│   ├── globals.css         # CSS variables, Tailwind @theme block, base styles
│   ├── (auth)/             # Unauthenticated routes (no app shell)
│   │   ├── login/
│   │   ├── register/
│   │   └── forgot-password/
│   └── (app)/              # Protected routes (JWT guard in layout.tsx)
│       ├── layout.tsx      # Auth check → redirect to /login if no token
│       ├── dashboard/
│       └── uploads/
│           ├── new/        # 5-step CSV upload wizard
│           └── history/    # Paginated job history + sync trigger buttons
│
├── components/
│   ├── layout/             # AppShell, Sidebar, AuthLayout, Breadcrumb
│   ├── dashboard/          # SourceHealthTable
│   └── ui/                 # 14 reusable primitives (Button, Card, StatCard…)
│
├── hooks/
│   └── useAuth.ts          # Auth state, token helpers, logout
│
├── lib/
│   ├── queryClient.ts      # React Query client factory
│   └── tokenStorage.ts     # localStorage wrappers for JWT tokens + user
│
├── types/
│   └── index.ts            # Shared TypeScript interfaces
│
└── test/
    └── setup.ts            # Vitest global mocks (fetch, localStorage, router)
```

---

## Pages and Routes

### `GET /` → redirect
`src/app/page.tsx` — Immediate redirect to `/dashboard`. No content rendered.

---

### `GET /login`
`src/app/(auth)/login/page.tsx`

Simple email/password login form using `AuthLayout`. On submit, calls `login()` from `api/auth.ts`, stores the access token in localStorage, then navigates to `/dashboard`. Displays server-side error messages inline.

---

### `GET /register`
`src/app/(auth)/register/page.tsx`

Registration form with client-side validation:
- Full name must contain at least two words
- Valid email format
- Password: 8+ characters, uppercase, lowercase, digit, special character

On success, automatically calls `login()` with the same credentials (the register endpoint returns no tokens) and redirects to `/dashboard`.

---

### `GET /forgot-password`
`src/app/(auth)/forgot-password/page.tsx`

Two-step UI: email form (`step="form"`) → confirmation message (`step="sent"`). The password reset is a stub — no backend call is made, the confirmation is shown immediately after submission.

---

### `GET /dashboard`
`src/app/(app)/dashboard/page.tsx`

Overview page showing:
- **4 StatCards** — Jobs Today, Successful Today, Failed Today, Records Ingested
- **SourceHealthTable** — health status of each data source (POS, Online Orders, Inventory, Feedback)

Data is fetched via `getDashboardStats()` which aggregates `/api/ingestion/pos/jobs/` and `/api/ingestion/online-orders/jobs/`, then refetches every **30 seconds**.

```tsx
useQuery({
  queryKey: ["dashboard-stats"],
  queryFn: getDashboardStats,
  staleTime: 0,
  refetchInterval: 30_000,
})
```

---

### `GET /uploads/new`
`src/app/(app)/uploads/new/page.tsx`

Five-step CSV upload wizard for POS files:

| Step | Description |
|---|---|
| 1 — Select | `FileDropzone` accepts `.csv` files; `validate_pos_file_columns` runs client-side column check |
| 2 — Preview | Renders the first 5 data rows as a table using column names from the file |
| 3 — Upload | Calls `uploadPOSFile(file)` → `POST /api/ingestion/pos/` (multipart) |
| 4 — Process | Polls `getJobStatus(jobId)` every **1.5 s** until `status` is `completed` or `failed`; shows a progress bar |
| 5 — Summary | Displays record breakdown: Processed, Skipped (duplicates), Rejected (FK misses), Errors (format) |

The "Already exists" tile on the summary page only appears when `skippedRows > 0`.

---

### `GET /uploads/history`
`src/app/(app)/uploads/history/page.tsx`

Paginated table of all ingestion jobs (POS + Online Orders + Feedback merged and sorted by `createdAt` descending).

**Key features:**
- Click any row → `JobDetailModal` overlay with full job metadata
- "Sync Feedbacks" button → `POST /api/ingestion/feedback/trigger/` (invalidates history cache on success)
- "Sync Online Orders" button → `POST /api/ingestion/online-orders/trigger/` (same)
- `Pagination` component for page navigation
- Status badges: pending / processing / completed / failed

**JobDetailModal fields:**
- Status badge, source type
- Job ID (monospace)
- File name (POS only)
- Records processed / total
- Skipped duplicates, rejected (FK misses), format errors
- Error message (if any)
- Started at / last updated

---

## Component Library

### Layout Components (`components/layout/`)

#### `AppShell`
Wraps every authenticated page. Renders the `Sidebar` (collapsible on mobile), `Header` (hamburger + breadcrumb + `ThemeToggle`), and main content area. Manages `sidebarOpen` state.

```tsx
<AppShell>
  {children}
</AppShell>
```

#### `Sidebar`
Fixed-position navigation with two sections: **OPERATIONS** (Dashboard, New Upload, Ingestion History) and **ANALYTICS** (Metabase external link).

The "Ingestion history" link has a dynamic job-count badge driven by a `useQuery` call that reuses the same `["ingestion-history", 1]` cache key as the history page, so no extra network request is made when both are mounted simultaneously.

```tsx
const { data: historyMeta } = useQuery({
  queryKey: ["ingestion-history", 1],
  queryFn: () => getIngestionHistory(1),
  staleTime: 60_000,
});
```

At the bottom, the user's avatar, name, and role are shown. Clicking triggers logout.

#### `AuthLayout`
Split layout for auth pages: decorative brand panel on the left (large screens) with a mesh-gradient animation and trust points; form area on the right.

#### `Breadcrumb`
Reads `usePathname()` and renders a crumb trail. Path segments are mapped to human-readable labels.

---

### UI Primitives (`components/ui/`)

| Component | Key Props | Notes |
|---|---|---|
| `AlertBanner` | `variant`, `message`, `onDismiss?` | `info` / `success` / `warning` / `error` variants |
| `Button` | `variant`, `size`, `loading?`, `disabled?` | Primary = green, secondary = gray, danger = red, ghost = transparent |
| `Card` | `title?`, `className?` | Rounded surface with optional titled header |
| `EmptyState` | `title`, `description?`, `action?` | Centered icon + message placeholder |
| `FileDropzone` | `onFile`, `accept?`, `disabled?` | Drag-and-drop with file-size display |
| `Input` | `label?`, `error?`, `...inputAttrs` | Form field with inline error |
| `LoadingSkeleton` | `rows?`, `className?` | Animated gray bar placeholders |
| `Modal` | `children` | Accessible dialog wrapper |
| `Pagination` | `page`, `totalPages`, `onPageChange` | Previous / Next; disabled at boundaries |
| `Select` | standard select attrs | Styled dropdown |
| `StatCard` | `label`, `value`, `icon`, `iconBg?`, `trend?` | Dashboard metric tile |
| `StatusBadge` | `status` | Color-coded dot + text for job/source statuses |
| `ThemeToggle` | `className?` | Sun/moon icon; hydration-safe (mounts after client load) |
| `TopLoader` | — | Page-transition progress bar; fires on `pathname` change |

---

## API Layer

All API modules live in `src/api/`. Every module imports from `client.ts` for authenticated requests.

### `client.ts` — Base HTTP client

```typescript
apiFetch<T>(path: string, options?: RequestInit & { skipAuth?: boolean }): Promise<T>
```

- Prepends `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000/api`)
- Injects `Authorization: Bearer <token>` from localStorage
- On **401**, hard-redirects to `/login`
- Parses DRF error shapes (`detail`, `non_field_errors`, field map) into a single readable string
- Throws `ApiError(status, detail)` on non-2xx responses

### `auth.ts`

| Function | Endpoint | Auth |
|---|---|---|
| `login(payload)` | `POST /auth/login/` | No |
| `register(payload)` | `POST /auth/register/` | No |
| `logout()` | `POST /auth/logout/` | Yes |
| `refreshToken(token)` | `POST /auth/token/refresh/` | No |
| `forgotPassword(email)` | — (stub) | — |

### `uploads.ts` — POS file upload and polling

| Function | Endpoint | Notes |
|---|---|---|
| `uploadFile(file, sourceType)` | `POST /ingestion/pos/` | Multipart FormData; stores `{ fileName, sourceType }` in client-side `JOB_META` Map |
| `getJobStatus(jobId)` | `GET /ingestion/{jobId}/status/` | Maps `running → processing`; surfaces `skipped_duplicates` from `error_report` |
| `uploadPOSFile(file)` | — | Wrapper for `uploadFile(file, "pos")` |

### `history.ts`

`getIngestionHistory(page?)` calls three endpoints in parallel, merges the results, and sorts by `createdAt` descending:

```typescript
const [posData, ooData, feedbackJobs] = await Promise.all([
  apiFetch<PosJobsPage>(`/ingestion/pos/jobs/?page=${page}`),
  getOnlineOrdersJobs(page),
  getFeedbackJobs(),
]);
```

Returns `PaginatedResponse<IngestionJob>` with a combined `count`.

### `onlineOrders.ts`

| Function | Endpoint |
|---|---|
| `triggerOnlineOrders()` | `POST /ingestion/online-orders/trigger/` |
| `getOnlineOrdersJobs(page?)` | `GET /ingestion/online-orders/jobs/?page={page}` |
| `getOnlineOrdersJobStatus(jobId)` | `GET /ingestion/online-orders/{jobId}/status/` |

Each raw `OnlineOrdersJob` is mapped to the canonical `IngestionJob` shape via `toIngestionJob()`.

### `feedback.ts`

| Function | Endpoint |
|---|---|
| `triggerFeedback()` | `POST /ingestion/feedback/trigger/` |
| `getFeedbackJobs()` | `GET /ingestion/feedback/jobs/` |
| `getFeedbackJobStatus(jobId)` | `GET /ingestion/feedback/jobs/{jobId}/status/` |

---

## Authentication

### Token Storage (`lib/tokenStorage.ts`)

Tokens are stored in `localStorage` under fixed keys:

| Key | Contents |
|---|---|
| `insightflow_token` | JWT access token (1-day lifetime) |
| `insightflow_refresh_token` | JWT refresh token (7-day lifetime) |
| `insightflow_user` | Serialised `User` object |

Helper functions: `getToken`, `setToken`, `clearToken`, `getRefreshToken`, `setRefreshToken`, `clearAllTokens`, `getStoredUser<T>`, `setStoredUser`, `clearStoredUser`.

### `useAuth` Hook (`hooks/useAuth.ts`)

```typescript
const { user, isAuthenticated, saveToken, setUser, logout } = useAuth();
```

- Initialises `user` state from `localStorage` on first render
- `isAuthenticated` — true if a stored access token exists
- `logout()` — calls `api/auth.logout()`, clears all localStorage keys, redirects to `/login`

### Route Protection

The layout at `src/app/(app)/layout.tsx` calls `getToken()` server-side equivalent and redirects to `/login` when absent. All pages under `(app)/` are protected.

There is no automatic silent token refresh — a 401 response in `apiFetch` triggers a hard redirect to `/login`.

---

## State Management

### React Query Client (`lib/queryClient.ts`)

```typescript
new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,  // 1 minute
      retry: 1,
    },
  },
})
```

### Query Key Conventions

| Key | Used by |
|---|---|
| `["dashboard-stats"]` | `/dashboard` page |
| `["ingestion-history", page]` | `/uploads/history` + Sidebar badge |
| `["job-status", jobId]` | Upload wizard polling |

### Polling

The upload wizard polls job status every 1.5 seconds:

```typescript
useQuery({
  queryKey: ["job-status", jobId],
  queryFn: () => getJobStatus(jobId!),
  enabled: Boolean(jobId),
  refetchInterval: (data) =>
    data?.status === "completed" || data?.status === "failed" ? false : 1500,
})
```

### Cache Invalidation

After a sync trigger (Feedback or Online Orders), `queryClient.invalidateQueries({ queryKey: ["ingestion-history"] })` fires to refresh the history table and sidebar badge simultaneously.

---

## Typography and Theming

### Fonts

Fonts are loaded by Next.js at build time and self-hosted — no runtime CDN request is needed.

```typescript
// src/app/layout.tsx
import { Space_Grotesk, JetBrains_Mono } from "next/font/google";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});
```

Both CSS variables are applied to `<html>` so they cascade everywhere.

### Tailwind `@theme` block (`globals.css`)

```css
@theme {
  --font-sans: var(--font-space-grotesk), "Space Grotesk", sans-serif;
  --font-mono: var(--font-jetbrains-mono), "JetBrains Mono", monospace;
}
```

### Font Usage Rules

| Context | Font | Class |
|---|---|---|
| All body text, headings, UI labels | Space Grotesk | default (`font-sans`) |
| Table cells (`<td>`), code, IDs, metrics, timestamps | JetBrains Mono | applied via CSS selector |
| Tabular numbers (aligned digits in tables) | JetBrains Mono | `font-variant-numeric: tabular-nums` |

```css
td, code, kbd, pre, .tabular-nums {
  font-family: var(--font-jetbrains-mono), "JetBrains Mono", monospace;
  font-variant-numeric: tabular-nums;
}
```

### Typography Scale

| Use | Class |
|---|---|
| Page title (h1) | `text-3xl font-semibold tracking-tight` |
| Section heading (h2) | `text-xl font-semibold tracking-tight` |
| Dashboard stat value | `text-5xl font-semibold tracking-tight` |
| Summary tile value | `text-3xl font-semibold tracking-tight` |
| Body text | `text-sm font-medium` |
| Muted label | `text-xs text-gray-500` |

### CSS Variables (color tokens)

```css
/* Light mode (:root) */
--bg:         #f9fafb   /* Page background */
--surface:    #ffffff   /* Card/panel surface */
--border:     #e5e7eb
--text:       #111827
--text-muted: #6b7280

/* Dark mode (.dark) */
--bg:         #0f172a   /* Slate 950 */
--surface:    #1e293b   /* Slate 800 */
--border:     #334155
--text:       #f1f5f9
--text-muted: #94a3b8
```

### Dark Mode

Implemented via `next-themes` with class-based toggling (`attribute="class"`). The Tailwind custom variant `@custom-variant dark (&:where(.dark, .dark *))` overrides the default media-query behaviour so that only the `.dark` class controls dark styles. Default theme follows the system preference.

---

## TypeScript Types

All shared interfaces live in `src/types/index.ts`.

```typescript
interface User {
  id: string;
  email: string;
  name: string;
  role: "admin" | "analyst" | "viewer";
  createdAt: string;
}

type IngestionStatus = "pending" | "processing" | "completed" | "failed";
type SourceType = "pos" | "inventory" | "online_orders" | "feedback";

interface IngestionJob {
  id: string;
  fileName: string;
  sourceType: SourceType;
  status: IngestionStatus;
  recordsTotal: number | null;
  recordsProcessed: number | null;   // valid rows inserted
  skippedRows?: number;              // duplicate rows already in DB
  rejectedRows?: number;             // FK misses (unknown store/cashier/product)
  errorRows?: number;                // CSV format errors
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

interface DataSource {
  id: string;
  name: string;
  type: string;
  lastSyncAt: string | null;
  status: "healthy" | "degraded" | "down";
}

interface DashboardStats {
  jobsToday: number;
  jobsSuccessToday: number;
  jobsFailedToday: number;
  recordsIngested: number;
  sources: DataSource[];
}

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
```

---

## Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Yes (prod) | `http://localhost:8000/api` | Backend API base URL |

Create `frontend/.env.local` for local development:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080/api
```

For production (Docker Compose), this is injected into the container via the `environment` block in `docker-compose.yml`.

---

## Testing

Tests use **Vitest** with **@testing-library/react** and JSDOM. Global mocks for `fetch`, `localStorage`, `next/navigation`, and `next-themes` are set up in `src/test/setup.ts`.

```bash
cd frontend
npm run test          # run once
npm run test:watch    # watch mode
npm run test:coverage # with coverage report
```

Test files live alongside the code they test:
- `src/api/__tests__/`
- `src/components/ui/__tests__/`
- `src/components/dashboard/__tests__/`
- `src/app/(app)/dashboard/__tests__/`
- `src/hooks/__tests__/`

---

## Development Workflow

```bash
cd frontend
npm install
npm run dev           # http://localhost:3000, hot reload
npm run build         # production build
npm run start         # serve production build
npm run lint          # ESLint
npm run test          # Vitest unit tests
```

### Adding a New API Source

1. Create `src/api/<source>.ts` — export `trigger<Source>()` and `get<Source>Jobs()` following the pattern in `feedback.ts`
2. Add converter `toIngestionJob(raw)` that maps the backend shape to `IngestionJob`
3. Import `get<Source>Jobs` in `src/api/history.ts` and add it to the `Promise.all` merge
4. Add trigger `useMutation` to `src/app/(app)/uploads/history/page.tsx`

### Adding a New Page

1. Create `src/app/(app)/<route>/page.tsx`
2. Add the route to `NAV` in `Sidebar.tsx` with the appropriate icon
3. Add a breadcrumb label mapping in `Breadcrumb.tsx`
