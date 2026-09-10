# LandslideAI — Frontend Rebuild

Nothing in your `data/`, `models/`, or the rest of your backend was touched.
Only two things changed:

1. **`backend/app/main.py`** — one endpoint was *added* (nothing removed/edited):
   `GET /api/risk/distribution?date=YYYY-MM-DD` — computes the real LOW…EXTREME
   class breakdown from the dynamic risk raster, using the same thresholds as
   your existing `risk_category()`. This powers the "Dynamic Risk Distribution"
   chart on the Overview page without inventing numbers.

2. **The entire `frontend/` folder** — rebuilt (missing `index.html` /
   `vite.config.js` added, `MonitoringAlerts.jsx` added since it was referenced
   in your spec but missing, and the whole UI re-themed to the Ocean Light Blue
   look).

## Where to put things

```
C:\Users\Naveen\Desktop\YHACK-LANDSLIDE\
├── backend\app\main.py        ← REPLACE with backend/app/main.py from this zip
└── frontend\                  ← REPLACE ENTIRELY with frontend/ from this zip
```

Everything else in your project (`data/`, `models/`, `scripts/`, `app/config.py`,
`requirements.txt`) stays exactly as it is.

## Run it

```powershell
# Terminal 1 — backend
cd C:\Users\Naveen\Desktop\YHACK-LANDSLIDE\backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd C:\Users\Naveen\Desktop\YHACK-LANDSLIDE\frontend
npm install
npm run dev
```

Open the Vite URL (usually `http://localhost:5173`). I ran `npm install` and
`npm run build` in a sandbox against this exact code and it compiles cleanly
(no errors, one expected "chunk size" perf warning from Leaflet/Recharts —
harmless for a demo).

## What was fixed/added, mapped to your spec

- **`index.html`, `vite.config.js`** — were missing, now present.
- **`MonitoringAlerts.jsx`** — was referenced in your architecture but the file
  didn't exist. Built it: pulls real roads/settlements from
  `/api/infrastructure/*`, filters to CRITICAL/VERY HIGH/HIGH, shows
  severity, name, type, risk score, a recommended action, and the
  "not an official warning" footer.
- **`RiskEngine.jsx`** (new) — the 5-stage visual pipeline
  (Terrain → Susceptibility → Rainfall Trigger → Dynamic Risk → Impact),
  used on Overview.
- **`DistributionChart`** in `Charts.jsx` (new) — donut chart of the dynamic
  risk class breakdown, fed by the new `/api/risk/distribution` endpoint.
- **`RiskMap.jsx`** — now also renders roads (capped at 6,000 on-screen for
  performance, KPI still reads 18,515 from `/api/summary`), and clicking any
  landslide point, settlement, or road opens the `LocationPanel` with its
  risk info. Added a `compact` mode so the same component works as the small
  Overview preview map.
- **`Overview.jsx`** — rebuilt to match the spec: hero, 4 KPI cards, mini risk
  map, Monitoring Alerts, Risk Engine, Rainfall Trigger (1/3/7/15/30‑day
  windows when present in the backend's rainfall CSV), and the Dynamic Risk
  Distribution chart.
- **`ModelInsights.jsx`** — now shows a Random Forest vs. Logistic Regression
  comparison table (was only showing one model before), plus the feature
  importance chart.
- **`Infrastructure.jsx`**, **`RiskMapPage.jsx`** — added loading/error states
  so a failed API call shows a message instead of a blank page.
- **`Topbar.jsx` / `App.jsx`** — the "API Online" indicator is now a real
  health check against `/api/health` (polled every 20s), not a static label.
- **Theme** — `index.css` rewritten top to bottom: white cards, deep navy
  text, ocean blue / cyan accents, light blue background with a subtle
  mountain-line motif in the hero, rounded 14–16px cards, soft shadows.

## One thing to double check

`GET /api/risk/distribution` reads the *entire* scenario raster (downsampled
4x) to count pixels per class — same pattern as your existing
`/api/risk/statistics`, so it should be fast, but if your rasters are huge
and you see it lag, tell me and I'll drop the sample resolution further.
