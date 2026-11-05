import uuid
from typing import List, Dict, Any, Optional, Tuple
from app.models.schemas import (
    SearchRequest,
    SearchResponse,
    RouteOption,
    RouteLeg,
    Coordinates,
)
from app.services.data_loader import TransitDataLoader
from app.services.geometry_utils import (
    haversine_meters,
    point_to_polyline_projection,
    slice_polyline,
)
from app.services.fare_service import FareService
from app.services.eta_service import ETAService

class MultimodalRoutingEngine:
    def __init__(self, data_loader: TransitDataLoader):
        self.loader = data_loader

    def search_routes(self, request: SearchRequest) -> SearchResponse:
        origin = request.origin
        destination = request.destination
        gender = (request.gender or "other").lower().strip()
        allowed_modes = set(m.lower().strip() for m in (request.allowed_modes or []))
        sort_by = (request.sort_by or "cheapest").lower().strip()

        direct_dist = haversine_meters(
            origin.lat, origin.lng, destination.lat, destination.lng
        )

        routes: List[RouteOption] = []

        # 1. Direct Walking (Only if distance is <= 2.0 km and walking allowed)
        if "walking" in allowed_modes and direct_dist <= 2000:
            routes.append(self._build_direct_walking_route(origin, destination, direct_dist, request.departure_time))

        # 2. MTC Bus (Real Theme7 Route Polyline Intersection)
        if "bus" in allowed_modes:
            bus_routes = self._build_mtc_bus_routes(origin, destination, gender, request.departure_time)
            routes.extend(bus_routes)

        # 3. Chennai Metro (Real Theme7 Metro Station & Corridor Slicing)
        if "metro" in allowed_modes:
            metro_route = self._build_metro_route(origin, destination, request.departure_time)
            if metro_route:
                routes.append(metro_route)

        # 4. Suburban Railway (Real Theme7 Suburban Stations & Track Slicing)
        if "suburban_train" in allowed_modes:
            suburban_route = self._build_suburban_route(origin, destination, request.departure_time)
            if suburban_route:
                routes.append(suburban_route)

        # Identify TAZ Zones using Theme7 TAZ Polygons
        origin_taz = self.loader.find_taz_zone(origin.lat, origin.lng)
        dest_taz = self.loader.find_taz_zone(destination.lat, destination.lng)

        # If no valid connected journey was found in the dataset, return empty list
        if not routes:
            dep_str, _ = ETAService.calculate_departure_and_arrival(request.departure_time or "", 0)
            return SearchResponse(
                search_id=f"search_{uuid.uuid4().hex[:8]}",
                origin=origin.name or f"({origin.lat:.4f}, {origin.lng:.4f})",
                destination=destination.name or f"({destination.lat:.4f}, {destination.lng:.4f})",
                departure_time=dep_str,
                gender=gender,
                origin_taz=origin_taz,
                destination_taz=dest_taz,
                message="No connected public transport route found in the Theme7 dataset between the specified coordinates within walking access thresholds.",
                routes=[],
            )

        # Mark Cheapest and Fastest
        min_fare = min(r.total_fare for r in routes)
        min_time = min(r.total_duration_minutes for r in routes)
        for r in routes:
            r.is_cheapest = (r.total_fare == min_fare)
            r.is_fastest = (r.total_duration_minutes == min_time)

        # Sort according to user preference
        if sort_by == "fastest":
            routes.sort(key=lambda r: (r.total_duration_minutes, r.total_fare))
        else:
            routes.sort(key=lambda r: (r.total_fare, r.total_duration_minutes))

        dep_str, _ = ETAService.calculate_departure_and_arrival(request.departure_time or "", 0)

        return SearchResponse(
            search_id=f"search_{uuid.uuid4().hex[:8]}",
            origin=origin.name or f"({origin.lat:.4f}, {origin.lng:.4f})",
            destination=destination.name or f"({destination.lat:.4f}, {destination.lng:.4f})",
            departure_time=dep_str,
            gender=gender,
            origin_taz=origin_taz,
            destination_taz=dest_taz,
            routes=routes,
        )

    def _build_direct_walking_route(
        self, origin: Coordinates, destination: Coordinates, dist: int, dep_time: Optional[str]
    ) -> RouteOption:
        dur = ETAService.calculate_duration_minutes(dist, "walking")
        dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", dur)
        fare, note, is_ver, prov = FareService.calculate_walking_fare(dist)
        leg = RouteLeg(
            mode="walking",
            from_name=origin.name or "Origin",
            to_name=destination.name or "Destination",
            duration_minutes=dur,
            distance_meters=dist,
            fare=fare,
            fare_note=note,
            is_estimated=False,
            is_verified=is_ver,
            provenance=prov,
            polyline=[[origin.lat, origin.lng], [destination.lat, destination.lng]],
        )
        return RouteOption(
            route_id=f"r_walk_{uuid.uuid4().hex[:6]}",
            summary=f"Direct Walk ({dur} mins, {dist}m)",
            total_fare=0.0,
            total_duration_minutes=dur,
            total_distance_meters=dist,
            transfers_count=0,
            departure_time=dep_str,
            arrival_time=arr_str,
            is_verified=True,
            provenance="Theme7 Pedestrian Walk Connection",
            legs=[leg],
        )

    def _build_mtc_bus_routes(
        self, origin: Coordinates, destination: Coordinates, gender: str, dep_time: Optional[str]
    ) -> List[RouteOption]:
        """
        Derive genuine bus journeys by finding actual MTC route geometries in routes_merged.shp
        that pass within walking radius of origin and destination in the travel direction.
        """
        results: List[RouteOption] = []
        max_access_m = 900  # maximum walking access radius to bus corridor

        # Spatial filter candidates using bounding boxes
        candidate_matches = []
        for route in self.loader.bus_routes:
            min_lat, min_lng, max_lat, max_lng = route["bbox"]
            margin = 0.01  # approx 1.1 km
            if not (min_lat - margin <= origin.lat <= max_lat + margin and
                    min_lng - margin <= origin.lng <= max_lng + margin):
                continue
            if not (min_lat - margin <= destination.lat <= max_lat + margin and
                    min_lng - margin <= destination.lng <= max_lng + margin):
                continue

            # Project origin and destination onto polyline
            d_orig, p_orig, idx_o, pos_o, tot_len = point_to_polyline_projection(
                origin.lat, origin.lng, route["points"]
            )
            if d_orig > max_access_m:
                continue

            d_dest, p_dest, idx_d, pos_d, _ = point_to_polyline_projection(
                destination.lat, destination.lng, route["points"]
            )
            if d_dest > max_access_m:
                continue

            # Route must traverse in the direction of travel
            if pos_o < pos_d and (pos_d - pos_o) >= 400:
                score = d_orig + d_dest
                candidate_matches.append({
                    "route": route,
                    "d_orig": d_orig,
                    "d_dest": d_dest,
                    "p_orig": p_orig,
                    "p_dest": p_dest,
                    "idx_o": idx_o,
                    "idx_d": idx_d,
                    "bus_dist": int(pos_d - pos_o),
                    "score": score,
                })

        if not candidate_matches:
            return []

        # Sort by best access proximity and pick top distinct route numbers
        candidate_matches.sort(key=lambda x: x["score"])
        seen_route_nums = set()
        selected_candidates = []
        for c in candidate_matches:
            rnum = c["route"]["route_num"]
            if rnum not in seen_route_nums:
                seen_route_nums.add(rnum)
                selected_candidates.append(c)
            if len(selected_candidates) >= 2:
                break

        for cand in selected_candidates:
            route = cand["route"]
            bus_dist = cand["bus_dist"]
            p_orig = cand["p_orig"]
            p_dest = cand["p_dest"]

            # Slice exact actual polyline from Theme7 routes_merged.shp
            sliced_bus_geom = slice_polyline(
                route["points"], p_orig, p_dest, cand["idx_o"], cand["idx_d"]
            )

            # Find closest Theme7 bus stop to boarding and alighting points
            orig_stop_match = self.loader.find_nearest_bus_stop(p_orig[0], p_orig[1], max_radius_m=800)
            dest_stop_match = self.loader.find_nearest_bus_stop(p_dest[0], p_dest[1], max_radius_m=800)

            orig_stop_name = (
                f"{orig_stop_match[0]['name']} (MTC Stop)"
                if orig_stop_match
                else f"MTC Boarding Point near {route['source']}"
            )
            dest_stop_name = (
                f"{dest_stop_match[0]['name']} (MTC Stop)"
                if dest_stop_match
                else f"MTC Alighting Point near {route['destinat']}"
            )

            walk1_dist = int(cand["d_orig"])
            walk2_dist = int(cand["d_dest"])
            walk1_dur = ETAService.calculate_duration_minutes(walk1_dist, "walking")
            walk2_dur = ETAService.calculate_duration_minutes(walk2_dist, "walking")
            bus_dur = ETAService.calculate_duration_minutes(bus_dist, "bus") + ETAService.TRANSFER_BUFFER_MINUTES["bus"]
            total_dur = walk1_dur + bus_dur + walk2_dur
            total_dist = walk1_dist + bus_dist + walk2_dist

            dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", total_dur)

            # Calculate verified MTC Ordinary Bus Fare (Vidiyal Payana Thittam)
            fare, fare_note, is_ver, prov = FareService.calculate_mtc_bus_fare(
                bus_dist, bus_type="ordinary", gender=gender
            )

            legs = [
                RouteLeg(
                    mode="walking",
                    from_name=origin.name or "Origin",
                    to_name=orig_stop_name,
                    duration_minutes=walk1_dur,
                    distance_meters=walk1_dist,
                    fare=0.0,
                    fare_note="Walking to MTC bus boarding location",
                    is_estimated=False,
                    is_verified=True,
                    provenance="Pedestrian Access",
                    polyline=[[origin.lat, origin.lng], [p_orig[0], p_orig[1]]],
                ),
                RouteLeg(
                    mode="bus",
                    route_number=route["route_num"],
                    bus_type="ordinary",
                    from_name=orig_stop_name,
                    to_name=dest_stop_name,
                    duration_minutes=bus_dur,
                    distance_meters=bus_dist,
                    fare=fare,
                    fare_note=f"{fare_note} [Spatially Derived Theme7 Corridor]",
                    is_estimated=False,
                    is_verified=False,  # Spatially derived stop sequence, not verified GTFS
                    provenance="Theme7.Public_Transport.MTC.routes_merged (Shapefile Geometry Sliced)",
                    polyline=sliced_bus_geom,
                ),
                RouteLeg(
                    mode="walking",
                    from_name=dest_stop_name,
                    to_name=destination.name or "Destination",
                    duration_minutes=walk2_dur,
                    distance_meters=walk2_dist,
                    fare=0.0,
                    fare_note="Walking from MTC bus alighting location",
                    is_estimated=False,
                    is_verified=True,
                    provenance="Pedestrian Access",
                    polyline=[[p_dest[0], p_dest[1]], [destination.lat, destination.lng]],
                ),
            ]

            summary = f"MTC Route {route['route_num']} ({route['source']} ➔ {route['destinat']})"
            results.append(
                RouteOption(
                    route_id=f"r_mtc_{route['route_num']}_{uuid.uuid4().hex[:4]}",
                    summary=summary,
                    total_fare=fare,
                    total_duration_minutes=total_dur,
                    total_distance_meters=total_dist,
                    transfers_count=1,
                    departure_time=dep_str,
                    arrival_time=arr_str,
                    is_verified=False,
                    provenance="SPATIALLY_DERIVED_THEME7_MTC",
                    legs=legs,
                )
            )

        return results

    def _build_metro_route(
        self, origin: Coordinates, destination: Coordinates, dep_time: Optional[str]
    ) -> Optional[RouteOption]:
        """
        Derive genuine Metro journey by projecting onto actual Operational_Metro_Stns.shp
        and slicing the actual corridor geometry from Operational_Metro.shp.
        """
        max_access_m = 1200  # maximum walking access to metro station

        # Find closest Theme7 Metro station to origin and destination
        orig_stn = None
        orig_min_d = float("inf")
        for stn in self.loader.metro_stations:
            d = haversine_meters(origin.lat, origin.lng, stn["lat"], stn["lng"])
            if d < orig_min_d and d <= max_access_m:
                orig_min_d = d
                orig_stn = stn

        dest_stn = None
        dest_min_d = float("inf")
        for stn in self.loader.metro_stations:
            d = haversine_meters(destination.lat, destination.lng, stn["lat"], stn["lng"])
            if d < dest_min_d and d <= max_access_m:
                dest_min_d = d
                dest_stn = stn

        if not orig_stn or not dest_stn or orig_stn["id"] == dest_stn["id"]:
            return None

        # Verify that both stations connect along an actual Metro corridor
        matched_corridor = None
        matched_slice = None
        metro_dist = 0

        for corr in self.loader.metro_corridors:
            d_o, p_o, idx_o, pos_o, _ = point_to_polyline_projection(
                orig_stn["lat"], orig_stn["lng"], corr["points"]
            )
            d_d, p_d, idx_d, pos_d, _ = point_to_polyline_projection(
                dest_stn["lat"], dest_stn["lng"], corr["points"]
            )

            # Both stations must be within 350m of this corridor line
            if d_o <= 350 and d_d <= 350:
                matched_corridor = corr
                metro_dist = int(abs(pos_d - pos_o))
                if pos_o <= pos_d:
                    matched_slice = slice_polyline(corr["points"], p_o, p_d, idx_o, idx_d)
                else:
                    rev_slice = slice_polyline(corr["points"], p_d, p_o, idx_d, idx_o)
                    matched_slice = list(reversed(rev_slice))
                break

        if not matched_corridor or not matched_slice or metro_dist < 500:
            return None

        fare, fare_note, is_ver, prov = FareService.calculate_metro_fare(metro_dist)
        walk1_dist = int(orig_min_d)
        walk2_dist = int(dest_min_d)
        walk1_dur = ETAService.calculate_duration_minutes(walk1_dist, "walking")
        walk2_dur = ETAService.calculate_duration_minutes(walk2_dist, "walking")
        metro_dur = ETAService.calculate_duration_minutes(metro_dist, "metro") + ETAService.TRANSFER_BUFFER_MINUTES["metro"]
        total_dur = walk1_dur + metro_dur + walk2_dur
        total_dist = walk1_dist + metro_dist + walk2_dist

        dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", total_dur)

        legs = [
            RouteLeg(
                mode="walking",
                from_name=origin.name or "Origin",
                to_name=orig_stn["name"],
                duration_minutes=walk1_dur,
                distance_meters=walk1_dist,
                fare=0.0,
                fare_note="Walking to Metro Station",
                is_estimated=False,
                is_verified=True,
                provenance="Pedestrian Access",
                polyline=[[origin.lat, origin.lng], [orig_stn["lat"], orig_stn["lng"]]],
            ),
            RouteLeg(
                mode="metro",
                route_number=f"CMRL {matched_corridor['corridor']}",
                from_name=orig_stn["name"],
                to_name=dest_stn["name"],
                duration_minutes=metro_dur,
                distance_meters=metro_dist,
                fare=fare,
                fare_note=fare_note,
                is_estimated=False,
                is_verified=True,
                provenance="Theme7.Public_Transport.Metro_Rail.Operational_Metro",
                polyline=matched_slice,
            ),
            RouteLeg(
                mode="walking",
                from_name=dest_stn["name"],
                to_name=destination.name or "Destination",
                duration_minutes=walk2_dur,
                distance_meters=walk2_dist,
                fare=0.0,
                fare_note="Walking from Metro Station to Destination",
                is_estimated=False,
                is_verified=True,
                provenance="Pedestrian Access",
                polyline=[[dest_stn["lat"], dest_stn["lng"]], [destination.lat, destination.lng]],
            ),
        ]

        return RouteOption(
            route_id=f"r_metro_{uuid.uuid4().hex[:6]}",
            summary=f"Chennai Metro ({matched_corridor['corridor']}: {orig_stn['raw_name']} ➔ {dest_stn['raw_name']})",
            total_fare=fare,
            total_duration_minutes=total_dur,
            total_distance_meters=total_dist,
            transfers_count=1,
            departure_time=dep_str,
            arrival_time=arr_str,
            is_verified=True,
            provenance="Theme7.Operational_Metro",
            legs=legs,
        )

    def _build_suburban_route(
        self, origin: Coordinates, destination: Coordinates, dep_time: Optional[str]
    ) -> Optional[RouteOption]:
        """
        Derive genuine Suburban railway journey from actual Suburban Stations.kml
        and sliced tracks from Rail_Network_Updated.shp.
        """
        max_access_m = 1500  # maximum walking access to suburban station

        orig_stn = None
        orig_min_d = float("inf")
        for stn in self.loader.suburban_stations:
            d = haversine_meters(origin.lat, origin.lng, stn["lat"], stn["lng"])
            if d < orig_min_d and d <= max_access_m:
                orig_min_d = d
                orig_stn = stn

        dest_stn = None
        dest_min_d = float("inf")
        for stn in self.loader.suburban_stations:
            d = haversine_meters(destination.lat, destination.lng, stn["lat"], stn["lng"])
            if d < dest_min_d and d <= max_access_m:
                dest_min_d = d
                dest_stn = stn

        if not orig_stn or not dest_stn or orig_stn["id"] == dest_stn["id"]:
            return None

        # Verify both stations connect along an actual suburban track
        matched_track = None
        matched_slice = None
        rail_dist = 0

        for track in self.loader.suburban_tracks:
            d_o, p_o, idx_o, pos_o, _ = point_to_polyline_projection(
                orig_stn["lat"], orig_stn["lng"], track["points"]
            )
            d_d, p_d, idx_d, pos_d, _ = point_to_polyline_projection(
                dest_stn["lat"], dest_stn["lng"], track["points"]
            )

            # Both stations within 600m of this track
            if d_o <= 600 and d_d <= 600:
                matched_track = track
                rail_dist = int(abs(pos_d - pos_o))
                if pos_o <= pos_d:
                    matched_slice = slice_polyline(track["points"], p_o, p_d, idx_o, idx_d)
                else:
                    rev_slice = slice_polyline(track["points"], p_d, p_o, idx_d, idx_o)
                    matched_slice = list(reversed(rev_slice))
                break

        if not matched_track or not matched_slice or rail_dist < 800:
            return None

        fare, fare_note, is_ver, prov = FareService.calculate_suburban_fare(rail_dist, is_ac_emu=False)
        walk1_dist = int(orig_min_d)
        walk2_dist = int(dest_min_d)
        walk1_dur = ETAService.calculate_duration_minutes(walk1_dist, "walking")
        walk2_dur = ETAService.calculate_duration_minutes(walk2_dist, "walking")
        rail_dur = ETAService.calculate_duration_minutes(rail_dist, "suburban_train") + ETAService.TRANSFER_BUFFER_MINUTES["suburban_train"]
        total_dur = walk1_dur + rail_dur + walk2_dur
        total_dist = walk1_dist + rail_dist + walk2_dist

        dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", total_dur)

        legs = [
            RouteLeg(
                mode="walking",
                from_name=origin.name or "Origin",
                to_name=orig_stn["name"],
                duration_minutes=walk1_dur,
                distance_meters=walk1_dist,
                fare=0.0,
                fare_note="Walking to Suburban Station",
                is_estimated=False,
                is_verified=True,
                provenance="Pedestrian Access",
                polyline=[[origin.lat, origin.lng], [orig_stn["lat"], orig_stn["lng"]]],
            ),
            RouteLeg(
                mode="suburban_train",
                route_number=f"Southern Railway {matched_track['type']}",
                from_name=orig_stn["name"],
                to_name=dest_stn["name"],
                duration_minutes=rail_dur,
                distance_meters=rail_dist,
                fare=fare,
                fare_note=fare_note,
                is_estimated=False,
                is_verified=True,
                provenance="Theme7.Public_Transport.Suburban_Rail.Rail_Network_Updated",
                polyline=matched_slice,
            ),
            RouteLeg(
                mode="walking",
                from_name=dest_stn["name"],
                to_name=destination.name or "Destination",
                duration_minutes=walk2_dur,
                distance_meters=walk2_dist,
                fare=0.0,
                fare_note="Walking from Suburban Station to Destination",
                is_estimated=False,
                is_verified=True,
                provenance="Pedestrian Access",
                polyline=[[dest_stn["lat"], dest_stn["lng"]], [destination.lat, destination.lng]],
            ),
        ]

        return RouteOption(
            route_id=f"r_sub_{uuid.uuid4().hex[:6]}",
            summary=f"Suburban Rail ({matched_track['type']}: {orig_stn['raw_name']} ➔ {dest_stn['raw_name']})",
            total_fare=fare,
            total_duration_minutes=total_dur,
            total_distance_meters=total_dist,
            transfers_count=1,
            departure_time=dep_str,
            arrival_time=arr_str,
            is_verified=True,
            provenance="Theme7.Rail_Network_Updated",
            legs=legs,
        )
