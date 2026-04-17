import gpxpy
from datetime import datetime

def gpx_to_time_log(gpx_path, output_txt="gps_time_log.txt"):
    # --- Read GPX file ---
    with open(gpx_path, 'r') as f:
        gpx = gpxpy.parse(f)

    time_dict = {}  # { second_timestamp: (lat, lon) }

    # --- Extract points ---
    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                if p.time:
                    # Round timestamp to nearest second
                    t = p.time.replace(microsecond=0)

                    # Only keep first point for each second
                    if t not in time_dict:
                        time_dict[t] = (p.latitude, p.longitude)

    # --- Sort by time ---
    sorted_items = sorted(time_dict.items(), key=lambda x: x[0])

    # --- Write to text file ---
    with open(output_txt, "w") as f:
        for t, (lat, lon) in sorted_items:
            f.write(f"{t.isoformat()}: {lat}: {lon}\n")

    print(f"GPS time log saved to {output_txt}")


# Your file:
gpx_to_time_log("GX010294_track.gpx", "GX010294_time_log.txt")
