# AGENTS.md - NammaFare Project Guidelines & Architecture

## 1. Project Overview & Purpose

**NammaFare** is a Chennai-focused, multimodal transport journey planner designed to help commuters discover, compare, and navigate public and intermediate transit options across the Chennai metropolitan region.

The core goal of NammaFare is to provide transparent, accurate fare estimations and travel time predictions (ETA) tailored to Chennai's unique transit ecosystem, empowering users to make cost-effective and time-efficient commuting decisions.

---

## 2. Technology Stack

### 2.1 Frontend
- **Framework:** Next.js (App Router)
- **UI Library:** React
- **Styling:** Tailwind CSS (utility-first, responsive, accessible)
- **State Management & Data Fetching:** React hooks, Fetch API / SWR
- **Icons & UI Utilities:** Lucide React (or equivalent lightweight SVG icons), clsx, tailwind-merge
- *Note on Mapping:* Interactive mapping (Leaflet / OpenStreetMap) is deferred to post-MVP. The MVP focuses on a crisp, responsive card-based comparison and step-by-step itinerary breakdown.

### 2.2 Backend
- **Language:** Python (3.11+)
- **Framework:** FastAPI
- **Data Validation & Serialization:** Pydantic v2
- **Server:** Uvicorn
- **Package & Dependency Management:** Virtual environment (`venv`) with `pip` / `requirements.txt` or `pyproject.toml`

### 2.3 Post-MVP Geospatial & Mapping Roadmap
- **Map Renderer:** Leaflet (`react-leaflet` or vanilla Leaflet in client-side Next.js components)
- **Map Tiles:** OpenStreetMap (OSM) standard tile servers
- **Geocoding & Transit GIS:** Chennai transit GTFS, OSM Nominatim/OSRM integration

---

## 3. Supported Chennai Transport Modes & Data Classification

NammaFare encompasses all seven agreed Chennai transit modes in the backend scope, with an explicit distinction between **verified official fare data** and **indicative estimates**:

### 3.1 Verified Official Data (Published Fare Tables)
1. **MTC Bus:** Metropolitan Transport Corporation bus network
   - *Ordinary / White-Board Buses:* Stage-based fare chart (₹5 to ₹14+), with statutory zero-fare for women under *Vidiyal Payana Thittam*.
   - *Express / Deluxe / AC Services:* Official fixed stage-fare tables (chargeable for all commuters).
2. **Chennai Metro (CMRL):** Blue Line & Green Line
   - Official station-to-station distance slabs (standard fare ₹10, ₹20, ₹30, ₹40, ₹50).
3. **Suburban Train (Southern Railway / Chennai Suburban & MRTS):**
   - Official Indian Railways unreserved second-class fare stages (e.g., ₹5 base up to 20 km, ₹10 up to 45 km).

### 3.2 Indicative & Calibrated Estimates (Street / Market Rates)
4. **Auto Rickshaw:** Calibrated Chennai daytime estimates based on minimum meter base (₹25–₹30 for first 1.8 km) + per-km slab (₹12–₹15/km), with clear indicative disclaimer.
5. **Share Auto:** Standard fixed-corridor and arterial feeder hop rates (e.g., ₹15–₹30 flat stages across corridors like Guindy, Koyambedu, Vadapalani, Ashok Pillar).
6. **Taxi / Cab:** Indicative point-to-point aggregator/cab daytime estimates (base fare + per-km rate).
7. **Walking:** Pedestrian legs for first-mile, last-mile, and inter-modal transfers (assumed walking speed of ~4.5–5 km/h, zero cost).

---

## 4. Confirmed MVP User Workflow (Two-Page Architecture)

The MVP is strictly scoped to a streamlined two-page flow with no extraneous controls:

```
[ Page 1: Journey Search ] ──▶ User submits parameters ──▶ [ Page 2: Route Comparison ]
  - Source (Origin)                                         - Editable Cost / Time sorting controls
  - Destination                                             - Editable Male / Female toggle
  - Lowest Cost / Least Time preference                     - Multimodal journey cards
  - Male / Female toggle (Male default)                     - Expandable fare & leg breakdown
  - "Search Routes" button                                  - Total fare & ETA per journey
```

### 4.1 Page 1: Journey Search
- **Source (Origin) Input:** Text input with Chennai locality/station autocomplete or suggestions.
- **Destination Input:** Text input with Chennai locality/station autocomplete or suggestions.
- **Preference Selector:** Toggle/selector for **Lowest Cost** vs **Least Time**.
- **Gender Toggle:** **Male** or **Female** only (strictly no "Other" option in MVP). **Default value: Male**.
- **Search Trigger:** "Search Routes" button submitting query parameters to Page 2 / backend routing engine.
- *Explicit MVP Exclusions:*
  - No gender "Other" option.
  - No transport mode selector or checkboxes (all applicable modes considered automatically).
  - No departure/arrival time picker (assumes immediate/daytime travel).
  - No interactive map.

### 4.2 Page 2: Route Comparison
- **Top Bar Controls (Fully Editable):**
  - **Cost / Time Sorting Switch:** Toggle between **Lowest Cost** and **Least Time** to instantly reorder results.
  - **Male / Female Toggle:** Editable toggle on the results page allowing users to switch gender and instantly see reactive fare re-calculations (especially MTC ordinary bus zero-fare).
- **Multimodal Journey Cards:**
  - Distinct cards for each viable journey option (e.g., Suburban Train + Bus, Metro + Share Auto, Direct Bus).
  - **Total Estimated Fare (₹)** prominently displayed.
  - **Total Travel Time & ETA** prominently displayed.
  - Leg summary preview (e.g., `Walk 5m` ➜ `MTC Bus 18A` ➜ `Walk 4m`).
- **Expandable Fare & Leg Breakdown:**
  - Per-leg mode, line/route number, boarding and alighting stop names.
  - Individual leg fare with transparent notes (e.g., *₹0 - MTC Ordinary [Vidiyal Payana Thittam]* or *₹5 - Suburban 2nd Class*).
  - Clear visual badge for verified fares vs indicative estimates.
- *Explicit MVP Exclusions:*
  - No interactive map on MVP (reserved for post-MVP).

---

## 5. Fare Engine & Transparency Rules

### 5.1 Gender-Based MTC Fare Rule (*Vidiyal Payana Thittam*)
- Under the Tamil Nadu Government scheme (*Vidiyal Payana Thittam*), **women travel free of charge** in standard **MTC Ordinary (White-Board) buses**.
- **Calculation Logic:**
  - When gender is **Female**: Fare for ordinary MTC bus legs is strictly **₹0**.
  - When gender is **Male** (Default): Standard distance-based MTC stage fare table applies (₹5, ₹8, ₹10, ₹12, ₹14+).
  - Express, Deluxe, and AC services remain chargeable for both genders.

### 5.2 Fare Transparency Badging
- Every leg and total fare must provide clear transparency:
  - **[Verified]**: For CMRL Metro, MTC Bus, and Southern Railway Suburban Train legs backed by official government fare tables.
  - **[Estimated]**: For Auto Rickshaw, Share Auto, and Taxi legs with indicative pricing disclaimers.

---

## 6. API Integration Conventions

### 6.1 Communication & Protocols
- RESTful HTTP APIs with JSON payloads.
- Base path prefix: `/api/v1`.
- CORS configured in FastAPI to allow requests from the Next.js frontend origin.

### 6.2 Standard MVP Endpoints

#### `GET /api/v1/health`
Healthcheck endpoint returning `{ "status": "ok" }`.

#### `GET /api/v1/places?q={query}`
Autocomplete search for Chennai localities, metro stations, suburban railway stations, and bus stops.

#### `POST /api/v1/routes/search`
Core multimodal journey planner endpoint.

**Request Body (MVP Schema):**
```json
{
  "source": "Chennai Central",
  "destination": "Guindy",
  "gender": "male",
  "sort_by": "cost"
}
```
*(Gender is `"male"` or `"female"`. `sort_by` is `"cost"` or `"time"`.)*

**Response Body (MVP Schema):**
```json
{
  "search_id": "search_101",
  "source": "Chennai Central",
  "destination": "Guindy",
  "gender": "male",
  "sort_by": "cost",
  "routes": [
    {
      "route_id": "route_suburban_direct",
      "total_fare": 5.0,
      "total_duration_minutes": 25,
      "transfers_count": 0,
      "summary": "Suburban Train from Moore Market Complex to Guindy",
      "legs": [
        {
          "mode": "walking",
          "from_stop": "Chennai Central",
          "to_stop": "Moore Market Complex (Suburban)",
          "duration_minutes": 4,
          "distance_meters": 250,
          "fare": 0.0,
          "fare_type": "verified",
          "fare_note": "Free walking transfer"
        },
        {
          "mode": "suburban_train",
          "route_name": "Beach - Tambaram Line",
          "from_stop": "Moore Market Complex",
          "to_stop": "Guindy Railway Station",
          "duration_minutes": 18,
          "distance_meters": 13000,
          "fare": 5.0,
          "fare_type": "verified",
          "fare_note": "Southern Railway 2nd Class Ordinary Ticket"
        },
        {
          "mode": "walking",
          "from_stop": "Guindy Railway Station",
          "to_stop": "Guindy",
          "duration_minutes": 3,
          "distance_meters": 200,
          "fare": 0.0,
          "fare_type": "verified",
          "fare_note": "Exit to destination"
        }
      ]
    }
  ]
}
```

### 6.3 Code Quality & Data Contracts
- Backend models defined using **Pydantic v2** (`BaseModel`).
- Frontend contracts mirroring backend models in `types/transit.ts`.
- Standard HTTP status codes: `200 OK`, `400 Bad Request`, `422 Unprocessable Entity`, `500 Internal Server Error`.

---

## 7. Git Workflow & Branching Policies

### 7.1 Branch Isolation
- **Frontend work** must be carried out exclusively on the `frontend` branch.
- **Backend work** must be carried out exclusively on the `backend` branch.
- Do not mix frontend application files into the backend branch or vice versa.

### 7.2 Safety & Integrity Rules
- **NEVER force-push** (`git push --force` or `git push -f`) to any branch under any circumstance.
- **NEVER merge directly into `main`** without explicit user review and approval.
- All merges to `main` must occur via reviewed pull requests or upon direct request by the user.

### 7.3 Pre-commit & Pre-push Testing
- Always run the relevant test, lint, and typecheck commands before committing or pushing changes:
  - **Frontend:**
    - Lint check: `npm run lint` / `pnpm lint`
    - Type check: `npx tsc --noEmit`
    - Test runner: `npm test`
  - **Backend:**
    - Unit tests: `pytest`
    - Formatting & linting: `flake8` / `ruff`
- If tests fail, resolve all errors before creating commits.

---

## 8. Current Roadmap Status

- [x] Repository initialized with Git and remote tracking.
- [x] `frontend` branch created and configured.
- [x] `AGENTS.md` updated with confirmed MVP UI specifications and data distinctions.
- [ ] Backend skeleton setup (`FastAPI`, fare rules engine distinguishing verified vs estimated data, pytest).
- [ ] Frontend MVP setup (`Next.js`, React, Tailwind CSS - Two-page workflow without map).
- [ ] Post-MVP: Leaflet & OpenStreetMap interactive mapping, mode toggles, departure-time scheduling.
