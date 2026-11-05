# Theme7 Public Transport & Road Network Data Inventory

## 1. Overview & Verification

This document provides a comprehensive inventory and data-quality assessment of the Chennai Metropolitan Area (CMA) **Theme7** dataset located in `data/raw/Theme7/`.

- **Source Directory:** `data/raw/Theme7/`
- **Verification Status:** Verified and inspected on 2026-11-06.
- **Dataset Scope:** Geospatial vector layers (ESRI Shapefiles, KML), tabular spreadsheets (XLSX), text metadata, and fare structure documentation (PDF). All original raw files have been preserved unmodified.

---

## 2. Dataset Inventory by Transport Mode

### 2.1 MTC Bus Network

#### A. Bus Route Alignments (`Public Transport/MTC/routes_merged.*`)
- **Format:** ESRI Shapefile (`.shp`, `.dbf`, `.prj`, `.qix`, `.qmd`, `.shx`)
- **Projection:** EPSG:4326 (WGS 84 geographic coordinates)
- **Record Count:** 1,348 route features (Polyline / MultiLineString)
- **Unique Bus Routes:** 680 distinct route numbers (e.g., `1C`, `1D`, `18A`, `21G`, `101`, `102`, `104`, `570`, `A1`, `M1`)
- **Unique Source Terminals:** 128 major bus stands/termini (e.g., M.G.R. Central, Broadway, T. Nagar, Tambaram, Thiruvanmiyur, Koyambedu, Poonamallee, Avadi)
- **Attributes:**
  - `route_num` (Character, 10): Official bus route designation.
  - `source` (Character, 50): Route origin / boarding terminus name.
  - `destinat` (Character, 50): Route destination terminus name.
  - `route_id` (Numeric, 19.11): Internal route identification number.
  - `poly_idx` (Character, 10): Polyline index sequence.
  - `Corridor` (Character, 50): Trunk or arterial corridor tag (predominantly unpopulated).

#### B. Bus Stops List (`Tambaram, Avadi, GCC Bus Stops List 1.xlsx`)
- **Format:** Microsoft Excel OpenXML Spreadsheet (`.xlsx`)
- **Sheets & Coverage:**
  - `GCC` (Greater Chennai Corporation): 2,227 bus stops
  - `Avadi` (Avadi Municipal Corporation): 143 bus stops
  - `Tambaram` (Tambaram Municipal Corporation): 347 bus stops
  - **Total Bus Stops Recorded:** 2,717 bus stop records across the 3 municipal regions
- **Attributes:**
  - `S.No`: Sequential stop index.
  - `Bus Stop Name`: Local name of the bus shelter / stop (e.g., *12th main road anna nagar*, *Anna Arch*, *Guindy Race Course*).
  - `Latitude`: Decimal degrees (WGS 84, approx. 12.8° to 13.3° N).
  - `Longitude`: Decimal degrees (WGS 84, approx. 80.0° to 80.3° E).

---

### 2.2 Chennai Metro Rail (CMRL)

#### A. Metro Corridors (`Public Transport/Metro Rail/Operational_Metro.*`)
- **Format:** ESRI Shapefile (`.shp`, `.dbf`, `.prj`, `.qmd`, `.shx`)
- **Projection:** EPSG:4326 (WGS 84)
- **Record Count:** 4 corridor segments (Polyline / MultiLineString)
- **Covered Corridors:**
  - **Blue Line (Phase 1):** 31.6 km (Wimco Nagar to Chennai International Airport)
  - **Green Line (Phase 1):** 21.3 km (Chennai Central to St. Thomas Mount via Koyambedu)
  - **C4 Corridor (Phase 2):** 26.1 km (Light House to Poonamallee Bypass alignment, recorded as 2 segments)
- **Attributes:**
  - `id` (Character, 10): Corridor index.
  - `Corridors` (Character, 50): Line name (`Blue Line`, `Green Line`, `C4 Corridor`).
  - `Phasing` (Character, 50): Implementation phase (`Phase 1`, `Phase 2`).
  - `Prop_Mode` (Character, 50): Transit mode (`Metro-Ph1&2`).
  - `Identifer` (Character, 50): Empty string.
  - `Length` (Character, 50): Corridor length in kilometers.

#### B. Metro Stations (`Public Transport/Metro Rail/Operational_Metro_Stns.*`)
- **Format:** ESRI Shapefile (`.shp`, `.dbf`, `.prj`, `.qmd`, `.shx`)
- **Projection:** EPSG:4326 (WGS 84)
- **Record Count:** 51 station nodes (Point geometry)
- **Corridor Distribution:**
  - Phase 1 Corridor 1 (Blue Line): 23 stations
  - Phase 1 Corridor 2 (Green Line): 18 stations
  - Phase 2 Corridor 4: 10 stations
- **Attributes:**
  - `id` (Character, 10): Blank.
  - `Name` (Character, 50): Synthetic placeholder labels (e.g., `Phase 1: C1-Stations 1`, `Phase 1 C2-Stations 1`, `Phase 2 Corridor 4 Stations 19`).
  - `descriptio`, `timestamp`, `begin`, `end`, `altitudeMo`, `icon`: Empty strings.
  - `tessellate`, `extrude`, `visibility`, `drawOrder`: Default GIS visualization parameters.

---

### 2.3 Suburban Railway & MRTS

#### A. Rail Network Alignment (`Public Transport/Suburban Rail/Rail_Network_Updated.*`)
- **Format:** ESRI Shapefile (`.shp`, `.dbf`, `.prj`, `.qmd`, `.shx`)
- **Projection:** EPSG:32644 (WGS 84 / UTM zone 44N projected coordinate system)
- **Record Count:** 53 track segments (Polyline)
- **Covered Line Types:**
  - `Suburban`: Broad-gauge suburban railway corridors (Chennai Beach–Tambaram–Chengalpattu, Central–Arakkonam, Central–Gummidipoondi).
  - `MRTS`: Mass Rapid Transit System elevated corridor (Chennai Beach–Velachery).
  - `MRTS&Sub`: Joint operating sections / shared corridors.
  - `CheckAD`: Administrative line checking segments.
- **Attributes:**
  - `OBJECTID`, `FNODE_`, `TNODE_`, `LPOLY_`, `RPOLY_`: Topological link-node descriptors.
  - `LENGTH`, `Shape_Leng`, `Length_Che`: Segment lengths (meters and kilometers).
  - `RL_CODE`: Railway line classification code (`0101`).
  - `Type`: Subsystem category (`Suburban`, `MRTS`, `MRTS&Sub`, `CheckAD`).
  - `Tracks`: Number of parallel rail tracks (e.g., 2.0 or 4.0 tracks).

#### B. Suburban Railway Stations (`Public Transport/Suburban Rail/Suburban Stations.kml`)
- **Format:** Keyhole Markup Language (`.kml`)
- **Record Count:** 70 station placemarks (Point geometry with Longitude, Latitude, Elevation)
- **Attributes:**
  - `<name>`: Anonymized placeholder names: `Stations 1` through `Stations 70`.
  - `<description>`: Unpopulated / empty tag.
  - `<coordinates>`: Geographical coordinates in WGS 84 (Lon, Lat, Altitude).

---

### 2.4 Road Network

#### Road Network (`Road Network Old CMA/Road_Network_Old CMA.*`)
- **Format:** ESRI Shapefile (`.shp`, `.dbf`, `.prj`, `.qmd`, `.shx`) accompanied by `Readme.txt`
- **Projection:** EPSG:32644 (UTM zone 44N)
- **Record Count:** 7,644 link segments (Polyline geometry)
- **Attributes:**
  - `NO` (Numeric, 10): Unique roadway link identifier.
  - `NUMLANES` (Character, 10): Number of lanes in one direction (`1`, `2`, `3`, `4`).
  - `V0PRT` (Character, 10): Free flow vehicular travel speed in km/h on link (`28km/h`, `30km/h`, `35km/h`, `40km/h`, `45km/h`, `50km/h`).
  - `Length` (Numeric, 10.2): Link length in kilometers.

---

### 2.5 Traffic Analysis Zones (TAZ)

#### TAZ Layer (`Traffic Analysis Zones/TAZ_old-CMA.*`)
- **Format:** ESRI Shapefile (`.shp`, `.dbf`, `.prj`, `.qmd`, `.shx`)
- **Projection:** EPSG:32644 (UTM zone 44N)
- **Record Count:** 280 traffic analysis zone polygons
- **Attributes:**
  - `taz` (Character, 10): Zone identifier (1 to 280).
  - `region` (Character, 50): Macro region (`OLD CMA Area`).
  - `district` (Character, 50): Administrative division (e.g., `Old Corporation`).
  - `agency` (Character, 50): Survey/planning agency (`VTRAC`).
  - `sample_cou` (Character, 10): Household travel survey sample count.
  - `lat` (Character, 30): Longitude value (see Data-Quality section).
  - `long` (Character, 30): Latitude value (see Data-Quality section).
  - `area` (Character, 30): Zone polygon area in sq km.

---

### 2.6 Public Transport Fare Structure (`Public Transport/PT Fare Structure.pdf`)

- **Format:** Adobe Portable Document Format (`.pdf`, 116,879 bytes)
- **Structure:** 1 page document containing an embedded raster image (`Image27`, 570 × 561 pixels, JPEG).
- **Available Slabs & Fares Decoded:**
  - **Local Train (Suburban 2nd Class Ordinary):**
    - 1 – 20 km: ₹5
    - 21 – 45 km: ₹10
    - 46 – 70 km: ₹15
    - 71 – 100 km: ₹20
  - **AC EMU (Local AC Train):**
    - 1 – 10 km: ₹35
    - 11 – 15 km: ₹40
    - 16 – 20 km: ₹60
    - 21 – 35 km: ₹85
    - 36 – 45 km: ₹90
    - 46 – 55 km: ₹100
    - 56 – 60 km: ₹105
    - 61 – 65 km: ₹115
    - 66 – 70 km: ₹130
  - **MRTS (2nd Class Ordinary):**
    - 1 – 10 km: ₹4
    - 11 – 15 km: ₹5
    - 16 – 20 km: ₹6
    - 21 – 25 km: ₹7

---

## 3. Data-Quality Issues & Anomalies

| Dataset | File / Layer | Severity | Identified Issue |
|---|---|---|---|
| **Metro Stations** | `Operational_Metro_Stns.dbf` | **Critical** | All 51 station features lack official public station names; instead, they have generic placeholder names (`Phase 1: C1-Stations 1`, `Phase 1 C2-Stations 1`). `descriptio` is blank. |
| **Suburban Stations** | `Suburban Stations.kml` | **Critical** | All 70 railway stations are anonymized as `Stations 1` through `Stations 70`. Station names (e.g., Chennai Beach, Guindy, Tambaram) are absent. |
| **MTC Bus Routes & Stops** | `routes_merged.shp` & `.xlsx` | **Critical** | There is **no foreign key, stop sequence table, or topological link** connecting the 1,348 route lines to the 2,717 bus stops in the Excel sheet. Routes only possess source and destination names. |
| **Fare Structure** | `PT Fare Structure.pdf` | **High** | The document is a raster screenshot cropped on the right edge. MTC bus fare tables, CMRL Metro station-to-station fare matrices, and First Class rail fares are truncated or missing. |
| **TAZ Coordinates** | `TAZ_old-CMA.dbf` | **Medium** | The attribute columns `lat` and `long` are **swapped**: the `lat` field contains longitude values (~80.2° E) and the `long` field contains latitude values (~13.0° N). |
| **Suburban Rail Network** | `Rail_Network_Updated.dbf` | **Medium** | Record 1 contains field overflow formatting asterisks (`**********` in `OBJECTID`, `FNODE_`, `LENGTH`, etc.). |
| **Road Network** | `Road_Network_Old CMA.dbf` | **Low** | Free flow speeds (`V0PRT`) are stored as text strings with suffix units (e.g. `'35km/h'`) rather than clean numerical types. Road names are omitted. |
| **Bus Stops Excel** | `Bus Stops List 1.xlsx` | **Low** | Redundant stop listings exist for bidirectional stops (e.g. opposite sides of roads) without standard direction markers (NB/SB/EB/WB). |

---

## 4. Missing Information & Gaps Summary

To deliver the multimodal journey planner defined in `AGENTS.md`, the following elements are **not present** in the raw Theme7 files:

1. **Timetables & Service Frequencies:**
   - No GTFS feeds, trip departure frequencies, first/last bus or train timings, or headway intervals are included in Theme7.
2. **Intermediate Public Transport (IPT):**
   - Auto rickshaws, share autos, and app-based taxi pricing/operating zones are not present in Theme7.
3. **Gender-Specific MTC Fare Rules:**
   - *Vidiyal Payana Thittam* (free travel for women on ordinary white-board buses) and stage-wise MTC bus fare tables (ordinary vs express vs deluxe vs AC) are absent from the cropped fare PDF.
4. **Official Station Names & Interchanges:**
   - Real-world station names for Metro and Suburban stations are missing and require reconciliation against ground-truth geospatial data.
5. **Bus Stop Sequence Topology:**
   - Order of bus stops along each bus route is not explicitly tabulated.

---

## 5. Strategic Recommendations for Backend Architecture

1. **Station Resolution:** Map the 51 Metro station points and 70 Suburban station coordinates to standard Chennai transit hubs using spatial proximity to ground-truth coordinates.
2. **Bus Route Association:** Use spatial buffering / projection of the 2,717 geocoded bus stops onto the 1,348 route polyline trajectories (`routes_merged.shp`) to synthesize valid stop sequences.
3. **Fare Engine Calibration:** Combine the decoded Suburban/MRTS distance slabs with the statutory MTC distance fare table, Chennai Metro zone matrix, and Tamil Nadu *Vidiyal Payana Thittam* rules as specified in `AGENTS.md`.
4. **Preservation:** All raw files under `data/raw/Theme7/` remain untouched as the immutable baseline.
