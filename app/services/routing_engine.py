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
from app.services.fare_service import (
    FareService,
    MTC_EFFECTIVE_DATE,
    MTC_SOURCE_URL,
)
from app.services.eta_service import ETAService

class MultimodalRoutingEngine:
    def __init__(self, data_loader: TransitDataLoader):
        self.loader = data_loader

    def _find_closest_stop_name(self, lat: float, lng: float, fallback: str = "MTC Stop") -> str:
        stop_match = self.loader.find_nearest_bus_stop(lat, lng, max_radius_m=800)
        if stop_match:
            return f"{stop_match[0]['name']} (MTC Stop)"
        return fallback

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
            bus_routes = self._build_mtc_bus_routes(
                origin, destination, gender, request.departure_time, request=request
            )
            routes.extend(bus_routes)

        # 3. Chennai Metro (Real Theme7 Metro Station & Corridor Slicing with Interchange)
        if "metro" in allowed_modes:
            metro_route = self._build_metro_route(origin, destination, request.departure_time)
            if metro_route:
                routes.append(metro_route)

        # 4. Suburban Railway (Real Theme7 Suburban Stations & Track Slicing)
        if "suburban_train" in allowed_modes:
            suburban_route = self._build_suburban_route(origin, destination, request.departure_time)
            if suburban_route:
                routes.append(suburban_route)

        # 5. Multimodal Combinations: MTC Bus + Metro & Metro + MTC Bus
        if "bus" in allowed_modes and "metro" in allowed_modes:
            bus_metro_routes = self._build_bus_metro_multimodal_routes(
                origin, destination, gender, request.departure_time, request=request
            )
            routes.extend(bus_metro_routes)

            metro_bus_routes = self._build_metro_bus_multimodal_routes(
                origin, destination, gender, request.departure_time, request=request
            )
            routes.extend(metro_bus_routes)

        # 6. Multimodal Combinations: Suburban Railway + Metro
        if "suburban_train" in allowed_modes and "metro" in allowed_modes:
            suburban_metro_routes = self._build_suburban_metro_multimodal_routes(
                origin, destination, request.departure_time
            )
            routes.extend(suburban_metro_routes)

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
        self,
        origin: Coordinates,
        destination: Coordinates,
        gender: str,
        dep_time: Optional[str],
        request: Optional[SearchRequest] = None,
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

            # Determine stage and service_type
            req_stage = request.stage if request and request.stage else route.get("stage")
            req_stype = request.service_type if request and request.service_type else route.get("service_type")
            canonical_stype = FareService.normalize_service_type(req_stype) if req_stype else None

            # Calculate MTC fare using exact stage lookup when stage is known
            if req_stage is not None and canonical_stype is not None:
                fare, fare_note, fare_is_ver, fare_prov = FareService.calculate_mtc_bus_fare_by_stage(
                    stage=req_stage, service_type=canonical_stype, gender=gender
                )
                bus_type_val = canonical_stype
                fare_status_val = "free_scheme" if (fare == 0.0 and fare_is_ver) else ("verified" if fare_is_ver else "unavailable")
                stage_count_val = req_stage
                eff_date_val = MTC_EFFECTIVE_DATE
            elif req_stage is not None and canonical_stype is None:
                fare = 0.0
                fare_note = f"MTC bus fare unavailable: stage is {req_stage}, but service type is unknown"
                fare_is_ver = False
                fare_prov = f"Official MTC Stage Fare Table (Effective {MTC_EFFECTIVE_DATE}, {MTC_SOURCE_URL}); service type not established"
                bus_type_val = "unknown"
                fare_status_val = "unavailable"
                stage_count_val = req_stage
                eff_date_val = MTC_EFFECTIVE_DATE
            elif canonical_stype == "Ordinary Services" and gender.lower().strip() == "female":
                # Eligible women travel free under Vidiyal Payana Thittam on Ordinary Services regardless of stage
                fare = 0.0
                fare_note = "Free travel under Vidiyal Payana Thittam (MTC Ordinary Service)"
                fare_is_ver = True
                fare_prov = "Official Tamil Nadu Government Scheme: Vidiyal Payana Thittam (MTC Ordinary Services)"
                bus_type_val = "Ordinary Services"
                fare_status_val = "free_scheme"
                stage_count_val = None
                eff_date_val = MTC_EFFECTIVE_DATE
            else:
                # Stage number is unavailable (do not fabricate from km or route geometry)
                fare = 0.0
                reasons = []
                if req_stage is None:
                    reasons.append("stage number not established for corridor")
                if canonical_stype is None:
                    reasons.append("service type unknown")
                fare_note = f"MTC bus fare unavailable: {', '.join(reasons)}"
                fare_is_ver = False
                fare_prov = (
                    f"Official MTC Stage Fare Table (Effective {MTC_EFFECTIVE_DATE}, {MTC_SOURCE_URL}); "
                    "Theme7 dataset lacks stop-to-stage sequence mapping"
                )
                bus_type_val = canonical_stype or "unknown"
                fare_status_val = "unavailable"
                stage_count_val = None
                eff_date_val = MTC_EFFECTIVE_DATE

            legs = [
                RouteLeg(
                    mode="walking",
                    from_name=origin.name or "Origin",
                    to_name=orig_stop_name,
                    duration_minutes=walk1_dur,
                    distance_meters=walk1_dist,
                    fare=0.0,
                    fare_note="Walking to MTC bus boarding location",
                    fare_status="zero_fare",
                    is_estimated=False,
                    is_verified=True,
                    provenance="Pedestrian Access",
                    polyline=[[origin.lat, origin.lng], [p_orig[0], p_orig[1]]],
                ),
                RouteLeg(
                    mode="bus",
                    route_number=route["route_num"],
                    bus_type=bus_type_val,
                    from_name=orig_stop_name,
                    to_name=dest_stop_name,
                    duration_minutes=bus_dur,
                    distance_meters=bus_dist,
                    fare=fare,
                    fare_note=f"{fare_note} [Spatially Derived Theme7 Corridor]",
                    fare_status=fare_status_val,
                    fare_effective_date=eff_date_val,
                    stage_count=stage_count_val,
                    is_estimated=False,
                    is_verified=fare_is_ver,
                    provenance=f"Theme7.Public_Transport.MTC.routes_merged (Shapefile Geometry Sliced) | {fare_prov}",
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
                    fare_status="zero_fare",
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
                    is_verified=fare_is_ver,
                    provenance="SPATIALLY_DERIVED_THEME7_MTC",
                    fare_status=fare_status_val,
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
        Supports both direct single-corridor lines and interchange connections (e.g. at Central or Alandur).
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

        # Exact station-to-station fare lookup
        orig_cmrl = orig_stn.get("cmrl_name") or orig_stn["name"]
        dest_cmrl = dest_stn.get("cmrl_name") or dest_stn["name"]
        fare, fare_note, is_ver, prov, fare_status = FareService.calculate_metro_fare_by_station(orig_cmrl, dest_cmrl)

        walk1_dist = int(orig_min_d)
        walk2_dist = int(dest_min_d)
        walk1_dur = ETAService.calculate_duration_minutes(walk1_dist, "walking")
        walk2_dur = ETAService.calculate_duration_minutes(walk2_dist, "walking")

        # 1. Check if both stations connect along a direct single corridor
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

        if matched_corridor and matched_slice and metro_dist >= 500:
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
                    fare_status="zero_fare",
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
                    fare_status=fare_status,
                    is_estimated=True,
                    is_verified=is_ver,
                    provenance=f"Theme7.Public_Transport.Metro_Rail.Operational_Metro | {prov}",
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
                    fare_status="zero_fare",
                    is_estimated=False,
                    is_verified=True,
                    provenance="Pedestrian Access",
                    polyline=[[dest_stn["lat"], dest_stn["lng"]], [destination.lat, destination.lng]],
                ),
            ]

            orig_disp = orig_stn.get("cmrl_name", orig_stn["raw_name"]).title()
            dest_disp = dest_stn.get("cmrl_name", dest_stn["raw_name"]).title()
            return RouteOption(
                route_id=f"r_metro_{uuid.uuid4().hex[:6]}",
                summary=f"Chennai Metro ({matched_corridor['corridor']}: {orig_disp} ➔ {dest_disp})",
                total_fare=fare,
                total_duration_minutes=total_dur,
                total_distance_meters=total_dist,
                transfers_count=1,
                departure_time=dep_str,
                arrival_time=arr_str,
                is_verified=is_ver,
                provenance="Theme7.Operational_Metro",
                fare_status=fare_status,
                legs=legs,
            )

        # 2. Check for Interchange connection (Phase 1 Blue Line <-> Green Line)
        # Interchanges: Central Metro (metro_stn_17) or Alandur Metro (metro_stn_16)
        interchange_candidates = [
            s for s in self.loader.metro_stations if s["id"] in ("metro_stn_17", "metro_stn_16")
        ]
        best_interchange = None
        best_slice_1 = None
        best_slice_2 = None
        best_corr_1 = None
        best_corr_2 = None
        best_dist_1 = 0
        best_dist_2 = 0
        min_total_rail_dist = float("inf")

        for int_stn in interchange_candidates:
            if int_stn["id"] in (orig_stn["id"], dest_stn["id"]):
                continue
            for c1 in self.loader.metro_corridors:
                d_o, p_o, idx_o, pos_o, _ = point_to_polyline_projection(orig_stn["lat"], orig_stn["lng"], c1["points"])
                d_i1, p_i1, idx_i1, pos_i1, _ = point_to_polyline_projection(int_stn["lat"], int_stn["lng"], c1["points"])
                if d_o > 350 or d_i1 > 350:
                    continue

                for c2 in self.loader.metro_corridors:
                    if c1["id"] == c2["id"]:
                        continue
                    d_i2, p_i2, idx_i2, pos_i2, _ = point_to_polyline_projection(int_stn["lat"], int_stn["lng"], c2["points"])
                    d_d, p_d, idx_d, pos_d, _ = point_to_polyline_projection(dest_stn["lat"], dest_stn["lng"], c2["points"])
                    if d_i2 > 350 or d_d > 350:
                        continue

                    dist1 = int(abs(pos_i1 - pos_o))
                    dist2 = int(abs(pos_d - pos_i2))
                    tot_rail = dist1 + dist2

                    if tot_rail < min_total_rail_dist and dist1 >= 300 and dist2 >= 300:
                        min_total_rail_dist = tot_rail
                        best_interchange = int_stn
                        best_corr_1 = c1
                        best_corr_2 = c2
                        best_dist_1 = dist1
                        best_dist_2 = dist2

                        if pos_o <= pos_i1:
                            best_slice_1 = slice_polyline(c1["points"], p_o, p_i1, idx_o, idx_i1)
                        else:
                            best_slice_1 = list(reversed(slice_polyline(c1["points"], p_i1, p_o, idx_i1, idx_o)))

                        if pos_i2 <= pos_d:
                            best_slice_2 = slice_polyline(c2["points"], p_i2, p_d, idx_i2, idx_d)
                        else:
                            best_slice_2 = list(reversed(slice_polyline(c2["points"], p_d, p_i2, idx_d, idx_i2)))

        if not best_interchange or not best_slice_1 or not best_slice_2:
            return None

        # Build 5-leg interchange journey
        dur_1 = ETAService.calculate_duration_minutes(best_dist_1, "metro")
        transfer_dur = 3  # 3 minutes platform transfer buffer
        dur_2 = ETAService.calculate_duration_minutes(best_dist_2, "metro")
        total_metro_dur = dur_1 + transfer_dur + dur_2 + ETAService.TRANSFER_BUFFER_MINUTES["metro"]
        total_dur = walk1_dur + total_metro_dur + walk2_dur
        total_dist = walk1_dist + best_dist_1 + 150 + best_dist_2 + walk2_dist
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
                fare_status="zero_fare",
                is_estimated=False,
                is_verified=True,
                provenance="Pedestrian Access",
                polyline=[[origin.lat, origin.lng], [orig_stn["lat"], orig_stn["lng"]]],
            ),
            RouteLeg(
                mode="metro",
                route_number=f"CMRL {best_corr_1['corridor']}",
                from_name=orig_stn["name"],
                to_name=best_interchange["name"],
                duration_minutes=dur_1,
                distance_meters=best_dist_1,
                fare=fare,
                fare_note=f"{fare_note} (Includes interchange transfer)",
                fare_status=fare_status,
                is_estimated=True,
                is_verified=is_ver,
                provenance=f"Theme7.Operational_Metro | {prov}",
                polyline=best_slice_1,
            ),
            RouteLeg(
                mode="walking",
                from_name=best_interchange["name"],
                to_name=f"{best_interchange['name']} (Interchange)",
                duration_minutes=transfer_dur,
                distance_meters=150,
                fare=0.0,
                fare_note=f"Platform transfer at {best_interchange['name']}",
                fare_status="zero_fare",
                is_estimated=False,
                is_verified=True,
                provenance="Interchange Platform Link",
                polyline=[[best_interchange["lat"], best_interchange["lng"]], [best_interchange["lat"], best_interchange["lng"]]],
            ),
            RouteLeg(
                mode="metro",
                route_number=f"CMRL {best_corr_2['corridor']}",
                from_name=best_interchange["name"],
                to_name=dest_stn["name"],
                duration_minutes=dur_2,
                distance_meters=best_dist_2,
                fare=0.0,
                fare_note="Connected leg (included in single journey token)",
                fare_status="zero_fare",
                is_estimated=True,
                is_verified=is_ver,
                provenance=f"Theme7.Operational_Metro | {prov}",
                polyline=best_slice_2,
            ),
            RouteLeg(
                mode="walking",
                from_name=dest_stn["name"],
                to_name=destination.name or "Destination",
                duration_minutes=walk2_dur,
                distance_meters=walk2_dist,
                fare=0.0,
                fare_note="Walking from Metro Station to Destination",
                fare_status="zero_fare",
                is_estimated=False,
                is_verified=True,
                provenance="Pedestrian Access",
                polyline=[[dest_stn["lat"], dest_stn["lng"]], [destination.lat, destination.lng]],
            ),
        ]

        orig_disp = orig_stn.get("cmrl_name", orig_stn["raw_name"]).title()
        dest_disp = dest_stn.get("cmrl_name", dest_stn["raw_name"]).title()
        int_disp = best_interchange.get("cmrl_name", best_interchange["raw_name"]).title()
        summary = f"Chennai Metro ({orig_disp} ➔ {dest_disp} via {int_disp} Interchange)"
        return RouteOption(
            route_id=f"r_metro_{uuid.uuid4().hex[:6]}",
            summary=summary,
            total_fare=fare,
            total_duration_minutes=total_dur,
            total_distance_meters=total_dist,
            transfers_count=2,
            departure_time=dep_str,
            arrival_time=arr_str,
            is_verified=is_ver,
            provenance="Theme7.Operational_Metro (Interchange Connected)",
            fare_status=fare_status,
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

    def _build_bus_metro_multimodal_routes(
        self,
        origin: Coordinates,
        destination: Coordinates,
        gender: str,
        dep_time: Optional[str],
        request: Optional[SearchRequest] = None,
    ) -> List[RouteOption]:
        """
        Multimodal journey: Walking ➔ MTC Bus ➔ Walking Transfer ➔ Metro ➔ Walking.
        Connects origin to an interchange hub via MTC bus, then takes Metro to destination.
        """
        # Find metro station within walking access of destination
        dest_metro_stn = None
        dest_min_d = float("inf")
        for stn in self.loader.metro_stations:
            d = haversine_meters(destination.lat, destination.lng, stn["lat"], stn["lng"])
            if d < dest_min_d and d <= 1200:
                dest_min_d = d
                dest_metro_stn = stn

        if not dest_metro_stn:
            return []

        # Candidate multimodal transfer hubs (Metro stations with bus connections)
        candidate_hubs = [
            s for s in self.loader.metro_stations
            if s["id"] in ("metro_stn_17", "metro_stn_7", "metro_stn_29", "metro_stn_38", "metro_stn_14", "metro_stn_1", "metro_stn_16")
        ]

        results = []
        for hub in candidate_hubs:
            if hub["id"] == dest_metro_stn["id"]:
                continue

            # Check if Metro connects hub to dest_metro_stn
            metro_slice = None
            metro_corr = None
            metro_dist = 0
            for corr in self.loader.metro_corridors:
                d_h, p_h_m, idx_h, pos_h_m, _ = point_to_polyline_projection(hub["lat"], hub["lng"], corr["points"])
                d_d, p_d_m, idx_d, pos_d_m, _ = point_to_polyline_projection(dest_metro_stn["lat"], dest_metro_stn["lng"], corr["points"])
                if d_h <= 350 and d_d <= 350:
                    metro_corr = corr
                    metro_dist = int(abs(pos_d_m - pos_h_m))
                    if pos_h_m <= pos_d_m:
                        metro_slice = slice_polyline(corr["points"], p_h_m, p_d_m, idx_h, idx_d)
                    else:
                        metro_slice = list(reversed(slice_polyline(corr["points"], p_d_m, p_h_m, idx_d, idx_h)))
                    break

            if not metro_slice or metro_dist < 500:
                continue

            # Find matching bus routes from origin to this hub
            for r in self.loader.bus_routes:
                min_lat, min_lng, max_lat, max_lng = r["bbox"]
                margin = 0.01
                if not (min_lat - margin <= origin.lat <= max_lat + margin and min_lng - margin <= origin.lng <= max_lng + margin):
                    continue
                if not (min_lat - margin <= hub["lat"] <= max_lat + margin and min_lng - margin <= hub["lng"] <= max_lng + margin):
                    continue

                d_orig, p_orig, idx_o, pos_o, _ = point_to_polyline_projection(origin.lat, origin.lng, r["points"])
                if d_orig > 800:
                    continue
                d_hub, p_hub, idx_h_b, pos_h_b, _ = point_to_polyline_projection(hub["lat"], hub["lng"], r["points"])
                if d_hub > 350:
                    continue
                if pos_o < pos_h_b and (pos_h_b - pos_o) >= 800:
                    bus_dist = int(pos_h_b - pos_o)
                    bus_slice = slice_polyline(r["points"], p_orig, p_hub, idx_o, idx_h_b)

                    # Bus stop names
                    orig_stop_name = self._find_closest_stop_name(p_orig[0], p_orig[1])
                    hub_stop_name = self._find_closest_stop_name(p_hub[0], p_hub[1])

                    # Fares
                    bus_fare = 0.0
                    bus_fare_note = "MTC Bus Fare (Theme7 Spatially Derived)"
                    bus_is_ver = False
                    bus_status = "unavailable"

                    has_stage = request and request.stage is not None and isinstance(request.stage, int) and request.stage > 0
                    has_st = request and request.service_type is not None and bool(request.service_type.strip())
                    req_st = request.service_type.strip() if (request and request.service_type) else ""

                    if gender == "female" and has_st and req_st.lower() in ("ordinary", "ordinary services", "white_board", "white board"):
                        bus_fare = 0.0
                        bus_fare_note = "Free travel under Vidiyal Payana Thittam (MTC Ordinary Service)"
                        bus_is_ver = True
                        bus_status = "zero_fare"
                    elif has_stage and has_st:
                        bus_fare, bus_fare_note, bus_is_ver, _ = FareService.calculate_mtc_bus_fare_by_stage(
                            request.stage, req_st, gender=gender
                        )
                        bus_status = "verified" if bus_is_ver else "unavailable"

                    # Metro fare
                    m_fare, m_note, m_ver, m_prov, m_status = FareService.calculate_metro_fare_by_station(
                        hub.get("cmrl_name"), dest_metro_stn.get("cmrl_name")
                    )

                    # Durations
                    walk1_dist = int(d_orig)
                    walk1_dur = ETAService.calculate_duration_minutes(walk1_dist, "walking")
                    bus_dur = ETAService.calculate_duration_minutes(bus_dist, "bus") + ETAService.TRANSFER_BUFFER_MINUTES["bus"]
                    transfer_dist = int(d_hub)
                    transfer_dur = max(3, ETAService.calculate_duration_minutes(transfer_dist, "walking"))
                    metro_dur = ETAService.calculate_duration_minutes(metro_dist, "metro") + ETAService.TRANSFER_BUFFER_MINUTES["metro"]
                    walk2_dist = int(dest_min_d)
                    walk2_dur = ETAService.calculate_duration_minutes(walk2_dist, "walking")

                    total_dur = walk1_dur + bus_dur + transfer_dur + metro_dur + walk2_dur
                    total_dist = walk1_dist + bus_dist + transfer_dist + metro_dist + walk2_dist
                    total_fare = bus_fare + m_fare
                    dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", total_dur)

                    legs = [
                        RouteLeg(
                            mode="walking",
                            from_name=origin.name or "Origin",
                            to_name=orig_stop_name,
                            duration_minutes=walk1_dur,
                            distance_meters=walk1_dist,
                            fare=0.0,
                            fare_note="Walking to MTC bus stop",
                            fare_status="zero_fare",
                            is_estimated=False,
                            is_verified=True,
                            provenance="Pedestrian Access",
                            polyline=[[origin.lat, origin.lng], [p_orig[0], p_orig[1]]],
                        ),
                        RouteLeg(
                            mode="bus",
                            route_number=r["route_num"],
                            bus_type=req_st or "unknown",
                            from_name=orig_stop_name,
                            to_name=hub_stop_name,
                            duration_minutes=bus_dur,
                            distance_meters=bus_dist,
                            fare=bus_fare,
                            fare_note=bus_fare_note,
                            fare_status=bus_status,
                            is_estimated=True,
                            is_verified=bus_is_ver,
                            provenance="Theme7.Public_Transport.MTC.routes_merged",
                            polyline=bus_slice,
                        ),
                        RouteLeg(
                            mode="walking",
                            from_name=hub_stop_name,
                            to_name=hub["name"],
                            duration_minutes=transfer_dur,
                            distance_meters=transfer_dist,
                            fare=0.0,
                            fare_note=f"Multimodal transfer: Bus ➔ Metro at {hub['name']}",
                            fare_status="zero_fare",
                            is_estimated=False,
                            is_verified=True,
                            provenance="Intermodal Pedestrian Transfer Link",
                            polyline=[[p_hub[0], p_hub[1]], [hub["lat"], hub["lng"]]],
                        ),
                        RouteLeg(
                            mode="metro",
                            route_number=f"CMRL {metro_corr['corridor']}",
                            from_name=hub["name"],
                            to_name=dest_metro_stn["name"],
                            duration_minutes=metro_dur,
                            distance_meters=metro_dist,
                            fare=m_fare,
                            fare_note=m_note,
                            fare_status=m_status,
                            is_estimated=True,
                            is_verified=m_ver,
                            provenance=f"Theme7.Operational_Metro | {m_prov}",
                            polyline=metro_slice,
                        ),
                        RouteLeg(
                            mode="walking",
                            from_name=dest_metro_stn["name"],
                            to_name=destination.name or "Destination",
                            duration_minutes=walk2_dur,
                            distance_meters=walk2_dist,
                            fare=0.0,
                            fare_note="Walking from Metro station to Destination",
                            fare_status="zero_fare",
                            is_estimated=False,
                            is_verified=True,
                            provenance="Pedestrian Access",
                            polyline=[[dest_metro_stn["lat"], dest_metro_stn["lng"]], [destination.lat, destination.lng]],
                        ),
                    ]

                    hub_disp = hub.get("cmrl_name", hub["raw_name"]).title()
                    dest_disp = dest_metro_stn.get("cmrl_name", dest_metro_stn["raw_name"]).title()
                    summary = f"Multimodal Combo: MTC Bus {r['route_num']} ➔ Transfer at {hub_disp} ➔ Metro ({dest_disp})"
                    opt_status = "verified" if (bus_is_ver and m_ver) else ("partially_unavailable" if (not bus_is_ver and m_ver) else "unavailable")
                    results.append(
                        RouteOption(
                            route_id=f"r_multi_bm_{r['route_num']}_{uuid.uuid4().hex[:4]}",
                            summary=summary,
                            total_fare=total_fare,
                            total_duration_minutes=total_dur,
                            total_distance_meters=total_dist,
                            transfers_count=2,
                            departure_time=dep_str,
                            arrival_time=arr_str,
                            is_verified=bus_is_ver and m_ver,
                            provenance="THEME7_MULTIMODAL_BUS_METRO",
                            fare_status=opt_status,
                            legs=legs,
                        )
                    )
                    break # Take top route for this hub

        return results[:2]

    def _build_metro_bus_multimodal_routes(
        self,
        origin: Coordinates,
        destination: Coordinates,
        gender: str,
        dep_time: Optional[str],
        request: Optional[SearchRequest] = None,
    ) -> List[RouteOption]:
        """
        Multimodal journey: Walking ➔ Metro ➔ Walking Transfer ➔ MTC Bus ➔ Walking.
        Connects origin via Metro to an interchange hub, then takes MTC bus to destination.
        """
        orig_metro_stn = None
        orig_min_d = float("inf")
        for stn in self.loader.metro_stations:
            d = haversine_meters(origin.lat, origin.lng, stn["lat"], stn["lng"])
            if d < orig_min_d and d <= 1200:
                orig_min_d = d
                orig_metro_stn = stn

        if not orig_metro_stn:
            return []

        candidate_hubs = [
            s for s in self.loader.metro_stations
            if s["id"] in ("metro_stn_17", "metro_stn_7", "metro_stn_29", "metro_stn_38", "metro_stn_14", "metro_stn_1", "metro_stn_16")
        ]

        results = []
        for hub in candidate_hubs:
            if hub["id"] == orig_metro_stn["id"]:
                continue

            metro_slice = None
            metro_corr = None
            metro_dist = 0
            for corr in self.loader.metro_corridors:
                d_o, p_o_m, idx_o, pos_o_m, _ = point_to_polyline_projection(orig_metro_stn["lat"], orig_metro_stn["lng"], corr["points"])
                d_h, p_h_m, idx_h, pos_h_m, _ = point_to_polyline_projection(hub["lat"], hub["lng"], corr["points"])
                if d_o <= 350 and d_h <= 350:
                    metro_corr = corr
                    metro_dist = int(abs(pos_h_m - pos_o_m))
                    if pos_o_m <= pos_h_m:
                        metro_slice = slice_polyline(corr["points"], p_o_m, p_h_m, idx_o, idx_h)
                    else:
                        metro_slice = list(reversed(slice_polyline(corr["points"], p_h_m, p_o_m, idx_h, idx_o)))
                    break

            if not metro_slice or metro_dist < 500:
                continue

            # Find matching bus routes from hub to destination
            for r in self.loader.bus_routes:
                min_lat, min_lng, max_lat, max_lng = r["bbox"]
                margin = 0.01
                if not (min_lat - margin <= hub.lat if hasattr(hub, 'lat') else hub['lat'] <= max_lat + margin):
                    continue
                d_hub, p_hub, idx_h_b, pos_h_b, _ = point_to_polyline_projection(hub["lat"], hub["lng"], r["points"])
                if d_hub > 350:
                    continue
                d_dest, p_dest, idx_d_b, pos_d_b, _ = point_to_polyline_projection(destination.lat, destination.lng, r["points"])
                if d_dest > 800:
                    continue
                if pos_h_b < pos_d_b and (pos_d_b - pos_h_b) >= 800:
                    bus_dist = int(pos_d_b - pos_h_b)
                    bus_slice = slice_polyline(r["points"], p_hub, p_dest, idx_h_b, idx_d_b)

                    hub_stop_name = self._find_closest_stop_name(p_hub[0], p_hub[1])
                    dest_stop_name = self._find_closest_stop_name(p_dest[0], p_dest[1])

                    # Fares
                    m_fare, m_note, m_ver, m_prov, m_status = FareService.calculate_metro_fare_by_station(
                        orig_metro_stn.get("cmrl_name"), hub.get("cmrl_name")
                    )

                    bus_fare = 0.0
                    bus_fare_note = "MTC Bus Fare (Theme7 Spatially Derived)"
                    bus_is_ver = False
                    bus_status = "unavailable"

                    has_stage = request and request.stage is not None and isinstance(request.stage, int) and request.stage > 0
                    has_st = request and request.service_type is not None and bool(request.service_type.strip())
                    req_st = request.service_type.strip() if (request and request.service_type) else ""

                    if gender == "female" and has_st and req_st.lower() in ("ordinary", "ordinary services", "white_board", "white board"):
                        bus_fare = 0.0
                        bus_fare_note = "Free travel under Vidiyal Payana Thittam (MTC Ordinary Service)"
                        bus_is_ver = True
                        bus_status = "zero_fare"
                    elif has_stage and has_st:
                        bus_fare, bus_fare_note, bus_is_ver, _ = FareService.calculate_mtc_bus_fare_by_stage(
                            request.stage, req_st, gender=gender
                        )
                        bus_status = "verified" if bus_is_ver else "unavailable"

                    # Durations
                    walk1_dist = int(orig_min_d)
                    walk1_dur = ETAService.calculate_duration_minutes(walk1_dist, "walking")
                    metro_dur = ETAService.calculate_duration_minutes(metro_dist, "metro") + ETAService.TRANSFER_BUFFER_MINUTES["metro"]
                    transfer_dist = int(d_hub)
                    transfer_dur = max(3, ETAService.calculate_duration_minutes(transfer_dist, "walking"))
                    bus_dur = ETAService.calculate_duration_minutes(bus_dist, "bus") + ETAService.TRANSFER_BUFFER_MINUTES["bus"]
                    walk2_dist = int(d_dest)
                    walk2_dur = ETAService.calculate_duration_minutes(walk2_dist, "walking")

                    total_dur = walk1_dur + metro_dur + transfer_dur + bus_dur + walk2_dur
                    total_dist = walk1_dist + metro_dist + transfer_dist + bus_dist + walk2_dist
                    total_fare = m_fare + bus_fare
                    dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", total_dur)

                    legs = [
                        RouteLeg(
                            mode="walking",
                            from_name=origin.name or "Origin",
                            to_name=orig_metro_stn["name"],
                            duration_minutes=walk1_dur,
                            distance_meters=walk1_dist,
                            fare=0.0,
                            fare_note="Walking to Metro station",
                            fare_status="zero_fare",
                            is_estimated=False,
                            is_verified=True,
                            provenance="Pedestrian Access",
                            polyline=[[origin.lat, origin.lng], [orig_metro_stn["lat"], orig_metro_stn["lng"]]],
                        ),
                        RouteLeg(
                            mode="metro",
                            route_number=f"CMRL {metro_corr['corridor']}",
                            from_name=orig_metro_stn["name"],
                            to_name=hub["name"],
                            duration_minutes=metro_dur,
                            distance_meters=metro_dist,
                            fare=m_fare,
                            fare_note=m_note,
                            fare_status=m_status,
                            is_estimated=True,
                            is_verified=m_ver,
                            provenance=f"Theme7.Operational_Metro | {m_prov}",
                            polyline=metro_slice,
                        ),
                        RouteLeg(
                            mode="walking",
                            from_name=hub["name"],
                            to_name=hub_stop_name,
                            duration_minutes=transfer_dur,
                            distance_meters=transfer_dist,
                            fare=0.0,
                            fare_note=f"Multimodal transfer: Metro ➔ Bus at {hub['name']}",
                            fare_status="zero_fare",
                            is_estimated=False,
                            is_verified=True,
                            provenance="Intermodal Pedestrian Transfer Link",
                            polyline=[[hub["lat"], hub["lng"]], [p_hub[0], p_hub[1]]],
                        ),
                        RouteLeg(
                            mode="bus",
                            route_number=r["route_num"],
                            bus_type=req_st or "unknown",
                            from_name=hub_stop_name,
                            to_name=dest_stop_name,
                            duration_minutes=bus_dur,
                            distance_meters=bus_dist,
                            fare=bus_fare,
                            fare_note=bus_fare_note,
                            fare_status=bus_status,
                            is_estimated=True,
                            is_verified=bus_is_ver,
                            provenance="Theme7.Public_Transport.MTC.routes_merged",
                            polyline=bus_slice,
                        ),
                        RouteLeg(
                            mode="walking",
                            from_name=dest_stop_name,
                            to_name=destination.name or "Destination",
                            duration_minutes=walk2_dur,
                            distance_meters=walk2_dist,
                            fare=0.0,
                            fare_note="Walking from bus stop to Destination",
                            fare_status="zero_fare",
                            is_estimated=False,
                            is_verified=True,
                            provenance="Pedestrian Access",
                            polyline=[[p_dest[0], p_dest[1]], [destination.lat, destination.lng]],
                        ),
                    ]

                    orig_disp = orig_metro_stn.get("cmrl_name", orig_metro_stn["raw_name"]).title()
                    hub_disp = hub.get("cmrl_name", hub["raw_name"]).title()
                    summary = f"Multimodal Combo: Metro ({orig_disp}) ➔ Transfer at {hub_disp} ➔ MTC Bus {r['route_num']}"
                    opt_status = "verified" if (bus_is_ver and m_ver) else ("partially_unavailable" if (not bus_is_ver and m_ver) else "unavailable")
                    results.append(
                        RouteOption(
                            route_id=f"r_multi_mb_{r['route_num']}_{uuid.uuid4().hex[:4]}",
                            summary=summary,
                            total_fare=total_fare,
                            total_duration_minutes=total_dur,
                            total_distance_meters=total_dist,
                            transfers_count=2,
                            departure_time=dep_str,
                            arrival_time=arr_str,
                            is_verified=bus_is_ver and m_ver,
                            provenance="THEME7_MULTIMODAL_METRO_BUS",
                            fare_status=opt_status,
                            legs=legs,
                        )
                    )
                    break

        return results[:2]

    def _build_suburban_metro_multimodal_routes(
        self,
        origin: Coordinates,
        destination: Coordinates,
        dep_time: Optional[str],
    ) -> List[RouteOption]:
        """
        Multimodal journey: Walking ➔ Suburban Rail ➔ Walking Transfer ➔ Metro ➔ Walking.
        Connects suburban rail to major interchange hubs (Central, Egmore, Guindy, St. Thomas Mount).
        """
        orig_sub_stn = None
        orig_min_d = float("inf")
        for stn in self.loader.suburban_stations:
            d = haversine_meters(origin.lat, origin.lng, stn["lat"], stn["lng"])
            if d < orig_min_d and d <= 1500:
                orig_min_d = d
                orig_sub_stn = stn

        dest_metro_stn = None
        dest_min_d = float("inf")
        for stn in self.loader.metro_stations:
            d = haversine_meters(destination.lat, destination.lng, stn["lat"], stn["lng"])
            if d < dest_min_d and d <= 1200:
                dest_min_d = d
                dest_metro_stn = stn

        if not orig_sub_stn or not dest_metro_stn:
            return []

        # Interchanges between Suburban and Metro
        interchanges = [
            ("Central", "metro_stn_17", 13.0827, 80.2755),
            ("Egmore", "metro_stn_7", 13.0789, 80.2608),
            ("Guindy", "metro_stn_38", 13.0094, 80.2133),
            ("St. Thomas Mount", "metro_stn_15", 12.9946, 80.1974),
        ]

        results = []
        for int_name, metro_id, int_lat, int_lng in interchanges:
            if metro_id == dest_metro_stn["id"]:
                continue
            hub_metro = next((s for s in self.loader.metro_stations if s["id"] == metro_id), None)
            if not hub_metro:
                continue

            # Check if suburban connects orig_sub_stn to an interchange suburban station
            matched_sub_stn = None
            for ss in self.loader.suburban_stations:
                if haversine_meters(int_lat, int_lng, ss["lat"], ss["lng"]) <= 350:
                    matched_sub_stn = ss
                    break
            if not matched_sub_stn or matched_sub_stn["id"] == orig_sub_stn["id"]:
                continue

            # Check track connection
            matched_track = None
            matched_sub_slice = None
            rail_dist = 0
            for track in self.loader.suburban_tracks:
                d_o, p_o, idx_o, pos_o, _ = point_to_polyline_projection(orig_sub_stn["lat"], orig_sub_stn["lng"], track["points"])
                d_d, p_d, idx_d, pos_d, _ = point_to_polyline_projection(matched_sub_stn["lat"], matched_sub_stn["lng"], track["points"])
                if d_o <= 350 and d_d <= 350:
                    matched_track = track
                    rail_dist = int(abs(pos_d - pos_o))
                    if pos_o <= pos_d:
                        matched_sub_slice = slice_polyline(track["points"], p_o, p_d, idx_o, idx_d)
                    else:
                        matched_sub_slice = list(reversed(slice_polyline(track["points"], p_d, p_o, idx_d, idx_o)))
                    break

            if not matched_track or not matched_sub_slice or rail_dist < 500:
                continue

            # Check metro connection from hub_metro to dest_metro_stn
            metro_slice = None
            metro_corr = None
            metro_dist = 0
            for corr in self.loader.metro_corridors:
                d_h, p_h_m, idx_h, pos_h_m, _ = point_to_polyline_projection(hub_metro["lat"], hub_metro["lng"], corr["points"])
                d_d, p_d_m, idx_d, pos_d_m, _ = point_to_polyline_projection(dest_metro_stn["lat"], dest_metro_stn["lng"], corr["points"])
                if d_h <= 350 and d_d <= 350:
                    metro_corr = corr
                    metro_dist = int(abs(pos_d_m - pos_h_m))
                    if pos_h_m <= pos_d_m:
                        metro_slice = slice_polyline(corr["points"], p_h_m, p_d_m, idx_h, idx_d)
                    else:
                        metro_slice = list(reversed(slice_polyline(corr["points"], p_d_m, p_h_m, idx_d, idx_h)))
                    break

            if not metro_slice or metro_dist < 500:
                continue

            # Fares
            sub_fare, sub_note, sub_ver, sub_prov = FareService.calculate_suburban_fare(rail_dist)
            m_fare, m_note, m_ver, m_prov, m_status = FareService.calculate_metro_fare_by_station(
                hub_metro.get("cmrl_name"), dest_metro_stn.get("cmrl_name")
            )

            # Durations
            walk1_dist = int(orig_min_d)
            walk1_dur = ETAService.calculate_duration_minutes(walk1_dist, "walking")
            rail_dur = ETAService.calculate_duration_minutes(rail_dist, "suburban_train") + ETAService.TRANSFER_BUFFER_MINUTES["suburban_train"]
            transfer_dist = 200
            transfer_dur = 4
            metro_dur = ETAService.calculate_duration_minutes(metro_dist, "metro") + ETAService.TRANSFER_BUFFER_MINUTES["metro"]
            walk2_dist = int(dest_min_d)
            walk2_dur = ETAService.calculate_duration_minutes(walk2_dist, "walking")

            total_dur = walk1_dur + rail_dur + transfer_dur + metro_dur + walk2_dur
            total_dist = walk1_dist + rail_dist + transfer_dist + metro_dist + walk2_dist
            total_fare = sub_fare + m_fare
            dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", total_dur)

            legs = [
                RouteLeg(
                    mode="walking",
                    from_name=origin.name or "Origin",
                    to_name=orig_sub_stn["name"],
                    duration_minutes=walk1_dur,
                    distance_meters=walk1_dist,
                    fare=0.0,
                    fare_note="Walking to Suburban Station",
                    fare_status="zero_fare",
                    is_estimated=False,
                    is_verified=True,
                    provenance="Pedestrian Access",
                    polyline=[[origin.lat, origin.lng], [orig_sub_stn["lat"], orig_sub_stn["lng"]]],
                ),
                RouteLeg(
                    mode="suburban_train",
                    route_number=f"Southern Railway {matched_track['type']}",
                    from_name=orig_sub_stn["name"],
                    to_name=matched_sub_stn["name"],
                    duration_minutes=rail_dur,
                    distance_meters=rail_dist,
                    fare=sub_fare,
                    fare_note=sub_note,
                    fare_status="verified",
                    is_estimated=True,
                    is_verified=sub_ver,
                    provenance="Theme7.Public_Transport.Suburban_Rail.Rail_Network_Updated",
                    polyline=matched_sub_slice,
                ),
                RouteLeg(
                    mode="walking",
                    from_name=matched_sub_stn["name"],
                    to_name=hub_metro["name"],
                    duration_minutes=transfer_dur,
                    distance_meters=transfer_dist,
                    fare=0.0,
                    fare_note=f"Multimodal transfer: Suburban ➔ Metro at {int_name}",
                    fare_status="zero_fare",
                    is_estimated=False,
                    is_verified=True,
                    provenance="Intermodal Pedestrian Transfer Link",
                    polyline=[[matched_sub_stn["lat"], matched_sub_stn["lng"]], [hub_metro["lat"], hub_metro["lng"]]],
                ),
                RouteLeg(
                    mode="metro",
                    route_number=f"CMRL {metro_corr['corridor']}",
                    from_name=hub_metro["name"],
                    to_name=dest_metro_stn["name"],
                    duration_minutes=metro_dur,
                    distance_meters=metro_dist,
                    fare=m_fare,
                    fare_note=m_note,
                    fare_status=m_status,
                    is_estimated=True,
                    is_verified=m_ver,
                    provenance=f"Theme7.Operational_Metro | {m_prov}",
                    polyline=metro_slice,
                ),
                RouteLeg(
                    mode="walking",
                    from_name=dest_metro_stn["name"],
                    to_name=destination.name or "Destination",
                    duration_minutes=walk2_dur,
                    distance_meters=walk2_dist,
                    fare=0.0,
                    fare_note="Walking from Metro station to Destination",
                    fare_status="zero_fare",
                    is_estimated=False,
                    is_verified=True,
                    provenance="Pedestrian Access",
                    polyline=[[dest_metro_stn["lat"], dest_metro_stn["lng"]], [destination.lat, destination.lng]],
                ),
            ]

            summary = f"Multimodal Rail Combo: Suburban ({orig_sub_stn['raw_name']}) ➔ Transfer at {int_name} ➔ Metro ({dest_metro_stn['raw_name']})"
            results.append(
                RouteOption(
                    route_id=f"r_multi_sm_{uuid.uuid4().hex[:6]}",
                    summary=summary,
                    total_fare=total_fare,
                    total_duration_minutes=total_dur,
                    total_distance_meters=total_dist,
                    transfers_count=2,
                    departure_time=dep_str,
                    arrival_time=arr_str,
                    is_verified=sub_ver and m_ver,
                    provenance="THEME7_MULTIMODAL_SUBURBAN_METRO",
                    fare_status="verified" if (sub_ver and m_ver) else "unavailable",
                    legs=legs,
                )
            )

        return results[:2]
