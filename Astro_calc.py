# astro_calc.py
# Core calculator using pyswisseph (swisseph python binding).
# - computes planetary longitudes (Sun..Saturn)
# - computes Ascendant (Lagna) and house placements
# - determines Moon sign and Nakshatra
# - implements Manglik check (Mars in 1,2,4,7,8,12 from Asc or Moon)

import swisseph as swe
from datetime import datetime, timezone, timedelta

# configure ephemeris path if you keep swiss eph data locally
# swe.set_ephe_path('/path/to/ephemeris')  # optional

PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
}

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra",
    "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
    "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta",
    "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]
# Note: there are 27 nakshatras. We'll use 360/27 = 13.333... deg each.

def datetime_to_jd_ut(dt: datetime, tz_offset_hours: float):
    """
    Convert a timezone-aware or naive datetime (assumed local) + tz offset (hours)
    to Julian day (UT) required by Swiss Ephemeris.
    tz_offset_hours: hours to subtract from local to get UTC (e.g., IST +5.5 -> 5.5)
    """
    # Convert dt to UTC by subtracting tz offset
    utc_dt = dt - timedelta(hours=tz_offset_hours)
    year, month, day = utc_dt.year, utc_dt.month, utc_dt.day
    hour = utc_dt.hour + utc_dt.minute / 60 + utc_dt.second / 3600
    jd = swe.julday(year, month, day, hour)
    return jd

def get_planet_longitudes(jd_ut):
    """
    Returns dict {planet_name: longitude_in_degrees}
    longitudes in tropical zodiac (0..360)
    """
    longs = {}
    for name, code in PLANETS.items():
        lon, lat, dist = swe.calc_ut(jd_ut, code)[0:3]  # returns (longitude, latitude, distance, ..)
        # ensure lon in 0..360
        lon = lon % 360.0
        longs[name] = lon
    return longs

def get_ascendant(jd_ut, lat, lon):
    """
    Returns ascendant longitude (degrees) and house cusps using Swiss Ephemeris houses()
    lat, lon in decimal degrees (lon: positive east)
    """
    # Swiss ephem expects geocentric: use flag 'P' (placidus) by default; many options exist
    cusps, ascmc = swe.houses(jd_ut, lat, lon)
    asc = ascmc[0] % 360.0  # ascendant longitude
    return asc, cusps  # cusps is 1..12 cusp longitudes (cusps[1] is 1st cusp)

def longitude_to_sign(lon):
    """Return sign index (1..12) and sign name from longitude in degrees."""
    sign_index = int(lon // 30) + 1
    sign_name = ZODIAC_SIGNS[sign_index - 1]
    return sign_index, sign_name

def longitude_to_house_from_asc(lon_planet, asc_lon):
    """
    Calculate house number (1..12) for a planet given Ascendant longitude.
    House 1 spans asc .. asc+30, house 2 asc+30 .. asc+60 etc.
    """
    relative = (lon_planet - asc_lon) % 360.0
    house = int(relative // 30) + 1
    return house

def longitude_to_house_from_ref(lon_planet, ref_lon):
    """Generic: house number from any reference point (asc or moon)."""
    relative = (lon_planet - ref_lon) % 360.0
    return int(relative // 30) + 1

def moon_nakshatra(moon_lon):
    """
    Returns nakshatra index (1..27) and name and intra-nakshatra degrees.
    Each nakshatra = 13°20' = 13.333333... degrees.
    """
    span = 360.0 / 27.0  # = 13.333333...
    idx = int(moon_lon // span)  # 0..26
    name = NAKSHATRAS[idx]
    intra_deg = moon_lon - (idx * span)
    return idx + 1, name, intra_deg

def compute_chart(birth_dt: datetime, tz_offset_hours: float, lat: float, lon: float):
    """
    Main routine:
    - birth_dt: naive datetime representing local birth time
    - tz_offset_hours: hours offset from UTC (e.g., IST = +5.5)
    - lat, lon: location coordinates (deg)
    Returns a dictionary with computed values.
    """
    jd_ut = datetime_to_jd_ut(birth_dt, tz_offset_hours)
    planets = get_planet_longitudes(jd_ut)
    asc, cusps = get_ascendant(jd_ut, lat, lon)

    moon_lon = planets["Moon"]
    moon_sign_idx, moon_sign_name = longitude_to_sign(moon_lon)
    nak_idx, nak_name, nak_intra = moon_nakshatra(moon_lon)

    # Houses: determine house numbers for planets from Ascendant
    planet_houses = {}
    for p, lon_p in planets.items():
        planet_houses[p] = longitude_to_house_from_asc(lon_p, asc)

    result = {
        "jd_ut": jd_ut,
        "planets": planets,
        "ascendant": asc,
        "cusps": cusps,
        "planet_houses": planet_houses,
        "moon_sign": {"index": moon_sign_idx, "name": moon_sign_name, "longitude": moon_lon},
        "nakshatra": {"index": nak_idx, "name": nak_name, "intra_deg": nak_intra},
    }
    return result

# ----- RULES -----

MANGLIK_HOUSES = {1, 2, 4, 7, 8, 12}

def is_manglik(chart):
    """
    Manglik Dosha detection (two variants):
    - Mars in 1,2,4,7,8,12 from Ascendant
    - OR Mars in 1,2,4,7,8,12 from Moon
    Returns dict with which rule triggered and supporting values.
    """
    mars_lon = chart["planets"]["Mars"]
    asc = chart["ascendant"]
    moon_lon = chart["planets"]["Moon"]

    house_from_asc = longitude_to_house_from_ref(mars_lon, asc)
    house_from_moon = longitude_to_house_from_ref(mars_lon, moon_lon)

    triggered_by_asc = house_from_asc in MANGLIK_HOUSES
    triggered_by_moon = house_from_moon in MANGLIK_HOUSES

    return {
        "manglik": (triggered_by_asc or triggered_by_moon),
        "by_asc": triggered_by_asc,
        "house_from_asc": house_from_asc,
        "by_moon": triggered_by_moon,
        "house_from_moon": house_from_moon,
        "mars_longitude": mars_lon
    }

# Note: Full Vimshottari Mahadasha implementation is non-trivial and not included here.
# We provide Nakshatra (birth star) which is the standard starting point for dasha calculations.
# TODO: implement full Vimshottari dasha timeline and current maha/sub-dasha.

if __name__ == "__main__":
    # quick debug example (Kolkata example in README)
    dt = datetime(1990, 8, 15, 6, 30)   # local time
    chart = compute_chart(dt, tz_offset_hours=5.5, lat=22.5726, lon=88.3639)
    print("Planets:", chart["planets"])
    print("Ascendant:", chart["ascendant"])
    print("Moon sign:", chart["moon_sign"])
    print("Nakshatra:", chart["nakshatra"])
    print("Manglik:", is_manglik(chart))
