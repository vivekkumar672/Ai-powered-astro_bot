# app.py
from datetime import datetime
from Astro_calc import compute_chart, is_manglik

def parse_input_date(date_str):
    # expected format: YYYY-MM-DD HH:MM (24h)
    return datetime.strptime(date_str.strip(), "%Y-%m-%d %H:%M")

def main():
    print("Astro-bot CLI — enter birth details")
    date_input = input("Enter birth date & time (YYYY-MM-DD HH:MM) e.g. 1990-08-15 06:30: ")
    tz_offset = float(input("Timezone offset from UTC in hours (e.g., IST = 5.5): "))
    lat = float(input("Latitude (decimal degrees): "))
    lon = float(input("Longitude (decimal degrees): "))

    birth_dt = parse_input_date(date_input)
    chart = compute_chart(birth_dt, tz_offset, lat, lon)
    manglik_info = is_manglik(chart)

    print("\nComputed Data (always show these):")
    print(f"Ascendant longitude: {chart['ascendant']:.3f}°")
    print("Planet longitudes (deg):")
    for p, lonp in chart["planets"].items():
        print(f"  {p}: {lonp:.3f}°  (house: {chart['planet_houses'][p]})")
    print(f"Moon sign: {chart['moon_sign']['name']} (index {chart['moon_sign']['index']})")
    print(f"Nakshatra: {chart['nakshatra']['name']} (#{chart['nakshatra']['index']})")

    # Natural language loop
    print("\nAsk simple questions. Examples: 'Am I Manglik?', 'What is my Moon sign?', 'exit'")
    while True:
        q = input("\nYour question: ").strip().lower()
        if q in ("exit", "quit"):
            break
        if "manglik" in q:
            if manglik_info["manglik"]:
                reasons = []
                if manglik_info["by_asc"]:
                    reasons.append(f"Mars is in house {manglik_info['house_from_asc']} from Ascendant.")
                if manglik_info["by_moon"]:
                    reasons.append(f"Mars is in house {manglik_info['house_from_moon']} from Moon.")
                print("Answer: YES — Manglik Dosha detected.")
                print("Explanation:", " ".join(reasons))
                print(f"Mars longitude: {manglik_info['mars_longitude']:.3f}°")
            else:
                print("Answer: NO — Manglik Dosha not detected by our rule.")
                print(f"Mars longitude: {manglik_info['mars_longitude']:.3f}°; house from asc: {manglik_info['house_from_asc']}")
            continue
        if "moon sign" in q or "moon" in q:
            ms = chart["moon_sign"]
            print(f"Answer: Moon sign is {ms['name']} (index {ms['index']}). Moon longitude: {ms['longitude']:.3f}°")
            continue
        if "mahadasha" in q or "dasha" in q:
            # placeholder: explain nakshatra and mention TODO
            nak = chart["nakshatra"]
            print("Mahadasha calculation is not implemented in this demo.")
            print(f"However, natal Moon Nakshatra is {nak['name']} (#{nak['index']}).")
            print("TODO: compute Vimshottari dasha timeline from moon nakshatra and birth fraction.")
            continue
        print("Sorry, I only support: Manglik, Moon sign, (Nakshatra shown). Try 'Am I Manglik?' or 'What is my Moon sign?'")

if __name__ == "__main__":
    main()
