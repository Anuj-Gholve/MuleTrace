# Graph-Based Financial Crime Detection Engine

> **Hackathon Project** — Money Muling Detection using Graph Theory

A production-ready web application that analyzes transaction data to detect financial crime patterns (cycles, smurfing, shell networks) using graph algorithms, and presents results through an interactive dashboard with graph visualization.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Frontend (React)                       │
│  ┌──────────┐  ┌──────────────────┐  ┌────────────────────┐  │
│  │  Upload   │  │  Results Table   │  │  Cytoscape.js      │  │
│  │  (CSV)    │──│  (Dashboard)     │  │  Graph Viz         │  │
│  └──────────┘  └──────────────────┘  └────────────────────┘  │
│           │            ▲                       ▲              │
│           └────────────┼───────────────────────┘              │
│                        │  JSON Response                       │
└────────────────────────┼─────────────────────────────────────┘
                         │  HTTP POST /api/upload
┌────────────────────────┼─────────────────────────────────────┐
│                    Backend (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │               Detection Pipeline                         │ │
│  │  1. Parse CSV → Build Adjacency Lists                    │ │
│  │  2. Precompute Metrics (degree, sorted txns)             │ │
│  │  3. Cycle Detection (DFS, length 3–5)                    │ │
│  │  4. Smurfing Detection (72h sliding window)              │ │
│  │  5. Shell Network Detection (DFS depth 4)                │ │
│  │  6. Suspicion Scoring (additive, capped 100)             │ │
│  │  7. Ring Risk Scoring (avg × multiplier)                 │ │
│  │  8. JSON Assembly                                        │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer     | Technology                |
|-----------|---------------------------|
| Backend   | Python 3.10+, FastAPI     |
| Analysis  | NetworkX, Pandas          |
| Frontend  | React (Vite), Tailwind    |
| Graph Viz | Cytoscape.js              |

---

## Installation & Setup

### Prerequisites

- Python 3.10+ with `pip`
- Node.js 18+ with `npm`

### Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
# Server runs at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# App runs at http://localhost:5173
```

The frontend development server proxies `/api/*` requests to the backend.

---

## CSV Format (Strict)

| Column         | Type   | Format                   |
|----------------|--------|--------------------------|
| transaction_id | String | e.g. `TXN_001`           |
| sender_id      | String | e.g. `ACC_00123`         |
| receiver_id    | String | e.g. `ACC_00456`         |
| amount         | Float  | e.g. `5000.00`           |
| timestamp      | String | `YYYY-MM-DD HH:MM:SS`   |

A sample file is provided at `sample_transactions.csv`.

---

## Algorithm Complexity Analysis

| Step | Algorithm | Complexity | Notes |
|------|-----------|-----------|-------|
| 1. Parse CSV | Single pass | **O(E)** | E = edges/transactions |
| 2. Precompute Metrics | Sort per account | **O(E log E)** | Sorting timestamps |
| 3. Cycle Detection | DFS per node, max depth 5 | **O(V · d⁵)** | d = avg out-degree; pruned |
| 4. Smurfing Detection | Two-pointer sliding window | **O(E)** | Per account, sorted transactions |
| 5. Shell Networks | DFS per node, max depth 4 | **O(V · d⁴)** | Intermediate degree filter prunes heavily |
| 6. Suspicion Scoring | Set lookups | **O(V)** | Simple additive |
| 7. Ring Risk | Iterate rings | **O(R · M)** | R = rings, M = avg members |

**Overall: O(E log E + V · d⁵)** — practical for 10,000+ transactions under 30 seconds.

---

## Suspicion Score Methodology

Scores are additive per account, capped at 100:

| Pattern       | Points | Rationale |
|---------------|--------|-----------|
| Cycle member  | +40    | Direct circular fund flow — strongest indicator |
| Fan-in (72h)  | +25    | Aggregating from 10+ sources rapidly |
| Fan-out (72h) | +25    | Dispersing to 10+ targets rapidly |
| Shell chain   | +20    | Layering through low-activity intermediaries |

### Ring Risk Score

```
risk_score = avg(member_suspicion_scores) × pattern_multiplier
```

| Pattern     | Multiplier | Rationale |
|-------------|------------|-----------|
| Cycle       | 1.3×       | Highest structural confidence |
| Shell chain | 1.2×       | Moderate confidence |
| Smurfing    | 1.1×       | Behavioral pattern |

---

## JSON Output Schema

```json
{
  "suspicious_accounts": [
    {
      "account_id": "ACC_00123",
      "suspicion_score": 87.5,
      "detected_patterns": ["cycle_length_3"],
      "ring_id": "RING_001"
    }
  ],
  "fraud_rings": [
    {
      "ring_id": "RING_001",
      "member_accounts": ["ACC_00123"],
      "pattern_type": "cycle",
      "risk_score": 95.3
    }
  ],
  "summary": {
    "total_accounts_analyzed": 500,
    "suspicious_accounts_flagged": 15,
    "fraud_rings_detected": 4,
    "processing_time_seconds": 2.3
  }
}
```

- `suspicion_score`: 0–100, sorted descending, 1 decimal
- `ring_id`: never null
- Empty arrays if no detections

---

## Project Structure

```
/
├── backend/
│   ├── main.py               # FastAPI app (upload endpoint, CORS)
│   ├── detection_engine.py   # Core detection algorithms (Steps 1–8)
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── public/
│   │   └── vite.svg
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── index.css
│       └── components/
│           ├── FileUpload.jsx
│           ├── ResultsDashboard.jsx
│           └── GraphVisualization.jsx
├── sample_transactions.csv   # Test data
├── example_output.json       # Expected output shape
└── README.md
```

---

## Deployment

### Quick Start (Development)

```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
python main.py

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

### Production Build

```bash
# Build frontend
cd frontend
npm run build   # output → frontend/dist/

# Serve with FastAPI (add StaticFiles mount) or any web server
# Backend: uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## License

Hackathon project — MIT License.
