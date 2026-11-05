# AGENTS.md - NammaFare Project Guidelines & Architecture

## 1. Project Overview & Purpose

**NammaFare** is a Chennai-focused, multimodal transport journey planner designed to help commuters discover, compare, and navigate public and intermediate transit options across the Chennai metropolitan region.

The core goal of NammaFare is to provide transparent, accurate fare estimations and travel time predictions (ETA) tailored to Chennai's unique transit ecosystem, empowering users to make cost-effective and time-efficient commuting decisions.

---

## 2. Technology Stack

### 2.1 Frontend
- **Framework:** Next.js (App Router preferred)
- **UI Library:** React
- **Styling:** Tailwind CSS (utility-first, responsive, accessible)
- **State Management & Data Fetching:** React hooks, TanStack Query / SWR / Fetch API
- **Icons & UI Utilities:** Lucide React (or equivalent lightweight SVG icons), clsx, tailwind-merge

### 2.2 Backend
- **Language:** Python (3.11+)
- **Framework:** FastAPI
- **Data Validation & Serialization:** Pydantic v2
- **Server:** Uvicorn
- **Package & Dependency Management:** Virtual environment (`venv`) with `pip` / `requirements.txt` or `pyproject.toml`

### 2.3 Mapping & Geospatial
- **Map Renderer:** Leaflet (`react-leaflet` or vanilla Leaflet in client-side Next.js components)
- **Map Tiles:** OpenStreetMap (OSM) standard tile servers
- **Routing & Geocoding:** Integration with OSM / OSRM / Nominatim or pre-indexed Chennai transit GTFS/GIS data

---

## 3. Supported Chennai Transport Modes

NammaFare models and combines the following transport options into seamless multimodal itineraries:

1. **Walking:** First-mile, last-mile, and transit transfer connections.
2. **MTC Bus:** Metropolitan Transport Corporation bus network (Ordinary / White-Board, Express, Deluxe, and AC Volvo services).
3. **Chennai Metro (CMRL):** Blue Line, Green Line, and upcoming extensions.
4. **Suburban Train:** Chennai Suburban Railway network (Southern Railway lines: Chennai Central–Arakkonam, Chennai Beach–Tambaram–Chengalpattu, Chennai Central–Gummidipoondi, and MRTS Chennai Beach–Velachery).
5. **Auto Rickshaw:** Standard auto rickshaw estimates (meter base + per-km slabs or calibrated street estimates).
6. **Share Auto:** Point-to-point and arterial feeder routes (e.g., Guindy, Koyambedu, Ashok Pillar corridors) at standardized flat/hop fares.
7. **Taxi / Cab:** App-cab / street taxi estimates for point-to-point and emergency/comfort connections.

---

## 4. User Workflow (Two-Page Architecture)

NammaFare is structured around a streamlined, responsive two-page journey:

```
[ Page 1: Journey Search ] ──▶ User submits parameters ──▶ [ Page 2: Route Comparison ]
  - Origin & Destination                                    - Summary stats (Cheapest vs Fastest)
  - Gender Selection (M / F / Other)                        - Interactive Leaflet/OSM map
  - Transport Mode Preferences                              - List of multimodal itinerary cards
  - Departure / Arrival time                                - Detailed per-leg fare & ETA breakdown
                                                            - Cost & Time sorting tabs/filters
```

### Page 1: Journey Search
- **Origin & Destination Inputs:** Searchable location fields with autocomplete support for Chennai localities, transit stops, and landmarks.
- **Gender Selection:** Male / Female selection (critical for MTC fare calculation rules).
- **Mode Toggles:** Checkboxes or chips to enable/disable specific modes (e.g., exclude cabs or prioritize rail).
- **Time/Departure Preferences:** "Leave Now" or specific time picker.
- **Action:** "Find Routes" trigger submitting the search parameters to the backend routing engine.

### Page 2: Route Comparison
- **Map View:** Embedded Leaflet map displaying:
  - Route polylines color-coded by transit mode (e.g., Blue for Metro, Green for Suburban, Red/Yellow for MTC bus, Grey for walking).
  - Stop markers, transfer interchange nodes, and origin/destination pins.
- **Route Cards:** Multi-modal itinerary options comparing:
  - Total Estimated Fare (₹).
  - Total Travel Time & Estimated Time of Arrival (ETA).
  - Number of transfers and leg summary (e.g., Walk 300m ➜ MTC Bus 21G ➜ Walk 150m).
- **Sorting Controls:**
  - **Cheapest First (Lowest Cost)**
  - **Fastest First (Shortest Duration / ETA)**
  - Optional: Minimum Transfers
- **Leg-by-Leg Details (Expandable/Drawer):**
  - Departure and arrival timings per step.
  - Transparent fare breakdown per segment (e.g., MTC Bus: ₹0 for female commuter; Suburban: ₹5; Metro: ₹30).
  - Instructions for transfers and platform/stop names.

---

## 5. Fare Engine & Transparency Rules

### 5.1 Gender-Based MTC Fare Rule (*Vidiyal Payana Thittam*)
- Under the Tamil Nadu Government scheme (*Vidiyal Payana Thittam*), **women travel free of charge** in standard **MTC Ordinary (White-Board) buses**.
- **Fare Rules:**
  - If commuter is **Female**: Fare for ordinary MTC bus legs is strictly **₹0**.
  - If commuter is **Male**: Standard distance-based MTC stage fare table applies (e.g., ₹5 to ₹25+ depending on stage distance).
  - Express, Deluxe, and AC services remain chargeable for all genders based on their respective fare charts.

### 5.2 Transparent Fare Breakdown
- Every route option must display:
  - **Total Estimated Fare** clearly badge-marked (e.g., `₹25`).
  - **Per-leg fare explanation** detailing the ticketing rule applied (e.g., *Suburban 2nd class ticket: ₹5*, *MTC Ordinary: ₹0 [Vidiyal Payana Thittam]*).
  - Explicit disclaimer when fares are indicative (e.g., auto rickshaw or taxi fares calculated using standard daytime rates).

---

## 6. API Integration Conventions

### 6.1 Communication & Protocols
- RESTful HTTP APIs communicating strictly with JSON payloads.
- Base path prefix: `/api/v1`.
- CORS configured in FastAPI to allow requests from the Next.js frontend origin.

### 6.2 Standard Endpoints (Target Schema)
- `GET /api/v1/health`: Healthcheck endpoint returning `{ "status": "ok" }`.
- `GET /api/v1/places?q={query}`: Autocomplete search for Chennai locations and transit hubs.
- `POST /api/v1/routes/search`: Core multimodal routing engine.
  - **Request Body:**
    ```json
    {
      "origin": { "lat": 13.0827, "lng": 80.2707, "name": "Chennai Central" },
      "destination": { "lat": 12.9807, "lng": 80.2228, "name": "Guindy" },
      "gender": "female",
      "allowed_modes": ["walking", "bus", "metro", "suburban_train", "auto", "share_auto", "taxi"],
      "departure_time": "2026-11-06T09:00:00"
    }
    ```
  - **Response Body:**
    ```json
    {
      "search_id": "route_12345",
      "origin": "Chennai Central",
      "destination": "Guindy",
      "routes": [
        {
          "route_id": "r_1",
          "total_fare": 0.0,
          "total_duration_minutes": 42,
          "transfers_count": 1,
          "legs": [
            {
              "mode": "walking",
              "from_name": "Chennai Central Station",
              "to_name": "Central Bus Stand",
              "duration_minutes": 5,
              "distance_meters": 350,
              "fare": 0.0
            },
            {
              "mode": "bus",
              "route_number": "18A",
              "bus_type": "ordinary",
              "from_name": "Central Bus Stand",
              "to_name": "Guindy Race Course",
              "duration_minutes": 37,
              "distance_meters": 11500,
              "fare": 0.0,
              "fare_note": "Free travel under Vidiyal Payana Thittam"
            }
          ]
        }
      ]
    }
    ```

### 6.3 Code Quality & Data Contracts
- FastAPI backend models must be defined with **Pydantic v2** (`BaseModel`).
- Next.js frontend must mirror backend response types using TypeScript `interface` or `type` definitions in a dedicated types folder (`types/transit.ts`).
- Standard HTTP status codes: `200 OK`, `400 Bad Request`, `422 Unprocessable Entity`, `500 Internal Server Error`.

---

## 7. Git Workflow & Branching Policies

All agents and developers contributing to this repository must adhere strictly to these rules:

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
    - Test runner: `npm test` (when test suite is established)
  - **Backend:**
    - Unit tests: `pytest`
    - Formatting & linting: `flake8` / `ruff`
- If tests fail, the build fails: resolve all errors before creating commits.

---

## 8. Current Roadmap Status

- [x] Repository initialized with Git and remote tracking.
- [x] `frontend` branch created and configured.
- [x] `AGENTS.md` system guidelines established.
- [ ] Backend skeleton setup (`FastAPI`, initial transit model, pytest).
- [ ] Frontend skeleton setup (`Next.js`, Tailwind CSS, Leaflet integration).
- [ ] Fare rules engine & routing pipeline implementation.
