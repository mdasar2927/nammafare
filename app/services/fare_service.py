from typing import Tuple, Optional

class FareService:
    """Independent fare calculation service adhering to Chennai fare rules."""

    @staticmethod
    def calculate_mtc_bus_fare(
        distance_meters: int,
        bus_type: str = "ordinary",
        gender: str = "other"
    ) -> Tuple[float, str, bool]:
        """
        Calculate MTC bus fare.
        - Women travel free on Ordinary (White-Board) buses (Vidiyal Payana Thittam).
        - Men / Other pay distance-based stage fare table.
        - Express, Deluxe, and AC services are chargeable for all commuters.
        """
        km = distance_meters / 1000.0
        gender_clean = (gender or "other").lower().strip()
        bus_type_clean = (bus_type or "ordinary").lower().strip()

        # Tamil Nadu Vidiyal Payana Thittam
        if gender_clean == "female" and bus_type_clean == "ordinary":
            return (0.0, "Free travel under Vidiyal Payana Thittam (MTC Ordinary Bus)", False)

        if bus_type_clean == "ordinary":
            # Ordinary bus stage fare table
            if km <= 2.0:
                fare = 5.0
            elif km <= 4.0:
                fare = 7.0
            elif km <= 6.0:
                fare = 9.0
            elif km <= 10.0:
                fare = 11.0
            elif km <= 14.0:
                fare = 14.0
            elif km <= 18.0:
                fare = 17.0
            elif km <= 22.0:
                fare = 20.0
            else:
                fare = 23.0
            return (fare, f"MTC Ordinary distance stage fare (₹{int(fare)})", False)

        elif bus_type_clean == "express":
            # Express services
            if km <= 4.0:
                fare = 7.0
            elif km <= 8.0:
                fare = 12.0
            elif km <= 15.0:
                fare = 18.0
            elif km <= 25.0:
                fare = 25.0
            else:
                fare = 30.0
            return (fare, f"MTC Express bus stage fare (₹{int(fare)})", False)

        elif bus_type_clean == "deluxe":
            # Deluxe services
            if km <= 4.0:
                fare = 11.0
            elif km <= 8.0:
                fare = 18.0
            elif km <= 15.0:
                fare = 25.0
            elif km <= 25.0:
                fare = 35.0
            else:
                fare = 42.0
            return (fare, f"MTC Deluxe bus stage fare (₹{int(fare)})", False)

        elif bus_type_clean == "ac":
            # AC Volvo services
            if km <= 5.0:
                fare = 20.0
            elif km <= 10.0:
                fare = 30.0
            elif km <= 20.0:
                fare = 45.0
            else:
                fare = 60.0
            return (fare, f"MTC AC Volvo bus stage fare (₹{int(fare)})", False)

        return (10.0, "MTC standard ticket", False)

    @staticmethod
    def calculate_suburban_fare(
        distance_meters: int,
        is_ac_emu: bool = False
    ) -> Tuple[float, str, bool]:
        """
        Calculate Southern Railway Suburban & MRTS fare based on Theme7 PT Fare Structure.pdf.
        """
        km = distance_meters / 1000.0

        if is_ac_emu:
            if km <= 10.0:
                fare = 35.0
            elif km <= 15.0:
                fare = 40.0
            elif km <= 20.0:
                fare = 60.0
            elif km <= 35.0:
                fare = 85.0
            elif km <= 45.0:
                fare = 90.0
            elif km <= 55.0:
                fare = 100.0
            elif km <= 60.0:
                fare = 105.0
            elif km <= 65.0:
                fare = 115.0
            else:
                fare = 130.0
            return (fare, f"AC EMU local train fare (₹{int(fare)})", False)

        # 2nd Class Ordinary Local Train / MRTS
        if km <= 20.0:
            fare = 5.0
        elif km <= 45.0:
            fare = 10.0
        elif km <= 70.0:
            fare = 15.0
        else:
            fare = 20.0
        return (fare, f"Suburban Railway 2nd Class standard ticket (₹{int(fare)})", False)

    @staticmethod
    def calculate_metro_fare(distance_meters: int) -> Tuple[float, str, bool]:
        """
        Calculate CMRL Chennai Metro fare based on official distance slabs.
        """
        km = distance_meters / 1000.0
        if km <= 2.0:
            fare = 10.0
        elif km <= 5.0:
            fare = 20.0
        elif km <= 12.0:
            fare = 30.0
        elif km <= 21.0:
            fare = 40.0
        else:
            fare = 50.0
        return (fare, f"Chennai Metro (CMRL) standard fare (₹{int(fare)})", False)

    @staticmethod
    def calculate_auto_fare(distance_meters: int) -> Tuple[float, str, bool]:
        """
        Calculate indicative Auto Rickshaw fare.
        Meter rule: ₹25 minimum for first 1.8 km + ₹12/km thereafter.
        Calibrated street baseline applied.
        """
        km = distance_meters / 1000.0
        base_km = 1.8
        base_rate = 25.0
        per_km_rate = 12.0
        if km <= base_km:
            fare = 35.0
        else:
            fare = round(base_rate + (km - base_km) * per_km_rate, 0)
            fare = max(35.0, fare)
        return (fare, "Indicative daytime auto meter estimate (₹25 base + ₹12/km, non-statutory)", True)

    @staticmethod
    def calculate_share_auto_fare(distance_meters: int) -> Tuple[float, str, bool]:
        """
        Calculate indicative Share Auto hop fare along Chennai arterial corridors.
        """
        km = distance_meters / 1000.0
        if km <= 3.0:
            fare = 15.0
        elif km <= 7.0:
            fare = 20.0
        elif km <= 12.0:
            fare = 25.0
        else:
            fare = 30.0
        return (fare, "Indicative Chennai arterial share-auto flat/hop fare", True)

    @staticmethod
    def calculate_taxi_fare(distance_meters: int) -> Tuple[float, str, bool]:
        """
        Calculate indicative Taxi / App-cab daytime fare.
        """
        km = distance_meters / 1000.0
        base_fare = 100.0  # includes first 4 km
        per_km = 18.0
        if km <= 4.0:
            fare = base_fare
        else:
            fare = round(base_fare + (km - 4.0) * per_km, 0)
        return (fare, "Indicative taxi / cab estimate (₹100 base + ₹18/km daytime)", True)

    @staticmethod
    def calculate_walking_fare(distance_meters: int) -> Tuple[float, str, bool]:
        return (0.0, "Walking connection", False)
