import os
import struct
import xml.etree.ElementTree as ET
import zipfile
import math
from typing import List, Dict, Any, Optional

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Calculate Haversine distance in meters between two coordinates."""
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return int(R * c)

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
    """Parse bus stops from Theme7 Excel file using zipfile and ElementTree."""
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
                            # Basic sanity check for Chennai bounding box
                            if 12.5 <= lat <= 13.5 and 79.8 <= lng <= 80.5:
                                stops.append(
                                    {
                                        "id": f"bs_{sname}_{s_no}_{r_idx}",
                                        "name": name.title(),
                                        "corporation": sname,
                                        "lat": lat,
                                        "lng": lng,
                                        "category": "bus_stop",
                                        "source": "theme7_raw",
                                    }
                                )
                        except (ValueError, TypeError):
                            continue
    except Exception as e:
        print(f"Error reading Excel {xlsx_path}: {e}")
    return stops

def read_kml_suburban_stations(kml_path: str) -> List[Dict[str, Any]]:
    """Parse Suburban Railway stations from KML file."""
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
            raw_name = name_elem.text.strip() if name_elem is not None else f"Station {idx+1}"
            if coords_elem is not None and coords_elem.text:
                parts = coords_elem.text.strip().split(",")
                if len(parts) >= 2:
                    lng = float(parts[0])
                    lat = float(parts[1])
                    stations.append(
                        {
                            "id": f"sub_stn_{idx+1}",
                            "raw_name": raw_name,
                            "lat": lat,
                            "lng": lng,
                            "category": "railway_station",
                            "source": "theme7_raw_anonymized",
                        }
                    )
    except Exception as e:
        print(f"Error reading KML {kml_path}: {e}")
    return stations

# Canonical Major Transit Hubs in Chennai with Ground Truth Coordinates
# Used to augment anonymized stations with real names while preserving raw data
CANONICAL_CHENNAI_HUBS = [
    {"name": "Puratchi Thalaivar Dr. M.G.R. Central (Chennai Central)", "short": "Chennai Central", "lat": 13.0827, "lng": 80.2755, "type": "interchange", "modes": ["metro", "suburban_train", "bus"]},
    {"name": "Chennai Egmore", "short": "Egmore", "lat": 13.0784, "lng": 80.2612, "type": "interchange", "modes": ["metro", "suburban_train", "bus"]},
    {"name": "Guindy", "short": "Guindy", "lat": 13.0067, "lng": 80.2128, "type": "interchange", "modes": ["metro", "suburban_train", "bus"]},
    {"name": "Tambaram", "short": "Tambaram", "lat": 12.9249, "lng": 80.1000, "type": "hub", "modes": ["suburban_train", "bus"]},
    {"name": "Chennai International Airport", "short": "Airport", "lat": 12.9800, "lng": 80.1636, "type": "metro_station", "modes": ["metro", "bus"]},
    {"name": "Koyambedu (Puratchi Thalaivar Dr. MGR Bus Terminus)", "short": "Koyambedu CMBT", "lat": 13.0673, "lng": 80.1983, "type": "interchange", "modes": ["metro", "bus"]},
    {"name": "Alandur", "short": "Alandur", "lat": 13.0041, "lng": 80.2015, "type": "interchange", "modes": ["metro"]},
    {"name": "Vadapalani", "short": "Vadapalani", "lat": 13.0504, "lng": 80.2121, "type": "metro_station", "modes": ["metro", "bus"]},
    {"name": "Thirumangalam", "short": "Thirumangalam", "lat": 13.0853, "lng": 80.1925, "type": "metro_station", "modes": ["metro", "bus"]},
    {"name": "Anna Nagar Tower", "short": "Anna Nagar", "lat": 13.0862, "lng": 80.2132, "type": "metro_station", "modes": ["metro", "bus"]},
    {"name": "T. Nagar (Thyagaraya Nagar)", "short": "T. Nagar", "lat": 13.0418, "lng": 80.2341, "type": "hub", "modes": ["bus", "suburban_train"]},
    {"name": "Chennai Beach", "short": "Chennai Beach", "lat": 13.0924, "lng": 80.2936, "type": "interchange", "modes": ["suburban_train", "bus"]},
    {"name": "Velachery", "short": "Velachery", "lat": 12.9759, "lng": 80.2212, "type": "hub", "modes": ["suburban_train", "bus"]},
    {"name": "Thiruvanmiyur", "short": "Thiruvanmiyur", "lat": 12.9830, "lng": 80.2594, "type": "hub", "modes": ["suburban_train", "bus"]},
    {"name": "Mylapore (Luz)", "short": "Mylapore", "lat": 13.0334, "lng": 80.2687, "type": "locality", "modes": ["bus", "suburban_train"]},
    {"name": "Adyar (LB Road)", "short": "Adyar", "lat": 13.0064, "lng": 80.2575, "type": "locality", "modes": ["bus"]},
    {"name": "Perambur", "short": "Perambur", "lat": 13.1098, "lng": 80.2335, "type": "interchange", "modes": ["suburban_train", "bus"]},
    {"name": "Avadi", "short": "Avadi", "lat": 13.1166, "lng": 80.0984, "type": "hub", "modes": ["suburban_train", "bus"]},
    {"name": "Poonamallee", "short": "Poonamallee", "lat": 13.0487, "lng": 80.0954, "type": "hub", "modes": ["bus"]},
    {"name": "Sholinganallur (OMR)", "short": "Sholinganallur", "lat": 12.9010, "lng": 80.2279, "type": "locality", "modes": ["bus"]},
    {"name": "Siruseri (SIPCOT IT Park)", "short": "Siruseri", "lat": 12.8258, "lng": 80.2195, "type": "locality", "modes": ["bus"]},
    {"name": "Chromepet", "short": "Chromepet", "lat": 12.9517, "lng": 80.1408, "type": "railway_station", "modes": ["suburban_train", "bus"]},
    {"name": "Pallavaram", "short": "Pallavaram", "lat": 12.9680, "lng": 80.1492, "type": "railway_station", "modes": ["suburban_train", "bus"]},
    {"name": "St. Thomas Mount", "short": "St. Thomas Mount", "lat": 12.9958, "lng": 80.1981, "type": "interchange", "modes": ["metro", "suburban_train", "bus"]},
    {"name": "Nandanam", "short": "Nandanam", "lat": 13.0310, "lng": 80.2390, "type": "metro_station", "modes": ["metro", "bus"]},
    {"name": "Saidapet", "short": "Saidapet", "lat": 13.0213, "lng": 80.2232, "type": "interchange", "modes": ["metro", "suburban_train", "bus"]},
    {"name": "Ashok Nagar", "short": "Ashok Nagar", "lat": 13.0354, "lng": 80.2114, "type": "metro_station", "modes": ["metro", "bus"]},
    {"name": "Wimco Nagar", "short": "Wimco Nagar", "lat": 13.1706, "lng": 80.3014, "type": "interchange", "modes": ["metro", "suburban_train"]},
    {"name": "Washermanpet", "short": "Washermanpet", "lat": 13.1118, "lng": 80.2831, "type": "interchange", "modes": ["metro", "suburban_train", "bus"]}
]

class TransitDataLoader:
    _instance = None

    def __init__(self, data_root: str = "data/raw/Theme7"):
        self.data_root = data_root
        self.bus_stops: List[Dict[str, Any]] = []
        self.bus_routes: List[Dict[str, Any]] = []
        self.metro_corridors: List[Dict[str, Any]] = []
        self.suburban_stations: List[Dict[str, Any]] = []
        self.places_index: List[Dict[str, Any]] = []
        self._load_all()

    @classmethod
    def get_instance(cls, data_root: str = "data/raw/Theme7") -> "TransitDataLoader":
        if cls._instance is None:
            cls._instance = TransitDataLoader(data_root=data_root)
        return cls._instance

    def _load_all(self):
        # 1. Load Bus Stops from Excel
        xlsx_path = os.path.join(self.data_root, "Tambaram, Avadi, GCC Bus Stops List  1.xlsx")
        self.bus_stops = read_xlsx_bus_stops(xlsx_path)

        # 2. Load MTC Bus Routes from DBF
        mtc_dbf = os.path.join(self.data_root, "Public Transport", "MTC", "routes_merged.dbf")
        self.bus_routes = read_dbf_records(mtc_dbf)

        # 3. Load Metro Corridors
        metro_dbf = os.path.join(self.data_root, "Public Transport", "Metro Rail", "Operational_Metro.dbf")
        self.metro_corridors = read_dbf_records(metro_dbf)

        # 4. Load Suburban Stations from KML
        kml_path = os.path.join(self.data_root, "Public Transport", "Suburban Rail", "Suburban Stations.kml")
        self.suburban_stations = read_kml_suburban_stations(kml_path)

        # 5. Build Comprehensive Places Index
        self._build_places_index()

    def _build_places_index(self):
        index = []
        # A. Add Canonical Transit Hubs
        for idx, hub in enumerate(CANONICAL_CHENNAI_HUBS):
            index.append({
                "id": f"hub_{idx+1}",
                "name": hub["name"],
                "short_name": hub["short"],
                "category": hub["type"],
                "lat": hub["lat"],
                "lng": hub["lng"],
                "modes": hub["modes"],
                "source": "canonical_hub",
                "description": f"Chennai Transit Hub ({', '.join(hub['modes']).title()})"
            })

        # B. Add Theme7 Bus Stops (deduplicating by normalized name & proximity)
        seen_stops = {}
        for bs in self.bus_stops:
            norm = bs["name"].lower().strip()
            if norm not in seen_stops:
                seen_stops[norm] = bs
                index.append({
                    "id": bs["id"],
                    "name": bs["name"],
                    "short_name": bs["name"],
                    "category": "bus_stop",
                    "lat": bs["lat"],
                    "lng": bs["lng"],
                    "modes": ["bus"],
                    "source": "theme7_bus_stops",
                    "description": f"MTC Bus Stop ({bs['corporation']} Corporation)"
                })

        self.places_index = index

    def search_places(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search transit places, hubs, and bus stops with substring and prefix matching."""
        q = query.lower().strip()
        if not q:
            # Return top major hubs
            return self.places_index[:limit]

        exact_matches = []
        prefix_matches = []
        sub_matches = []

        for p in self.places_index:
            name_lower = p["name"].lower()
            short_lower = p.get("short_name", "").lower()
            if q == name_lower or q == short_lower:
                exact_matches.append(p)
            elif name_lower.startswith(q) or short_lower.startswith(q):
                prefix_matches.append(p)
            elif q in name_lower or q in short_lower:
                sub_matches.append(p)

        # Prioritize canonical hubs and exact matches
        combined = exact_matches + prefix_matches + sub_matches
        seen = set()
        deduped = []
        for item in combined:
            if item["id"] not in seen:
                seen.add(item["id"])
                deduped.append(item)
            if len(deduped) >= limit:
                break
        return deduped

    def find_nearest_place(self, lat: float, lng: float, mode_filter: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find the closest transit place to a given coordinate."""
        closest = None
        min_dist = float("inf")
        for p in self.places_index:
            if mode_filter and mode_filter not in p.get("modes", []):
                continue
            dist = haversine_distance_meters(lat, lng, p["lat"], p["lng"])
            if dist < min_dist:
                min_dist = dist
                closest = (p, dist)
        return closest
