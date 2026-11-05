import os
import struct
import xml.etree.ElementTree as ET
import zipfile
from typing import List, Dict, Any, Optional, Tuple

from app.services.geometry_utils import (
    haversine_meters,
    read_shp_records,
    utm44n_to_wgs84,
    point_to_polyline_projection,
    slice_polyline,
    point_in_polygon,
)

def read_dbf_records(dbf_path: str) -> List[Dict[str, str]]:
    """Parse DBF binary file using standard library struct."""
    if not os.path.exists(dbf_path):
        return []
    try:
        with open(dbf_path, "rb") as f:
            header = f.read(32)
            if len(header) < 12:
                return []
            version, yy, mm, dd, num_records, header_len, record_len = struct.unpack(
                "<BBBBIHH", header[:12]
            )
            fields = []
            while True:
                field_desc = f.read(32)
                if not field_desc or field_desc[0] == 0x0D:
                    break
                name = field_desc[:11].split(b"\x00")[0].decode("ascii", errors="ignore")
                typ = chr(field_desc[11])
                length = field_desc[16]
                fields.append((name, typ, length))

            f.seek(header_len)
            records = []
            for _ in range(num_records):
                rec_bytes = f.read(record_len)
                if not rec_bytes or rec_bytes[0] == 0x1A:
                    break
                offset = 1
                rec = {}
                for name, typ, length in fields:
                    val = (
                        rec_bytes[offset : offset + length]
                        .decode("latin1", errors="replace")
                        .strip()
                    )
                    offset += length
                    rec[name] = val
                records.append(rec)
            return records
    except Exception as e:
        print(f"Error reading DBF {dbf_path}: {e}")
        return []

def read_xlsx_bus_stops(xlsx_path: str) -> List[Dict[str, Any]]:
    """Parse real bus stops from Theme7 Excel file."""
    if not os.path.exists(xlsx_path):
        return []
    stops = []
    try:
        with zipfile.ZipFile(xlsx_path, "r") as z:
            wb_xml = z.read("xl/workbook.xml")
            wb_tree = ET.fromstring(wb_xml)
            sheet_names = [
                node.attrib.get("name") for node in wb_tree.findall(".//{*}sheet")
            ]

            shared_strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                ss_tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for si in ss_tree.findall(".//{*}si"):
                    text = "".join([t.text for t in si.findall(".//{*}t") if t.text])
                    shared_strings.append(text)

            for idx, sname in enumerate(sheet_names, 1):
                sheet_file = f"xl/worksheets/sheet{idx}.xml"
                if sheet_file not in z.namelist():
                    continue
                s_tree = ET.fromstring(z.read(sheet_file))
                rows = s_tree.findall(".//{*}row")
                for r_idx, r in enumerate(rows):
                    if r_idx == 0:
                        continue  # Skip header
                    cells = r.findall("{*}c")
                    row_vals = []
                    for c in cells:
                        t = c.attrib.get("t")
                        v = c.find("{*}v")
                        val = v.text if v is not None else ""
                        if t == "s" and val.isdigit() and int(val) < len(shared_strings):
                            val = shared_strings[int(val)]
                        row_vals.append(val)
                    if len(row_vals) >= 4:
                        try:
                            s_no = row_vals[0]
                            name = row_vals[1].strip()
                            lat = float(row_vals[2])
                            lng = float(row_vals[3])
                            if 12.5 <= lat <= 13.5 and 79.8 <= lng <= 80.5:
                                stops.append(
                                    {
                                        "id": f"bs_{sname}_{s_no}_{r_idx}",
                                        "name": name.title(),
                                        "corporation": sname,
                                        "lat": lat,
                                        "lng": lng,
                                        "category": "bus_stop",
                                        "source": "Theme7.Bus_Stops_List",
                                    }
                                )
                        except (ValueError, TypeError):
                            continue
    except Exception as e:
        print(f"Error reading Excel {xlsx_path}: {e}")
    return stops

def read_kml_suburban_stations(kml_path: str) -> List[Dict[str, Any]]:
    """Parse real Suburban Railway stations from KML file."""
    if not os.path.exists(kml_path):
        return []
    stations = []
    try:
        tree = ET.parse(kml_path)
        root = tree.getroot()
        placemarks = root.findall(".//{*}Placemark")
        for idx, pm in enumerate(placemarks):
            name_elem = pm.find(".//{*}name")
            coords_elem = pm.find(".//{*}coordinates")
            raw_name = name_elem.text.strip() if name_elem is not None else f"Stations {idx+1}"
            if coords_elem is not None and coords_elem.text:
                parts = coords_elem.text.strip().split(",")
                if len(parts) >= 2:
                    lng = float(parts[0])
                    lat = float(parts[1])
                    stations.append(
                        {
                            "id": f"sub_stn_{idx+1}",
                            "name": f"Theme7 Suburban Station: {raw_name}",
                            "raw_name": raw_name,
                            "lat": lat,
                            "lng": lng,
                            "category": "railway_station",
                            "source": "Theme7.Suburban_Stations_KML",
                        }
                    )
    except Exception as e:
        print(f"Error reading KML {kml_path}: {e}")
    return stations

class TransitDataLoader:
    _instance = None

    def __init__(self, data_root: str = "data/raw/Theme7"):
        self.data_root = data_root

        # Datasets
        self.bus_stops: List[Dict[str, Any]] = []
        self.bus_routes: List[Dict[str, Any]] = []
        self.metro_corridors: List[Dict[str, Any]] = []
        self.metro_stations: List[Dict[str, Any]] = []
        self.suburban_tracks: List[Dict[str, Any]] = []
        self.suburban_stations: List[Dict[str, Any]] = []
        self.road_network: List[Dict[str, Any]] = []
        self.taz_zones: List[Dict[str, Any]] = []

        # Unified Search Index (Only Real Theme7 Places)
        self.places_index: List[Dict[str, Any]] = []

        self._load_all()

    @classmethod
    def get_instance(cls, data_root: str = "data/raw/Theme7") -> "TransitDataLoader":
        if cls._instance is None:
            cls._instance = TransitDataLoader(data_root=data_root)
        return cls._instance

    def _load_all(self):
        print("Loading full Theme7 dataset into pure data-driven routing memory...")

        # 1. Bus Stops (Excel)
        xlsx_path = os.path.join(self.data_root, "Tambaram, Avadi, GCC Bus Stops List  1.xlsx")
        self.bus_stops = read_xlsx_bus_stops(xlsx_path)

        # 2. MTC Bus Routes (Shapefile + DBF)
        mtc_shp = os.path.join(self.data_root, "Public Transport", "MTC", "routes_merged.shp")
        mtc_dbf = os.path.join(self.data_root, "Public Transport", "MTC", "routes_merged.dbf")
        shp_records = read_shp_records(mtc_shp, is_utm=False) if os.path.exists(mtc_shp) else []
        dbf_records = read_dbf_records(mtc_dbf) if os.path.exists(mtc_dbf) else []

        routes = []
        for i in range(min(len(shp_records), len(dbf_records))):
            geom = shp_records[i]
            attr = dbf_records[i]
            if geom["type"] == "polyline" and len(geom["points"]) >= 2:
                pts = geom["points"]
                lats = [p[0] for p in pts]
                lngs = [p[1] for p in pts]
                routes.append({
                    "index": i,
                    "route_num": attr.get("route_num", f"MTC-{i+1}"),
                    "source": attr.get("source", "Origin Terminus"),
                    "destinat": attr.get("destinat", "Destination Terminus"),
                    "route_id": attr.get("route_id", str(i+1)),
                    "poly_idx": attr.get("poly_idx", "1"),
                    "points": pts,
                    "bbox": (min(lats), min(lngs), max(lats), max(lngs)),
                })
        self.bus_routes = routes

        # 3. Metro Corridors & Stations (Shapefile + DBF)
        metro_shp = os.path.join(self.data_root, "Public Transport", "Metro Rail", "Operational_Metro.shp")
        metro_dbf = os.path.join(self.data_root, "Public Transport", "Metro Rail", "Operational_Metro.dbf")
        m_lines = read_shp_records(metro_shp, is_utm=False) if os.path.exists(metro_shp) else []
        m_attr = read_dbf_records(metro_dbf) if os.path.exists(metro_dbf) else []

        metro_corr = []
        for i in range(min(len(m_lines), len(m_attr))):
            geom = m_lines[i]
            attr = m_attr[i]
            if geom["type"] == "polyline" and len(geom["points"]) >= 2:
                metro_corr.append({
                    "id": attr.get("id", str(i+1)),
                    "corridor": attr.get("Corridors", f"Corridor {i+1}"),
                    "phasing": attr.get("Phasing", "Phase 1"),
                    "length_km": attr.get("Length", "20.0"),
                    "points": geom["points"],
                })
        self.metro_corridors = metro_corr

        stn_shp = os.path.join(self.data_root, "Public Transport", "Metro Rail", "Operational_Metro_Stns.shp")
        stn_dbf = os.path.join(self.data_root, "Public Transport", "Metro Rail", "Operational_Metro_Stns.dbf")
        s_pts = read_shp_records(stn_shp, is_utm=False) if os.path.exists(stn_shp) else []
        s_attr = read_dbf_records(stn_dbf) if os.path.exists(stn_dbf) else []

        m_stns = []
        for i in range(min(len(s_pts), len(s_attr))):
            geom = s_pts[i]
            attr = s_attr[i]
            if geom["type"] == "point":
                raw_name = attr.get("Name", f"Phase 1 Stations {i+1}")
                m_stns.append({
                    "id": f"metro_stn_{i+1}",
                    "name": f"Theme7 Metro Station: {raw_name}",
                    "raw_name": raw_name,
                    "lat": geom["point"][0],
                    "lng": geom["point"][1],
                    "category": "metro_station",
                    "source": "Theme7.Operational_Metro_Stns",
                })
        self.metro_stations = m_stns

        # 4. Suburban Rail Tracks & Stations (UTM converted to WGS84)
        rail_shp = os.path.join(self.data_root, "Public Transport", "Suburban Rail", "Rail_Network_Updated.shp")
        rail_dbf = os.path.join(self.data_root, "Public Transport", "Suburban Rail", "Rail_Network_Updated.dbf")
        r_lines = read_shp_records(rail_shp, is_utm=True) if os.path.exists(rail_shp) else []
        r_attr = read_dbf_records(rail_dbf) if os.path.exists(rail_dbf) else []

        s_tracks = []
        for i in range(min(len(r_lines), len(r_attr))):
            geom = r_lines[i]
            attr = r_attr[i]
            if geom["type"] == "polyline" and len(geom["points"]) >= 2:
                s_tracks.append({
                    "id": attr.get("OBJECTID", str(i+1)),
                    "type": attr.get("Type", "Suburban"),
                    "tracks": attr.get("Tracks", "2"),
                    "length": attr.get("LENGTH", "1000"),
                    "points": geom["points"],
                })
        self.suburban_tracks = s_tracks

        kml_path = os.path.join(self.data_root, "Public Transport", "Suburban Rail", "Suburban Stations.kml")
        self.suburban_stations = read_kml_suburban_stations(kml_path)

        # 5. Road Network (UTM to WGS84)
        road_shp = os.path.join(self.data_root, "Road Network Old CMA", "Road_Network_Old CMA.shp")
        road_dbf = os.path.join(self.data_root, "Road Network Old CMA", "Road_Network_Old CMA.dbf")
        rd_lines = read_shp_records(road_shp, is_utm=True) if os.path.exists(road_shp) else []
        rd_attr = read_dbf_records(road_dbf) if os.path.exists(road_dbf) else []

        roads = []
        for i in range(min(len(rd_lines), len(rd_attr))):
            geom = rd_lines[i]
            attr = rd_attr[i]
            if geom["type"] == "polyline" and len(geom["points"]) >= 2:
                roads.append({
                    "id": attr.get("NO", str(i+1)),
                    "lanes": attr.get("NUMLANES", "2"),
                    "speed": attr.get("V0PRT", "35km/h"),
                    "length_km": attr.get("Length", "0.5"),
                    "points": geom["points"],
                })
        self.road_network = roads

        # 6. TAZ Polygons (UTM to WGS84)
        taz_shp = os.path.join(self.data_root, "Traffic Analysis Zones", "TAZ_old-CMA.shp")
        taz_dbf = os.path.join(self.data_root, "Traffic Analysis Zones", "TAZ_old-CMA.dbf")
        t_polys = read_shp_records(taz_shp, is_utm=True) if os.path.exists(taz_shp) else []
        t_attr = read_dbf_records(taz_dbf) if os.path.exists(taz_dbf) else []

        zones = []
        for i in range(min(len(t_polys), len(t_attr))):
            geom = t_polys[i]
            attr = t_attr[i]
            if geom["type"] == "polygon" and len(geom["points"]) >= 3:
                pts = geom["points"]
                lats = [p[0] for p in pts]
                lngs = [p[1] for p in pts]
                zones.append({
                    "taz_id": attr.get("taz", str(i+1)),
                    "region": attr.get("region", "Old CMA"),
                    "district": attr.get("district", "Chennai"),
                    "sample_count": attr.get("sample_cou", "0"),
                    "points": pts,
                    "bbox": (min(lats), min(lngs), max(lats), max(lngs)),
                })
        self.taz_zones = zones

        # 7. Build Places Index strictly from Theme7 records
        self._build_places_index()

    def _build_places_index(self):
        index = []

        # A. Theme7 Bus Stops (deduplicated by normalized name)
        seen = set()
        for bs in self.bus_stops:
            norm = bs["name"].lower().strip()
            if norm not in seen:
                seen.add(norm)
                index.append({
                    "id": bs["id"],
                    "name": bs["name"],
                    "category": "bus_stop",
                    "lat": bs["lat"],
                    "lng": bs["lng"],
                    "source": bs["source"],
                    "provenance": "Theme7 dataset — Bus_Stops_List.xlsx (organization-provided)",
                    "is_verified": True,
                    "description": f"MTC Bus Stop ({bs['corporation']} Corporation)",
                })

        # B. Theme7 Metro Stations
        for ms in self.metro_stations:
            index.append({
                "id": ms["id"],
                "name": ms["name"],
                "category": "metro_station",
                "lat": ms["lat"],
                "lng": ms["lng"],
                "source": ms["source"],
                "provenance": "Theme7 dataset — Operational_Metro_Stns shapefile (organization-provided)",
                "is_verified": True,
                "description": "CMRL Metro Station (Phase 1/2)",
            })

        # C. Theme7 Suburban Stations
        for ss in self.suburban_stations:
            index.append({
                "id": ss["id"],
                "name": ss["name"],
                "category": "railway_station",
                "lat": ss["lat"],
                "lng": ss["lng"],
                "source": ss["source"],
                "provenance": "Theme7 dataset — Suburban_Stations_KML (organization-provided)",
                "is_verified": True,
                "description": "Chennai Suburban Railway Station",
            })

        self.places_index = index
        print(f"Theme7 Places Index built: {len(self.places_index)} real stations and stops.")

    def search_places(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search actual Theme7 stations and bus stops by substring query."""
        q = query.lower().strip()
        if not q:
            return self.places_index[:limit]

        exact = []
        prefix = []
        sub = []

        for p in self.places_index:
            name_lower = p["name"].lower()
            if q == name_lower:
                exact.append(p)
            elif name_lower.startswith(q):
                prefix.append(p)
            elif q in name_lower:
                sub.append(p)

        combined = exact + prefix + sub
        deduped = []
        seen = set()
        for p in combined:
            if p["id"] not in seen:
                seen.add(p["id"])
                deduped.append(p)
            if len(deduped) >= limit:
                break
        return deduped

    def find_nearest_bus_stop(self, lat: float, lng: float, max_radius_m: int = 1500) -> Optional[Tuple[Dict[str, Any], int]]:
        """Find the single closest actual Theme7 bus stop within radius."""
        closest = None
        min_dist = float("inf")
        for bs in self.bus_stops:
            d = haversine_meters(lat, lng, bs["lat"], bs["lng"])
            if d < min_dist and d <= max_radius_m:
                min_dist = d
                closest = (bs, d)
        return closest

    def find_taz_zone(self, lat: float, lng: float) -> Optional[str]:
        """Find the Traffic Analysis Zone (TAZ) containing the coordinate."""
        for z in self.taz_zones:
            min_lat, min_lng, max_lat, max_lng = z["bbox"]
            if min_lat <= lat <= max_lat and min_lng <= lng <= max_lng:
                if point_in_polygon(lat, lng, z["points"]):
                    return f"TAZ {z['taz_id']} ({z['district']})"
        return None

    def find_nearby_transport(
        self,
        lat: float,
        lng: float,
        radius_m: int = 800,
    ) -> Dict[str, List[Tuple[Dict[str, Any], int]]]:
        """
        Return Theme7 transport stops within *radius_m* metres of (lat, lng).

        Results are sorted by ascending distance.
        Returns dict with keys: "bus_stops", "metro_stations", "railway_stations".
        Each entry is a list of (stop_dict, distance_metres) tuples.
        """
        from app.core import config as cfg

        # Bus stops
        bus_hits = []
        for bs in self.bus_stops:
            d = haversine_meters(lat, lng, bs["lat"], bs["lng"])
            if d <= radius_m:
                bus_hits.append((bs, int(d)))
        bus_hits.sort(key=lambda x: x[1])

        # Metro stations
        metro_hits = []
        for ms in self.metro_stations:
            d = haversine_meters(lat, lng, ms["lat"], ms["lng"])
            if d <= radius_m:
                metro_hits.append((ms, int(d)))
        metro_hits.sort(key=lambda x: x[1])

        # Suburban railway stations
        rail_hits = []
        for ss in self.suburban_stations:
            d = haversine_meters(lat, lng, ss["lat"], ss["lng"])
            if d <= radius_m:
                rail_hits.append((ss, int(d)))
        rail_hits.sort(key=lambda x: x[1])

        return {
            "bus_stops": bus_hits[: cfg.NEARBY_MAX_BUS_STOPS],
            "metro_stations": metro_hits[: cfg.NEARBY_MAX_METRO],
            "railway_stations": rail_hits[: cfg.NEARBY_MAX_RAIL],
        }
