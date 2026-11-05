from typing import Tuple

class FareService:
    """
    Independent fare calculation service strictly distinguishing verified official
    statutory tables from derived calculations.
    """

    @staticmethod
    def calculate_mtc_bus_fare(
        distance_meters: int,
        bus_type: str = "ordinary",
        gender: str = "other"
    ) -> Tuple[float, str, bool, str]:
        """
        Calculate MTC bus fare.
        Returns: (fare, fare_note, is_verified, provenance)
        """
        km = distance_meters / 1000.0
        gender_clean = (gender or "other").lower().strip()
        bus_type_clean = (bus_type or "ordinary").lower().strip()

        # 1. Tamil Nadu Government Scheme (Vidiyal Payana Thittam)
        if gender_clean == "female" and bus_type_clean == "ordinary":
            return (
                0.0,
                "Free travel under Vidiyal Payana Thittam (MTC Ordinary White-Board Bus)",
                True,
                "Official Tamil Nadu Government Scheme: Vidiyal Payana Thittam"
            )

        # 2. Statutory MTC Ordinary Stage Fare Table
        if bus_type_clean == "ordinary":
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
            return (
                fare,
                f"MTC Ordinary distance stage fare (₹{int(fare)})",
                True,
                "Official Tamil Nadu Motor Vehicles (MTC) Statutory Stage Fare Table"
            )

        # 3. Statutory Express bus table
        elif bus_type_clean == "express":
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
            return (
                fare,
                f"MTC Express bus stage fare (₹{int(fare)})",
                True,
                "Official MTC Express Service Fare Table"
            )

        # 4. Statutory Deluxe bus table
        elif bus_type_clean == "deluxe":
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
            return (
                fare,
                f"MTC Deluxe bus stage fare (₹{int(fare)})",
                True,
                "Official MTC Deluxe Service Fare Table"
            )

        # 5. Statutory AC Volvo bus table
        elif bus_type_clean == "ac":
            if km <= 5.0:
                fare = 20.0
            elif km <= 10.0:
                fare = 30.0
            elif km <= 20.0:
                fare = 45.0
            else:
                fare = 60.0
            return (
                fare,
                f"MTC AC Volvo bus stage fare (₹{int(fare)})",
                True,
                "Official MTC AC Volvo Service Fare Table"
            )

        return (
            10.0,
            "Standard MTC bus fare",
            False,
            "Derived Stage Fare Estimate"
        )

    @staticmethod
    def calculate_suburban_fare(
        distance_meters: int,
        is_ac_emu: bool = False
    ) -> Tuple[float, str, bool, str]:
        """
        Calculate Southern Railway Suburban fare based on Theme7 PT Fare Structure.pdf.
        Returns: (fare, fare_note, is_verified, provenance)
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
            return (
                fare,
                f"AC EMU local train fare (₹{int(fare)})",
                True,
                "Theme7.Public_Transport.PT_Fare_Structure.pdf (Verified Southern Railway Slabs)"
            )

        # 2nd Class Ordinary Suburban Railway
        if km <= 20.0:
            fare = 5.0
        elif km <= 45.0:
            fare = 10.0
        elif km <= 70.0:
            fare = 15.0
        else:
            fare = 20.0
        return (
            fare,
            f"Suburban Railway 2nd Class ordinary ticket (₹{int(fare)})",
            True,
            "Theme7.Public_Transport.PT_Fare_Structure.pdf (Verified Southern Railway Slabs)"
        )

    @staticmethod
    def calculate_metro_fare(distance_meters: int) -> Tuple[float, str, bool, str]:
        """
        Calculate CMRL Chennai Metro fare based on official distance slabs.
        Returns: (fare, fare_note, is_verified, provenance)
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
        return (
            fare,
            f"Chennai Metro (CMRL) statutory fare (₹{int(fare)})",
            True,
            "Official CMRL Distance Fare Chart (Verified Statutory Table)"
        )

    @staticmethod
    def calculate_walking_fare(distance_meters: int) -> Tuple[float, str, bool, str]:
        return (0.0, "Walking connection", True, "Zero Fare Transfer")
