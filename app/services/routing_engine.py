import uuid
from typing import List, Dict, Any, Optional
from app.models.schemas import (
    SearchRequest,
    SearchResponse,
    RouteOption,
    RouteLeg,
    Coordinates,
)
from app.services.data_loader import TransitDataLoader, haversine_distance_meters
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

        # Direct distance between origin and destination
        direct_dist = haversine_distance_meters(
            origin.lat, origin.lng, destination.lat, destination.lng
        )

        routes: List[RouteOption] = []

        # 1. Direct Walking (if <= 2.5 km and walking allowed)
        if "walking" in allowed_modes and direct_dist <= 2500:
            routes.append(self._create_walking_route(origin, destination, direct_dist, request.departure_time))

        # 2. MTC Bus Ordinary Option (White-Board)
        if "bus" in allowed_modes:
            routes.append(
                self._create_bus_route(
                    origin, destination, direct_dist, gender, bus_type="ordinary", dep_time=request.departure_time
                )
            )

        # 3. MTC Bus Express/Deluxe Option
        if "bus" in allowed_modes and direct_dist >= 4000:
            routes.append(
                self._create_bus_route(
                    origin, destination, direct_dist, gender, bus_type="express", dep_time=request.departure_time
                )
            )

        # 4. Chennai Metro (CMRL) Route
        if "metro" in allowed_modes and direct_dist >= 2000:
            metro_route = self._create_metro_route(origin, destination, direct_dist, request.departure_time)
            if metro_route:
                routes.append(metro_route)

        # 5. Suburban Railway Route
        if "suburban_train" in allowed_modes and direct_dist >= 3000:
            suburban_route = self._create_suburban_route(origin, destination, direct_dist, request.departure_time)
            if suburban_route:
                routes.append(suburban_route)

        # 6. Intermediate Public Transport: Auto Rickshaw
        if "auto" in allowed_modes:
            routes.append(self._create_auto_route(origin, destination, direct_dist, request.departure_time))

        # 7. Intermediate Public Transport: Share Auto
        if "share_auto" in allowed_modes and direct_dist >= 1500:
            routes.append(self._create_share_auto_route(origin, destination, direct_dist, request.departure_time))

        # 8. Taxi / Cab Option
        if "taxi" in allowed_modes and direct_dist >= 2000:
            routes.append(self._create_taxi_route(origin, destination, direct_dist, request.departure_time))

        # Filter out empty or duplicate routes
        routes = [r for r in routes if r and r.legs]

        if not routes:
            # Fallback direct walk / auto
            routes.append(self._create_auto_route(origin, destination, direct_dist, request.departure_time))

        # Mark Cheapest and Fastest
        min_fare = min(r.total_fare for r in routes)
        min_time = min(r.total_duration_minutes for r in routes)

        for r in routes:
            r.is_cheapest = (r.total_fare == min_fare)
            r.is_fastest = (r.total_duration_minutes == min_time)

        # Sort according to user preference
        if sort_by == "fastest":
            routes.sort(key=lambda r: (r.total_duration_minutes, r.total_fare))
        else:  # cheapest
            routes.sort(key=lambda r: (r.total_fare, r.total_duration_minutes))

        dep_str, _ = ETAService.calculate_departure_and_arrival(
            request.departure_time or "", 0
        )

        return SearchResponse(
            search_id=f"search_{uuid.uuid4().hex[:8]}",
            origin=origin.name or "Selected Origin",
            destination=destination.name or "Selected Destination",
            departure_time=dep_str,
            gender=gender,
            routes=routes,
        )

    def _create_walking_route(
        self, origin: Coordinates, destination: Coordinates, dist: int, dep_time: Optional[str]
    ) -> RouteOption:
        dur = ETAService.calculate_duration_minutes(dist, "walking")
        dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", dur)
        fare, note, is_est = FareService.calculate_walking_fare(dist)
        leg = RouteLeg(
            mode="walking",
            from_name=origin.name or "Origin",
            to_name=destination.name or "Destination",
            duration_minutes=dur,
            distance_meters=dist,
            fare=fare,
            fare_note=note,
            is_estimated=is_est,
            polyline=[[origin.lat, origin.lng], [destination.lat, destination.lng]],
        )
        return RouteOption(
            route_id=f"r_walk_{uuid.uuid4().hex[:6]}",
            summary=f"Walk ({dur} mins, ₹0)",
            total_fare=0.0,
            total_duration_minutes=dur,
            total_distance_meters=dist,
            transfers_count=0,
            departure_time=dep_str,
            arrival_time=arr_str,
            legs=[leg],
        )

    def _create_bus_route(
        self,
        origin: Coordinates,
        destination: Coordinates,
        direct_dist: int,
        gender: str,
        bus_type: str = "ordinary",
        dep_time: Optional[str] = None,
    ) -> RouteOption:
        # Find closest bus stops from Theme7 data
        first_walk_dist = min(500, int(direct_dist * 0.08))
        last_walk_dist = min(400, int(direct_dist * 0.07))
        bus_dist = max(500, direct_dist - first_walk_dist - last_walk_dist)

        origin_nearest = self.loader.find_nearest_place(origin.lat, origin.lng, mode_filter="bus")
        dest_nearest = self.loader.find_nearest_place(destination.lat, destination.lng, mode_filter="bus")

        origin_stop_name = origin_nearest[0]["name"] if origin_nearest else f"Near {origin.name or 'Origin'} Stop"
        dest_stop_name = dest_nearest[0]["name"] if dest_nearest else f"Near {destination.name or 'Destination'} Stop"

        # Determine prominent MTC route number from dataset or canonical
        route_no = "18A" if bus_type == "ordinary" else "21G"
        if direct_dist > 15000:
            route_no = "570" if bus_type == "ordinary" else "102"

        fare, fare_note, is_est = FareService.calculate_mtc_bus_fare(
            bus_dist, bus_type=bus_type, gender=gender
        )

        walk1_dur = ETAService.calculate_duration_minutes(first_walk_dist, "walking")
        bus_dur = ETAService.calculate_duration_minutes(bus_dist, "bus") + ETAService.TRANSFER_BUFFER_MINUTES["bus"]
        walk2_dur = ETAService.calculate_duration_minutes(last_walk_dist, "walking")
        total_dur = walk1_dur + bus_dur + walk2_dur
        total_dist = first_walk_dist + bus_dist + last_walk_dist

        dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", total_dur)

        type_title = "Ordinary (White-Board)" if bus_type == "ordinary" else "Express"
        legs = [
            RouteLeg(
                mode="walking",
                from_name=origin.name or "Origin",
                to_name=origin_stop_name,
                duration_minutes=walk1_dur,
                distance_meters=first_walk_dist,
                fare=0.0,
                polyline=[[origin.lat, origin.lng], [origin.lat + 0.002, origin.lng + 0.002]],
            ),
            RouteLeg(
                mode="bus",
                route_number=route_no,
                bus_type=bus_type,
                from_name=origin_stop_name,
                to_name=dest_stop_name,
                duration_minutes=bus_dur,
                distance_meters=bus_dist,
                fare=fare,
                fare_note=fare_note,
                is_estimated=is_est,
                polyline=[[origin.lat + 0.002, origin.lng + 0.002], [destination.lat - 0.002, destination.lng - 0.002]],
            ),
            RouteLeg(
                mode="walking",
                from_name=dest_stop_name,
                to_name=destination.name or "Destination",
                duration_minutes=walk2_dur,
                distance_meters=last_walk_dist,
                fare=0.0,
                polyline=[[destination.lat - 0.002, destination.lng - 0.002], [destination.lat, destination.lng]],
            ),
        ]

        summary = f"MTC Bus {route_no} ({type_title})"
        return RouteOption(
            route_id=f"r_bus_{bus_type}_{uuid.uuid4().hex[:6]}",
            summary=summary,
            total_fare=fare,
            total_duration_minutes=total_dur,
            total_distance_meters=total_dist,
            transfers_count=1,
            departure_time=dep_str,
            arrival_time=arr_str,
            legs=legs,
        )

    def _create_metro_route(
        self,
        origin: Coordinates,
        destination: Coordinates,
        direct_dist: int,
        dep_time: Optional[str] = None,
    ) -> Optional[RouteOption]:
        # Nearest Metro stations
        origin_stn = self.loader.find_nearest_place(origin.lat, origin.lng, mode_filter="metro")
        dest_stn = self.loader.find_nearest_place(destination.lat, destination.lng, mode_filter="metro")

        stn1_name = origin_stn[0]["name"] if origin_stn else "Chennai Central Metro"
        stn2_name = dest_stn[0]["name"] if dest_stn else "Guindy Metro"

        walk1_dist = min(700, int(direct_dist * 0.1))
        walk2_dist = min(600, int(direct_dist * 0.1))
        metro_dist = max(1000, direct_dist - walk1_dist - walk2_dist)

        fare, fare_note, is_est = FareService.calculate_metro_fare(metro_dist)

        walk1_dur = ETAService.calculate_duration_minutes(walk1_dist, "walking")
        metro_dur = ETAService.calculate_duration_minutes(metro_dist, "metro") + ETAService.TRANSFER_BUFFER_MINUTES["metro"]
        walk2_dur = ETAService.calculate_duration_minutes(walk2_dist, "walking")
        total_dur = walk1_dur + metro_dur + walk2_dur
        total_dist = walk1_dist + metro_dist + walk2_dist

        dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", total_dur)

        legs = [
            RouteLeg(
                mode="walking",
                from_name=origin.name or "Origin",
                to_name=stn1_name,
                duration_minutes=walk1_dur,
                distance_meters=walk1_dist,
                fare=0.0,
                polyline=[[origin.lat, origin.lng], [origin_stn[0]["lat"] if origin_stn else origin.lat, origin_stn[0]["lng"] if origin_stn else origin.lng]],
            ),
            RouteLeg(
                mode="metro",
                route_number="Blue / Green Line",
                from_name=stn1_name,
                to_name=stn2_name,
                duration_minutes=metro_dur,
                distance_meters=metro_dist,
                fare=fare,
                fare_note=fare_note,
                is_estimated=is_est,
                polyline=[
                    [origin_stn[0]["lat"] if origin_stn else origin.lat, origin_stn[0]["lng"] if origin_stn else origin.lng],
                    [dest_stn[0]["lat"] if dest_stn else destination.lat, dest_stn[0]["lng"] if dest_stn else destination.lng]
                ],
            ),
            RouteLeg(
                mode="walking",
                from_name=stn2_name,
                to_name=destination.name or "Destination",
                duration_minutes=walk2_dur,
                distance_meters=walk2_dist,
                fare=0.0,
                polyline=[[dest_stn[0]["lat"] if dest_stn else destination.lat, dest_stn[0]["lng"] if dest_stn else destination.lng], [destination.lat, destination.lng]],
            ),
        ]

        return RouteOption(
            route_id=f"r_metro_{uuid.uuid4().hex[:6]}",
            summary=f"Chennai Metro (Walk ➔ {stn1_name} ➔ {stn2_name})",
            total_fare=fare,
            total_duration_minutes=total_dur,
            total_distance_meters=total_dist,
            transfers_count=1,
            departure_time=dep_str,
            arrival_time=arr_str,
            legs=legs,
        )

    def _create_suburban_route(
        self,
        origin: Coordinates,
        destination: Coordinates,
        direct_dist: int,
        dep_time: Optional[str] = None,
    ) -> Optional[RouteOption]:
        # Nearest Suburban railway stations
        origin_stn = self.loader.find_nearest_place(origin.lat, origin.lng, mode_filter="suburban_train")
        dest_stn = self.loader.find_nearest_place(destination.lat, destination.lng, mode_filter="suburban_train")

        stn1_name = origin_stn[0]["name"] if origin_stn else "Chennai Beach / Fort"
        stn2_name = dest_stn[0]["name"] if dest_stn else "Tambaram / Guindy"

        walk1_dist = min(800, int(direct_dist * 0.12))
        walk2_dist = min(700, int(direct_dist * 0.1))
        train_dist = max(1500, direct_dist - walk1_dist - walk2_dist)

        fare, fare_note, is_est = FareService.calculate_suburban_fare(train_dist, is_ac_emu=False)

        walk1_dur = ETAService.calculate_duration_minutes(walk1_dist, "walking")
        train_dur = ETAService.calculate_duration_minutes(train_dist, "suburban_train") + ETAService.TRANSFER_BUFFER_MINUTES["suburban_train"]
        walk2_dur = ETAService.calculate_duration_minutes(walk2_dist, "walking")
        total_dur = walk1_dur + train_dur + walk2_dur
        total_dist = walk1_dist + train_dist + walk2_dist

        dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", total_dur)

        legs = [
            RouteLeg(
                mode="walking",
                from_name=origin.name or "Origin",
                to_name=stn1_name,
                duration_minutes=walk1_dur,
                distance_meters=walk1_dist,
                fare=0.0,
                polyline=[[origin.lat, origin.lng], [origin_stn[0]["lat"] if origin_stn else origin.lat, origin_stn[0]["lng"] if origin_stn else origin.lng]],
            ),
            RouteLeg(
                mode="suburban_train",
                route_number="Southern Railway Suburban EMU",
                from_name=stn1_name,
                to_name=stn2_name,
                duration_minutes=train_dur,
                distance_meters=train_dist,
                fare=fare,
                fare_note=fare_note,
                is_estimated=is_est,
                polyline=[
                    [origin_stn[0]["lat"] if origin_stn else origin.lat, origin_stn[0]["lng"] if origin_stn else origin.lng],
                    [dest_stn[0]["lat"] if dest_stn else destination.lat, dest_stn[0]["lng"] if dest_stn else destination.lng]
                ],
            ),
            RouteLeg(
                mode="walking",
                from_name=stn2_name,
                to_name=destination.name or "Destination",
                duration_minutes=walk2_dur,
                distance_meters=walk2_dist,
                fare=0.0,
                polyline=[[dest_stn[0]["lat"] if dest_stn else destination.lat, dest_stn[0]["lng"] if dest_stn else destination.lng], [destination.lat, destination.lng]],
            ),
        ]

        return RouteOption(
            route_id=f"r_sub_{uuid.uuid4().hex[:6]}",
            summary=f"Suburban EMU (Walk ➔ {stn1_name} ➔ {stn2_name})",
            total_fare=fare,
            total_duration_minutes=total_dur,
            total_distance_meters=total_dist,
            transfers_count=1,
            departure_time=dep_str,
            arrival_time=arr_str,
            legs=legs,
        )

    def _create_auto_route(
        self, origin: Coordinates, destination: Coordinates, dist: int, dep_time: Optional[str]
    ) -> RouteOption:
        dur = ETAService.calculate_duration_minutes(dist, "auto") + ETAService.TRANSFER_BUFFER_MINUTES["auto"]
        dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", dur)
        fare, note, is_est = FareService.calculate_auto_fare(dist)
        leg = RouteLeg(
            mode="auto",
            from_name=origin.name or "Origin",
            to_name=destination.name or "Destination",
            duration_minutes=dur,
            distance_meters=dist,
            fare=fare,
            fare_note=note,
            is_estimated=is_est,
            polyline=[[origin.lat, origin.lng], [destination.lat, destination.lng]],
        )
        return RouteOption(
            route_id=f"r_auto_{uuid.uuid4().hex[:6]}",
            summary=f"Auto Rickshaw (Direct ₹{int(fare)})",
            total_fare=fare,
            total_duration_minutes=dur,
            total_distance_meters=dist,
            transfers_count=0,
            departure_time=dep_str,
            arrival_time=arr_str,
            legs=[leg],
        )

    def _create_share_auto_route(
        self, origin: Coordinates, destination: Coordinates, dist: int, dep_time: Optional[str]
    ) -> RouteOption:
        walk1_dist = min(350, int(dist * 0.08))
        walk2_dist = min(300, int(dist * 0.08))
        auto_dist = max(500, dist - walk1_dist - walk2_dist)

        walk1_dur = ETAService.calculate_duration_minutes(walk1_dist, "walking")
        auto_dur = ETAService.calculate_duration_minutes(auto_dist, "share_auto") + ETAService.TRANSFER_BUFFER_MINUTES["share_auto"]
        walk2_dur = ETAService.calculate_duration_minutes(walk2_dist, "walking")
        total_dur = walk1_dur + auto_dur + walk2_dur
        total_dist = walk1_dist + auto_dist + walk2_dist

        fare, note, is_est = FareService.calculate_share_auto_fare(auto_dist)
        dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", total_dur)

        legs = [
            RouteLeg(
                mode="walking",
                from_name=origin.name or "Origin",
                to_name="Arterial Share-Auto Stand",
                duration_minutes=walk1_dur,
                distance_meters=walk1_dist,
                fare=0.0,
                polyline=[[origin.lat, origin.lng], [origin.lat + 0.001, origin.lng + 0.001]],
            ),
            RouteLeg(
                mode="share_auto",
                route_number="Feeder / Arterial",
                from_name="Arterial Share-Auto Stand",
                to_name="Destination Junction",
                duration_minutes=auto_dur,
                distance_meters=auto_dist,
                fare=fare,
                fare_note=note,
                is_estimated=is_est,
                polyline=[[origin.lat + 0.001, origin.lng + 0.001], [destination.lat - 0.001, destination.lng - 0.001]],
            ),
            RouteLeg(
                mode="walking",
                from_name="Destination Junction",
                to_name=destination.name or "Destination",
                duration_minutes=walk2_dur,
                distance_meters=walk2_dist,
                fare=0.0,
                polyline=[[destination.lat - 0.001, destination.lng - 0.001], [destination.lat, destination.lng]],
            ),
        ]
        return RouteOption(
            route_id=f"r_share_{uuid.uuid4().hex[:6]}",
            summary=f"Share Auto (Hop ₹{int(fare)})",
            total_fare=fare,
            total_duration_minutes=total_dur,
            total_distance_meters=total_dist,
            transfers_count=1,
            departure_time=dep_str,
            arrival_time=arr_str,
            legs=legs,
        )

    def _create_taxi_route(
        self, origin: Coordinates, destination: Coordinates, dist: int, dep_time: Optional[str]
    ) -> RouteOption:
        dur = ETAService.calculate_duration_minutes(dist, "taxi") + ETAService.TRANSFER_BUFFER_MINUTES["taxi"]
        dep_str, arr_str = ETAService.calculate_departure_and_arrival(dep_time or "", dur)
        fare, note, is_est = FareService.calculate_taxi_fare(dist)
        leg = RouteLeg(
            mode="taxi",
            from_name=origin.name or "Origin",
            to_name=destination.name or "Destination",
            duration_minutes=dur,
            distance_meters=dist,
            fare=fare,
            fare_note=note,
            is_estimated=is_est,
            polyline=[[origin.lat, origin.lng], [destination.lat, destination.lng]],
        )
        return RouteOption(
            route_id=f"r_taxi_{uuid.uuid4().hex[:6]}",
            summary=f"Taxi / Cab (Door-to-Door ₹{int(fare)})",
            total_fare=fare,
            total_duration_minutes=dur,
            total_distance_meters=dist,
            transfers_count=0,
            departure_time=dep_str,
            arrival_time=arr_str,
            legs=[leg],
        )
