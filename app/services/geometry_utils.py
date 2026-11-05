import math
import struct
from typing import List, Tuple, Dict, Any, Optional

def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Calculate Haversine distance in meters between two WGS84 coordinates."""
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return int(R * c)

def wgs84_to_utm44n(lat: float, lon: float) -> Tuple[float, float]:
    """Convert WGS84 geographic coordinates to UTM Zone 44N (EPSG:32644) Easting, Northing."""
    a = 6378137.0
    f = 1 / 298.257223563
    b = a * (1 - f)
    e2 = (a*a - b*b) / (a*a)
    e_prime2 = (a*a - b*b) / (b*b)
    k0 = 0.9996
    lon0 = 81.0

    phi = math.radians(lat)
    lam = math.radians(lon)
    lam0 = math.radians(lon0)

    N = a / math.sqrt(1 - e2 * math.sin(phi)**2)
    T = math.tan(phi)**2
    C = e_prime2 * math.cos(phi)**2
    A = (lam - lam0) * math.cos(phi)

    M = a * ((1 - e2/4 - 3*e2**2/64 - 5*e2**3/256) * phi
             - (3*e2/8 + 3*e2**2/32 + 45*e2**3/1024) * math.sin(2*phi)
             + (15*e2**2/256 + 45*e2**3/1024) * math.sin(4*phi)
             - (35*e2**3/3072) * math.sin(6*phi))

    easting = k0 * N * (A + (1 - T + C) * A**3 / 6 + (5 - 18*T + T**2 + 72*C - 58*e_prime2) * A**5 / 120) + 500000.0
    northing = k0 * (M + N * math.tan(phi) * (A**2 / 2 + (5 - T + 9*C + 4*C**2) * A**4 / 24 + (61 - 58*T + T**2 + 600*C - 330*e_prime2) * A**6 / 720))
    return easting, northing

def utm44n_to_wgs84(easting: float, northing: float) -> Tuple[float, float]:
    """Convert UTM Zone 44N Easting, Northing to WGS84 Latitude, Longitude."""
    a = 6378137.0
    f = 1 / 298.257223563
    b = a * (1 - f)
    e2 = (a*a - b*b) / (a*a)
    e_prime2 = (a*a - b*b) / (b*b)
    k0 = 0.9996
    lon0 = 81.0

    x = easting - 500000.0
    y = northing
    M = y / k0
    mu = M / (a * (1 - e2/4 - 3*e2**2/64 - 5*e2**3/256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))

    phi1 = mu + (3*e1/2 - 27*e1**3/32)*math.sin(2*mu) + (21*e1**2/16 - 55*e1**4/32)*math.sin(4*mu) + (151*e1**3/96)*math.sin(6*mu)
    N1 = a / math.sqrt(1 - e2 * math.sin(phi1)**2)
    T1 = math.tan(phi1)**2
    C1 = e_prime2 * math.cos(phi1)**2
    R1 = a * (1 - e2) / (1 - e2 * math.sin(phi1)**2)**1.5
    D = x / (N1 * k0)

    lat = phi1 - (N1 * math.tan(phi1) / R1) * (D**2 / 2 - (5 + 3*T1 + 10*C1 - 4*C1**2 - 9*e_prime2) * D**4 / 24 + (61 + 90*T1 + 298*C1 + 45*T1**2 - 252*e_prime2 - 3*C1**2) * D**6 / 720)
    lon = math.radians(lon0) + (D - (1 + 2*T1 + C1) * D**3 / 6 + (5 - 2*C1 + 28*T1 - 3*C1**2 + 8*e_prime2 + 24*T1**2) * D**5 / 120) / math.cos(phi1)
    return math.degrees(lat), math.degrees(lon)

def read_shp_records(shp_path: str, is_utm: bool = False) -> List[Dict[str, Any]]:
    """Parse ESRI Shapefile binary file and return geometry records."""
    records = []
    with open(shp_path, "rb") as f:
        header = f.read(100)
        if len(header) < 100:
            return []
        file_len = struct.unpack(">I", header[24:28])[0] * 2

        while f.tell() < file_len:
            rec_head = f.read(8)
            if not rec_head or len(rec_head) < 8:
                break
            rec_num, content_len = struct.unpack(">II", rec_head)
            rec_data = f.read(content_len * 2)
            if len(rec_data) < 4:
                break
            shape_type = struct.unpack("<I", rec_data[:4])[0]

            # Point (1) or PointZ (11)
            if shape_type in (1, 11):
                x, y = struct.unpack("<dd", rec_data[4:20])
                if is_utm:
                    lat, lon = utm44n_to_wgs84(x, y)
                else:
                    lat, lon = y, x
                records.append({"type": "point", "point": (lat, lon)})

            # Polyline (3) or PolyLineZ (13)
            elif shape_type in (3, 13):
                num_parts, num_points = struct.unpack("<II", rec_data[36:44])
                pts_offset = 44 + 4 * num_parts
                points = []
                for i in range(num_points):
                    x, y = struct.unpack("<dd", rec_data[pts_offset + i * 16 : pts_offset + (i + 1) * 16])
                    if is_utm:
                        lat, lon = utm44n_to_wgs84(x, y)
                    else:
                        lat, lon = y, x
                    points.append((lat, lon))
                records.append({"type": "polyline", "points": points})

            # Polygon (5)
            elif shape_type == 5:
                num_parts, num_points = struct.unpack("<II", rec_data[36:44])
                pts_offset = 44 + 4 * num_parts
                points = []
                for i in range(num_points):
                    x, y = struct.unpack("<dd", rec_data[pts_offset + i * 16 : pts_offset + (i + 1) * 16])
                    if is_utm:
                        lat, lon = utm44n_to_wgs84(x, y)
                    else:
                        lat, lon = y, x
                    points.append((lat, lon))
                records.append({"type": "polygon", "points": points})
            else:
                records.append({"type": "null"})
    return records

def point_to_polyline_projection(
    plat: float, plng: float, polyline: List[Tuple[float, float]]
) -> Tuple[float, Tuple[float, float], int, float, float]:
    """
    Project point onto polyline.
    Returns:
      (min_distance_meters, projected_point, segment_index, curve_position_meters, total_line_length_meters)
    """
    if len(polyline) < 2:
        return float("inf"), (plat, plng), 0, 0.0, 0.0

    min_dist = float("inf")
    best_idx = 0
    best_t = 0.0
    best_proj = polyline[0]

    cum_dists = [0.0]
    for i in range(len(polyline) - 1):
        p1 = polyline[i]
        p2 = polyline[i + 1]
        seg_len = haversine_meters(p1[0], p1[1], p2[0], p2[1])
        cum_dists.append(cum_dists[-1] + seg_len)

        dx = (p2[1] - p1[1]) * math.cos(math.radians((p1[0] + p2[0]) / 2.0))
        dy = (p2[0] - p1[0])
        if dx == 0 and dy == 0:
            d = haversine_meters(plat, plng, p1[0], p1[1])
            proj = p1
            t = 0.0
        else:
            px = (plng - p1[1]) * math.cos(math.radians((p1[0] + p2[0]) / 2.0))
            py = (plat - p1[0])
            t = max(0.0, min(1.0, (px * dx + py * dy) / (dx * dx + dy * dy)))
            proj = (p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1]))
            d = haversine_meters(plat, plng, proj[0], proj[1])

        if d < min_dist:
            min_dist = d
            best_idx = i
            best_t = t
            best_proj = proj

    curve_pos = cum_dists[best_idx] + best_t * (cum_dists[best_idx + 1] - cum_dists[best_idx])
    return min_dist, best_proj, best_idx, curve_pos, cum_dists[-1]

def slice_polyline(
    polyline: List[Tuple[float, float]],
    start_proj: Tuple[float, float],
    end_proj: Tuple[float, float],
    start_idx: int,
    end_idx: int,
) -> List[List[float]]:
    """Extract the exact sub-polyline segment from start projection to end projection."""
    sliced = [[start_proj[0], start_proj[1]]]
    for i in range(start_idx + 1, end_idx + 1):
        sliced.append([polyline[i][0], polyline[i][1]])
    sliced.append([end_proj[0], end_proj[1]])
    return sliced

def point_in_polygon(lat: float, lng: float, polygon: List[Tuple[float, float]]) -> bool:
    """Ray casting point-in-polygon test."""
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    p1lat, p1lng = polygon[0]
    for i in range(1, n + 1):
        p2lat, p2lng = polygon[i % n]
        if min(p1lat, p2lat) < lat <= max(p1lat, p2lat):
            if lng <= max(p1lng, p2lng):
                if p1lat != p2lat:
                    xinters = (lat - p1lat) * (p2lng - p1lng) / (p2lat - p1lat) + p1lng
                if p1lng == p2lng or lng <= xinters:
                    inside = not inside
        p1lat, p1lng = p2lat, p2lng
    return inside

