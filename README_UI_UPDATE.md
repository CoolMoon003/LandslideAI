# LandslideAI — UI update package

Scope: frontend visual redesign only. Nothing in `backend/`, the data
pipeline, or your existing API contracts was touched.

## How to apply

Drop these files into your project at the SAME paths, overwriting what's
there:

```
frontend/src/App.jsx                              (replace)
frontend/src/index.css                            (replace)
frontend/src/components/TopNav.jsx                (new file)
frontend/src/components/RiskEngine.jsx            (replace)
frontend/src/components/MonitoringAlerts.jsx       (replace)
frontend/src/components/MetricCard.jsx            (replace)
frontend/src/components/RiskDistributionBars.jsx  (new file)
frontend/src/pages/Overview.jsx                   (replace)
frontend/src/assets/hero-mountains.svg            (new file)
```

Then DELETE these two (no longer used, replaced by TopNav.jsx):

```
frontend/src/components/Sidebar.jsx
frontend/src/components/Topbar.jsx
```

## What changed

1. **Sidebar -> top nav.** New `TopNav.jsx` combines the brand mark, the
   4 page links, the scenario date picker, refresh button and the
   API online/offline badge into one horizontal bar, matching the
   reference screenshot's layout.

2. **Hero section fixed + restyled.** Your `Overview.jsx` was already
   using `.pill`, `.primary`, `<h2>`, and `<em>` classes/tags that had
   **no matching CSS** — they were rendering unstyled text. `index.css`
   now defines all of them, plus a photographic-style background: an
   original layered-mountain SVG illustration (`hero-mountains.svg`)
   under the same blue gradient tint your app already uses elsewhere.
   I did not embed a real photo pulled from a web image search into your
   code, since the licensing on those isn't something I can clear for you —
   this SVG is original and safe to ship. If you have your own licensed
   drone/satellite shot of Meghalaya, swap the `background-image` url in
   `.hero` (index.css) for that image and it'll look even better.

3. **KPI cards now carry icons** (mountain / road / home / alert-triangle),
   with tone-tinted icon backgrounds (`MetricCard.jsx`).

4. **Dynamic risk distribution** is now a 6-column horizontal bar row
   (`RiskDistributionBars.jsx`) matching the reference image, instead of
   the previous donut chart. Same `/api/risk/distribution` data shape.

5. **Monitoring alerts** get a severity-colored left border and an
   action tag ("Prioritize monitoring" for Very High/Extreme, "Review
   exposure" for High).

6. **Risk engine pipeline** now shows numbered circles (01-05) instead
   of plain icons, matching the reference.

7. Removed all dead `.sidebar` / `.topbar` CSS left over from the old
   layout.

## Verification done here (and why a full build wasn't possible)

I could not run `npm run build` successfully in my own sandbox — your
`node_modules` was `npm install`-ed on Windows, and it ships
platform-specific native binaries (`@rollup/rollup-win32-x64-msvc`,
`@esbuild/win32-x64`) that don't run on my Linux container. That's an
environment mismatch, not a bug in this code.

What I verified instead, with tools that don't need native binaries:
- Parsed every changed/new `.jsx`/`.js` file with `@babel/parser`
  (JSX-aware) — all 17 touched files parse with zero syntax errors.
- Walked every relative `import ... from "./..."` in those files and
  confirmed the target file actually exists on disk — zero missing
  imports.
- Confirmed `index.css` has balanced braces (288 open / 288 close).

**You should still run `npm run build` (or `npm run dev`) yourself once**
before the demo, on your own machine, to catch anything environment-specific
(e.g. Leaflet CSS import order, Vite dev-server proxy) that only shows up
at runtime rather than at parse time.
