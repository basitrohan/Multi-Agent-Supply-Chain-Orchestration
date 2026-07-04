# SupplyChain Sentinel — Web Console

A browser-based interface for the SupplyChain Sentinel multi-agent backend, built for non-technical users: fill in a form, watch the agent pipeline run, see the results — no API calls, JSON, or terminal commands required.

## What it does

- **Run a stress test** — pick a disruption type, region, severity, and duration; click one button.
- **Watch the agent pipeline** — a live "manifest" shows each of the five agents stamping through as it completes, including a visible retry tag if the Simulation agent escalates to a higher-fidelity re-run.
- **See the results** — risk score, stockout probability, revenue impact, a 12-month forecast chart, and the full generated report, all rendered visually.
- **Swap in your own data** — upload a suppliers or inventory CSV directly from the browser; no command line needed.

## Running it

This is a separate app from the backend — they talk to each other over HTTP. You need **both** running at the same time.

### 1. Start the backend first

From the project root (one level up from this folder):

```bash
source venv/bin/activate      # Windows: venv\Scripts\activate
uvicorn app.main:app --reload
```

Leave this running. It serves the API at `http://localhost:8000`.

### 2. Start the web console

In a **second** terminal window:

```bash
cd frontend
npm install        # first time only
npm run dev
```

Then open the URL it prints (usually `http://localhost:5173`).

### Configuring a different backend address

If your backend runs somewhere other than `http://localhost:8000`, copy `.env.example` to `.env` and set:

```
VITE_API_BASE_URL=http://your-backend-address/api/v1
```

## Building for production

```bash
npm run build
```

This produces a `dist/` folder of static files you can deploy to any static host (Netlify, Vercel, S3 + CloudFront, nginx, etc.) — see the main project's `docs/USER_GUIDE.md` for deployment notes once you're ready to go beyond local use.

## Project structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── StressTestForm.jsx   # scenario input form
│   │   ├── DataPanel.jsx         # current data summary + CSV upload
│   │   ├── AgentManifest.jsx     # the live pipeline visual (signature element)
│   │   ├── ResultsPanel.jsx      # risk/simulation/forecast results + chart
│   │   ├── Card.jsx              # shared card container
│   │   └── RiskBadge.jsx         # color-coded risk level pill
│   ├── lib/
│   │   └── api.js                # all backend API calls live here
│   ├── App.jsx                   # top-level layout and state
│   ├── App.css                   # component styles
│   └── index.css                 # design tokens (colors, type, etc.)
└── .env.example
```

If you want to change colors or fonts, everything is driven by CSS variables defined once at the top of `src/index.css` — change a value there and it updates everywhere.
