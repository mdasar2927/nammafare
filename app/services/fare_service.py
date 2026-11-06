import json
import os
from typing import Any, Dict, List, Optional, Tuple

# Path to verified MTC fares JSON
_FARES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "mtc_fares.json"
)

# Load MTC fare data from JSON on module import
_MTC_DATA: Dict[str, Any] = {}
if os.path.exists(_FARES_FILE):
    try:
        with open(_FARES_FILE, "r", encoding="utf-8") as f:
            _MTC_DATA = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load MTC fare data from {_FARES_FILE}: {e}")

_MTC_METADATA = _MTC_DATA.get("metadata", {})
_MTC_SERVICE_TYPES = _MTC_DATA.get("service_types", [])
_MTC_FARES_BY_STAGE = _MTC_DATA.get("fares_by_stage", {})

# Official metadata strings for provenance
MTC_SOURCE_URL = _MTC_METADATA.get(
    "source_url", "https://mtcbus.tn.gov.in/Home/fares"
)
MTC_EFFECTIVE_DATE = _MTC_METADATA.get("published_effective_date", "2018-01-29")
MTC_LIMITATION_NOTE = _MTC_METADATA.get(
    "important_limitation",
    "Verify all fares against current MTC rules before production use.",
)

# Path to verified Chennai Metro (CMRL) fares JSON
_METRO_FARES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "metro_fares.json"
)
_METRO_DATA: Dict[str, Any] = {}
if os.path.exists(_METRO_FARES_FILE):
    try:
        with open(_METRO_FARES_FILE, "r", encoding="utf-8") as f:
            _METRO_DATA = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load CMRL metro fare data from {_METRO_FARES_FILE}: {e}")

CMRL_SOURCE = _METRO_DATA.get(
    "source", "Chennai Metro Rail Limited (CMRL) Official Fare Table"
)
CMRL_SOURCE_URL = _METRO_DATA.get(
    "source_url", "https://chennaimetrorail.org/wp-content/uploads/2026/10/Fare-Table.pdf"
)
CMRL_EFFECTIVE_DATE = _METRO_DATA.get("effective_date", "2026-10")
_METRO_STATIONS: List[str] = _METRO_DATA.get("stations", [])
_METRO_MATRIX: List[List[int]] = _METRO_DATA.get("matrix", [])
_METRO_STATION_INDEX: Dict[str, int] = {
    s.upper().strip(): idx for idx, s in enumerate(_METRO_STATIONS)
}

# Normalization mapping for canonical service types
_SERVICE_TYPE_ALIASES = {
    "ordinary": "Ordinary Services",
    "ordinary services": "Ordinary Services",
    "white_board": "Ordinary Services",
    "white board": "Ordinary Services",
    "express": "Express Services",
    "express services": "Express Services",
    "deluxe": "Deluxe Services",
    "deluxe services": "Deluxe Services",
    "small": "Small",
    "small bus": "Small",
    "night": "Night services",
    "night services": "Night services",
    "night service": "Night services",
    "ev_deluxe": "E/V Deluxe Service",
    "e/v deluxe service": "E/V Deluxe Service",
    "ev deluxe service": "E/V Deluxe Service",
    "ev_ac": "E/V A/C Service",
    "e/v a/c service": "E/V A/C Service",
    "ev a/c service": "E/V A/C Service",
    "ac": "E/V A/C Service",
    "ac_volvo": "E/V A/C Service",
    "vintage": "Chennai Ula Vintage Services",
    "chennai ula vintage services": "Chennai Ula Vintage Services",
    "pink": "Pink Services",
    "pink services": "Pink Services",
    "chennai_ula_ac": "Chennai Ula A/C Services",
    "chennai ula a/c services": "Chennai Ula A/C Services",
    "premium": "Premium Services",
    "premium services": "Premium Services",
}


class FareService:
    """
    Independent fare calculation service strictly distinguishing verified official
    statutory tables from derived calculations.
    """

    @classmethod
    def get_supported_service_types(cls) -> list[str]:
        """Return the official list of 11 MTC service types from mtc_fares.json."""
        return list(_MTC_SERVICE_TYPES)

    @classmethod
    def normalize_service_type(cls, service_type: str) -> Optional[str]:
        """Resolve any alias or case-insensitive string to canonical MTC service type."""
        clean = (service_type or "").lower().strip()
        return _SERVICE_TYPE_ALIASES.get(clean)

    @classmethod
    def calculate_mtc_bus_fare_by_stage(
        cls,
        stage: Optional[int],
        service_type: str = "Ordinary Services",
        gender: str = "other",
    ) -> Tuple[float, str, bool, str]:
        """
        Exact stage-wise fare lookup from the official MTC Fares_By_Stage table.

        Parameters:
            stage: Tariff stage number (1 to 30; 1 to 5 for Premium Services).
            service_type: One of the 11 MTC service types (or supported aliases).
            gender: 'female', 'male', or 'other'.

        Returns:
            Tuple of (fare: float, fare_note: str, is_verified: bool, provenance: str)
        """
        gender_clean = (gender or "other").lower().strip()

        # 1. Validate stage parameter
        if stage is None or not isinstance(stage, int) or stage <= 0:
            return (
                0.0,
                "Fare unavailable: missing or invalid stage number (stage must be >= 1)",
                False,
                f"MTC Official Stage Fare Table (Effective {MTC_EFFECTIVE_DATE}, {MTC_SOURCE_URL}); stage not provided or invalid",
            )

        # 2. Resolve canonical service type
        canonical = cls.normalize_service_type(service_type)
        if not canonical or canonical not in _MTC_SERVICE_TYPES:
            return (
                0.0,
                f"Fare unavailable: unknown MTC service type '{service_type}'",
                False,
                f"MTC Official Stage Fare Table (Effective {MTC_EFFECTIVE_DATE}, {MTC_SOURCE_URL}); unrecognized service type",
            )

        # 3. Women's free travel rule (Vidiyal Payana Thittam)
        # Apply strictly to Ordinary Services as officially verified.
        # Do NOT apply to Pink Services until eligibility is independently confirmed.
        if gender_clean == "female" and canonical == "Ordinary Services":
            return (
                0.0,
                "Free travel under Vidiyal Payana Thittam (MTC Ordinary Service)",
                True,
                "Official Tamil Nadu Government Scheme: Vidiyal Payana Thittam (MTC Ordinary Services)",
            )

        # 4. Check stage boundaries
        if canonical == "Premium Services" and stage > 5:
            return (
                0.0,
                f"Fare unavailable: Premium Services operates only for stages 1 to 5 (requested stage {stage})",
                False,
                f"Official MTC Stage Fare Table (Effective {MTC_EFFECTIVE_DATE}, {MTC_SOURCE_URL}); Premium Services stage out of range",
            )

        if stage > 30:
            return (
                0.0,
                f"Fare unavailable: stage {stage} exceeds maximum defined MTC stage table limit (stage 30)",
                False,
                f"Official MTC Stage Fare Table (Effective {MTC_EFFECTIVE_DATE}, {MTC_SOURCE_URL}); stage exceeds defined range 1-30",
            )

        # 5. Lookup fare from Fares_By_Stage table
        stage_str = str(stage)
        stage_row = _MTC_FARES_BY_STAGE.get(stage_str, {})
        fare_val = stage_row.get(canonical)

        if fare_val is None:
            return (
                0.0,
                f"Fare unavailable for {canonical} at stage {stage}",
                False,
                f"Official MTC Stage Fare Table (Effective {MTC_EFFECTIVE_DATE}, {MTC_SOURCE_URL}); unlisted stage",
            )

        fare = float(fare_val)
        provenance = (
            f"Official MTC Bus Fares Table (Effective {MTC_EFFECTIVE_DATE}, {MTC_SOURCE_URL}) "
            f"[{MTC_LIMITATION_NOTE}]"
        )
        return (
            fare,
            f"MTC {canonical} stage {stage} statutory fare (₹{int(fare)})",
            True,
            provenance,
        )

    @staticmethod
    def calculate_mtc_bus_fare(
        distance_meters: int,
        bus_type: str = "ordinary",
        gender: str = "other",
    ) -> Tuple[float, str, bool, str]:
        """
        Calculate MTC bus fare based on distance (backward compatibility for existing callers).
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
                "Official Tamil Nadu Government Scheme: Vidiyal Payana Thittam",
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
                "Official Tamil Nadu Motor Vehicles (MTC) Statutory Stage Fare Table",
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
                "Official MTC Express Service Fare Table",
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
                "Official MTC Deluxe Service Fare Table",
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
                "Official MTC AC Volvo Service Fare Table",
            )

        return (
            10.0,
            "Standard MTC bus fare",
            False,
            "Derived Stage Fare Estimate",
        )

    @staticmethod
    def calculate_suburban_fare(
        distance_meters: int, is_ac_emu: bool = False
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
                "Theme7.Public_Transport.PT_Fare_Structure.pdf (Verified Southern Railway Slabs)",
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
            "Theme7.Public_Transport.PT_Fare_Structure.pdf (Verified Southern Railway Slabs)",
        )

    @staticmethod
    def normalize_metro_station(station_name: Optional[str]) -> Optional[str]:
        """Normalize station name to official CMRL station name."""
        if not station_name:
            return None
        cleaned = station_name.upper().strip()
        # Direct lookup
        if cleaned in _METRO_STATION_INDEX:
            return cleaned
        # Strip common prefixes / suffixes
        prefixes_to_strip = ["THEME7 METRO STATION: ", "CHENNAI METRO: ", "METRO: ", "STATION: "]
        for p in prefixes_to_strip:
            if cleaned.startswith(p):
                cleaned = cleaned[len(p):].strip()
        suffixes_to_strip = [" METRO STATION", " METRO", " STATION"]
        for s in suffixes_to_strip:
            if cleaned.endswith(s):
                cleaned = cleaned[:-len(s)].strip()

        if cleaned in _METRO_STATION_INDEX:
            return cleaned

        # Known common aliases
        aliases = {
            "MANNADY": "MANNADI",
            "CENTRAL": "PURATCHI THALAIVAR DR.M.G.RAMACHANDRAN CENTRAL METRO",
            "MGR CENTRAL": "PURATCHI THALAIVAR DR.M.G.RAMACHANDRAN CENTRAL METRO",
            "CHENNAI CENTRAL": "PURATCHI THALAIVAR DR.M.G.RAMACHANDRAN CENTRAL METRO",
            "CENTRAL METRO": "PURATCHI THALAIVAR DR.M.G.RAMACHANDRAN CENTRAL METRO",
            "DR. MGR CENTRAL": "PURATCHI THALAIVAR DR.M.G.RAMACHANDRAN CENTRAL METRO",
            "PURATCHI THALAIVAR DR. M.G. RAMACHANDRAN CENTRAL": "PURATCHI THALAIVAR DR.M.G.RAMACHANDRAN CENTRAL METRO",
            "PURATCHI THALAIVAR DR. M.G. RAMACHANDRAN CENTRAL METRO": "PURATCHI THALAIVAR DR.M.G.RAMACHANDRAN CENTRAL METRO",
            "EGMORE": "EGMORE",
            "CHENNAI EGMORE": "EGMORE",
            "AIRPORT": "AIRPORT",
            "CHENNAI AIRPORT": "AIRPORT",
            "ALANDUR": "ARIGNAR ANNA ALANDUR METRO",
            "ARIGNAR ANNA ALANDUR": "ARIGNAR ANNA ALANDUR METRO",
            "CMBT": "PURATCHI THALAIVI DR.J.JAYALALITHA CMBT METRO",
            "PURATCHI THALAIVI DR.J.JAYALALITHA CMBT": "PURATCHI THALAIVI DR.J.JAYALALITHA CMBT METRO",
            "ST. THOMAS MOUNT": "ST. THOMAS MOUNT",
            "ST THOMAS MOUNT": "ST. THOMAS MOUNT",
            "NANGANALLUR ROAD": "OTA - NANGANALLUR ROAD",
            "OTA": "OTA - NANGANALLUR ROAD",
            "WIMCO NAGAR": "WIMCONAGAR",
            "WIMCONAGAR DEPOT": "WIMCO NAGAR DEPOT",
            "THIRUVOTRIYUR THERADI": "THIRUVOTRIYUR THERADI METRO",
            "PACHAIYAPPAS COLLEGE": "PACHIAPPAS COLLEGE",
            "PACHAIYAPPA'S COLLEGE": "PACHIAPPAS COLLEGE",
        }
        if cleaned in aliases:
            return aliases[cleaned]

        # Fuzzy substring match against matrix station names
        for stn in _METRO_STATIONS:
            if cleaned == stn or cleaned in stn:
                return stn

        return None

    @classmethod
    def calculate_metro_fare_by_station(
        cls, boarding_station: Optional[str], alighting_station: Optional[str]
    ) -> Tuple[float, str, bool, str, str]:
        """
        Calculate exact single-journey Metro fare between two stations using the CMRL Fare Matrix.
        Returns:
            Tuple of (fare: float, fare_note: str, is_verified: bool, provenance: str, fare_status: str)
        """
        norm_b = cls.normalize_metro_station(boarding_station)
        norm_a = cls.normalize_metro_station(alighting_station)

        if not norm_b or not norm_a:
            missing = []
            if not norm_b:
                missing.append(f"boarding='{boarding_station}'")
            if not norm_a:
                missing.append(f"alighting='{alighting_station}'")
            return (
                0.0,
                f"Metro fare unavailable: unmapped station ({', '.join(missing)})",
                False,
                f"{CMRL_SOURCE} ({CMRL_SOURCE_URL}); station mapping not established",
                "unavailable",
            )

        idx_b = _METRO_STATION_INDEX.get(norm_b)
        idx_a = _METRO_STATION_INDEX.get(norm_a)

        if idx_b is None or idx_a is None or idx_b >= len(_METRO_MATRIX) or idx_a >= len(_METRO_MATRIX[0]):
            return (
                0.0,
                "Metro fare unavailable: station index out of matrix bounds",
                False,
                f"{CMRL_SOURCE} ({CMRL_SOURCE_URL}); matrix lookup failed",
                "unavailable",
            )

        fare = float(_METRO_MATRIX[idx_b][idx_a])
        fare_note = f"CMRL Single Journey statutory fare: {norm_b} ➔ {norm_a} (₹{int(fare)})"
        provenance = (
            f"Official CMRL Station-to-Station Single Journey Fare Matrix "
            f"(Effective {CMRL_EFFECTIVE_DATE}, {CMRL_SOURCE_URL})"
        )
        return (fare, fare_note, True, provenance, "verified")

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
            "Official CMRL Distance Fare Chart (Verified Statutory Table)",
        )

    @staticmethod
    def calculate_walking_fare(distance_meters: int) -> Tuple[float, str, bool, str]:
        return (0.0, "Walking connection", True, "Zero Fare Transfer")
