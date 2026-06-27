# oh-my-class Design System

## 1. Atmosphere & Identity

oh-my-class feels like a calm teacher command center: clear enough for busy classroom planning, structured enough to trust an AI pipeline, and quiet enough not to compete with lesson content. The signature is staged assurance: every workflow surface shows where the teaching pack is, what needs the teacher's decision, and what evidence the system used.

## 2. Color

### Palette

| Role | Token | Light | Dark | Usage |
|------|-------|-------|------|-------|
| Surface/primary | `--color-background` | `#ffffff` | `#0f172a` | Page background |
| Surface/elevated | `--color-card` | `#ffffff` | `#1e293b` | Cards, sidebars, modals |
| Surface/muted | `--color-muted` | `#f1f5f9` | `#1e293b` | Event logs, subtle panels |
| Text/primary | `--color-foreground` | `#0f172a` | `#f8fafc` | Headlines, body |
| Text/secondary | `--color-muted-foreground` | `#64748b` | `#94a3b8` | Metadata, helper copy |
| Border/default | `--color-border` | `#e2e8f0` | `#334155` | Dividers, cards, outlines |
| Input/default | `--color-input` | `#e2e8f0` | `#334155` | Form controls |
| Accent/primary | `--color-primary` | `#4f46e5` | `#818cf8` | Primary actions, focus, active step |
| Accent/on-primary | `--color-primary-foreground` | `#ffffff` | `#0f172a` | Text on primary actions |
| Status/error | `--color-destructive` | `#ef4444` | `#ef4444` | Destructive actions, failures |
| Status/on-error | `--color-destructive-foreground` | `#ffffff` | `#ffffff` | Text on destructive actions |

### Rules

- Use the indigo accent only for actions, active progress, and links.
- Status color is semantic, not decorative: failed/cancelled states use destructive, awaiting/queued states use muted surfaces.
- No new raw color values in UI code. Add a token here and in `apps/web/src/app/globals.css` first.

## 3. Typography

### Scale

| Level | Size | Weight | Line Height | Tracking | Usage |
|-------|------|--------|-------------|----------|-------|
| H1 | 30px / `text-3xl` | 700 | 1.2 | -0.01em | Run detail title |
| H2 | 24px / `text-2xl` | 700 | 1.25 | -0.01em | Page title |
| H3 | 18px / `text-lg` | 600 | 1.4 | 0 | Card and section title |
| Body | 16px / `text-base` | 400 | 1.6 | 0 | Main copy |
| Body/sm | 14px / `text-sm` | 400/500 | 1.5 | 0 | Controls, metadata |
| Caption | 12px / `text-xs` | 500/600 | 1.4 | 0.02em | Badges, event labels |

### Font Stack

- Primary: `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`.
- Mono: `"SF Mono", "Cascadia Code", "Fira Code", monospace`.

### Rules

- Body text never below `text-sm` except compact badges.
- Use tabular/mono styling for ids, hashes, and event sequence-like data.
- Prefer sentence case for gate headings and actions.

## 4. Spacing & Layout

### Base Unit

All spacing derives from 4px via Tailwind spacing tokens.

| Token | Value | Usage |
|-------|-------|-------|
| `gap-1` / `p-1` | 4px | Icon-label gaps |
| `gap-2` / `p-2` | 8px | Compact buttons, badges |
| `gap-3` / `p-3` | 12px | Dense list rows |
| `gap-4` / `p-4` | 16px | Default panel padding |
| `gap-6` / `p-6` | 24px | Cards and modal bodies |
| `gap-8` | 32px | Section groups |
| `p-8` | 32px | Run detail page padding |

### Grid

- Max content width: `1280px` for dashboard content.
- Dashboard shell: fixed 256px sidebar plus flexible main content.
- Breakpoints: Tailwind defaults (`sm`, `md`, `lg`, `xl`, `2xl`).

### Rules

- Use `min-h-[100dvh]` for viewport-height app shells going forward.
- Use CSS grid for multi-column status/preview layouts; avoid percentage flex math.
- Mobile gates stack vertically; preview panes must not require horizontal scroll.

## 5. Components

### Button

- **Structure**: shadcn-style `Button` with `variant` and `size` props.
- **Variants**: default, secondary, destructive, outline, ghost, link.
- **Spacing**: default height `h-10`, horizontal padding `px-4`.
- **States**: hover shifts background opacity; focus uses `--color-ring`; disabled uses opacity and disables pointer events.
- **Accessibility**: native `<button>` unless `asChild` wraps a semantic link.
- **Motion**: color transition only.

### Card / panel

- **Structure**: `Card`, `CardHeader`, `CardTitle`, `CardContent`.
- **Variants**: default bordered surface; muted inline panel for logs and gate details.
- **Spacing**: `p-6` for cards, `p-4` for compact panels.
- **States**: interactive cards add hover surface shift, not heavy shadow.
- **Accessibility**: use semantic headings inside panels.
- **Motion**: mount fade/translate only when useful.

### Gate modal shell

- **Structure**: header with gate name/status, body mapped by gate type, footer with primary/secondary actions.
- **Variants**: clarification, contract confirmation, search plan confirmation, blueprint approval, content approval.
- **Spacing**: `p-6` body, `gap-4` between decision groups.
- **States**: loading disables primary action; backend errors render inline.
- **Accessibility**: labelled dialog title, keyboard-reachable controls, no `alert()`.
- **Motion**: overlay/content fade only.

### Stage progress

- **Structure**: ordered stage list with status badge and compact description.
- **Variants**: pending, active, blocked, complete, failed.
- **Spacing**: `gap-3` row, `p-3` row body.
- **States**: active uses primary accent; failed uses destructive text.
- **Accessibility**: ordered list communicates sequence; current stage labelled in text.
- **Motion**: no layout animation.

## 6. Motion & Interaction

| Type | Duration | Easing | Usage |
|------|----------|--------|-------|
| Micro | 100-150ms | ease-out | Button press, hover |
| Standard | 200ms | ease-in-out | Tab switch, modal state |
| Emphasis | 300-400ms | cubic-bezier(0.16, 1, 0.3, 1) | Panel entry |

### Rules

- Animate only `transform` and `opacity`; color transitions are acceptable for controls.
- Every interactive element needs hover, active, focus, disabled/loading states where relevant.
- Respect reduced motion; keep motion non-essential.

## 7. Depth & Surface

### Strategy

Use borders plus tonal shifts. Existing shadcn cards keep `shadow-sm`, but new V2 workflow surfaces should prefer borders and muted panels over decorative shadows.

| Type | Value | Usage |
|------|-------|-------|
| Default border | `1px solid var(--color-border)` | Cards, dialogs, rows |
| Muted fill | `bg-muted` | Logs, status panels, skeletons |
| Elevated surface | `bg-card` | Sidebar, modal, preview frame |

### Rules

- Do not add arbitrary `box-shadow` values.
- Use `rounded-lg` for main panels, `rounded-md` for controls, `rounded-full` only for compact status badges.
