import os
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from flask import Response
import plotly.graph_objects as go
import cv2

from video_stream import frame_stream, set_warning_flag, set_stats_callback
from risk_calculator import calculate_risk

# -----------------------------
# Setup
# -----------------------------
VIDEO_FOLDER = "videos"
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

# -----------------------------
# Global Stats & State
# -----------------------------
stats = {
    "min_conf": None,
    "max_conf": None,
    "sum_conf": 0.0,
    "count_conf": 0,

    "dry": 0,
    "puddle": 0,
    "standing": 0,
    "overall": "N/A",

    "risk": 0.0,
    "avg_risk": 0.0,
    "risk_count": 0,

    "speed": 60.0,
    "pressure": 32.0,
    "speed_input_value": 60.0,
    "user_input": 100,
    "warning": False,

    "v2x_message": "",

    # GPS
    "gps_points": [],      # list of {"lat": ..., "lon": ...}
    "gps_index": 0,        # current index into gps_points
    "gps_lat": None,
    "gps_lon": None,
}

throttle_reduction_active = False
safe_counter = 0
current_video_path = None

# -----------------------------
# GPS Loader
# -----------------------------
def load_gps_file(video_name):
    """
    GPS file shares base name with video.
    Each line: TIMESTAMP: lon: lat
    We ignore the timestamp (you've guaranteed alignment) and just
    store lon/lat in order.
    """
    base, _ = os.path.splitext(video_name)
    gps_file = base + ".txt"
    gps_path = os.path.join(VIDEO_FOLDER, gps_file)

    gps_points = []
    if os.path.exists(gps_path):
        with open(gps_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(":")
                if len(parts) < 3:
                    continue

                try:
                    lon = float(parts[-2].strip())
                    lat = float(parts[-1].strip())
                except ValueError:
                    continue

                gps_points.append({"lat": lat, "lon": lon})

    return gps_points


def advance_gps_index():
    """
    Advance gps_index by one, clamp at end.
    Called once per stats interval (1 second) to keep GPS in sync
    with video, since you've guaranteed the GPS file spans exactly
    the video duration.
    """
    if not stats["gps_points"]:
        return

    if stats["gps_index"] < len(stats["gps_points"]) - 1:
        stats["gps_index"] += 1

    point = stats["gps_points"][stats["gps_index"]]
    stats["gps_lat"] = point["lat"]
    stats["gps_lon"] = point["lon"]

# -----------------------------
# Detection Stats Callback
# -----------------------------
def detection_stats_callback(confidence, label):
    global throttle_reduction_active, safe_counter

    # Confidence stats
    if stats["min_conf"] is None or confidence < stats["min_conf"]:
        stats["min_conf"] = confidence
    if stats["max_conf"] is None or confidence > stats["max_conf"]:
        stats["max_conf"] = confidence

    stats["sum_conf"] += confidence
    stats["count_conf"] += 1

    # Road condition stats
    if label == "dry":
        stats["dry"] += 1
        stats["v2x_message"] = ""

    elif label == "puddle":
        stats["puddle"] += 1
        stats["v2x_message"] = ""

    elif label == "standingwater":
        stats["standing"] += 1

        # Use current GPS position for V2X
        if stats["gps_lat"] is not None and stats["gps_lon"] is not None:
            stats["v2x_message"] = (
                f"V2X: Standing Water at Lat {stats['gps_lat']:.5f}, "
                f"Lon {stats['gps_lon']:.5f}"
            )
        else:
            stats["v2x_message"] = "V2X: Standing Water (No GPS available)"

    conds = {
        "Dry": stats["dry"],
        "Puddle": stats["puddle"],
        "Standing Water": stats["standing"],
    }
    stats["overall"] = max(conds, key=conds.get)

    # Risk calculation
    speed = stats["speed"]
    pressure = stats["pressure"]
    risk = calculate_risk(confidence, label, speed, pressure)
    risk_percent = risk * 100

    stats["risk"] = risk_percent
    stats["risk_count"] += 1
    stats["avg_risk"] = (
        (stats["avg_risk"] * (stats["risk_count"] - 1) + risk_percent)
        / stats["risk_count"]
    )

    # Speed reduction logic
    if risk_percent > 75:
        throttle_reduction_active = True
        safe_counter = 0
        stats["user_input"] = max(0, stats["user_input"] - 10)
        stats["speed"] = max(0, stats["speed"] * 0.9)

    elif risk_percent < 60:
        if throttle_reduction_active:
            safe_counter += 1
            if safe_counter >= 4:
                throttle_reduction_active = False
                stats["user_input"] = 100
                stats["speed"] = stats["speed_input_value"]

    # Warning logic
    if risk_percent > 60:
        stats["warning"] = True
        safe_counter = 0
    else:
        if stats["warning"]:
            safe_counter += 1
            if safe_counter >= 4:
                stats["warning"] = False
                stats["v2x_message"] = ""

    set_warning_flag(stats["warning"])


set_stats_callback(detection_stats_callback)

# -----------------------------
# Flask Route for Video Stream
# -----------------------------
@server.route("/video_feed")
def video_feed():
    global current_video_path
    if not current_video_path:
        return "No video selected", 400
    return Response(
        frame_stream(current_video_path),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

# -----------------------------
# Layout
# -----------------------------
def get_video_list():
    return [
        f for f in os.listdir(VIDEO_FOLDER)
        if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))
    ]


overview_layout = html.Div(
    [
        html.H2("Aquaplaning Detection Dashboard"),
        html.Hr(),

        html.H4("Select Video"),
        dcc.Dropdown(
            id="video-select",
            options=[{"label": v, "value": v} for v in get_video_list()],
            placeholder="Choose a video...",
            style={"width": "50%"},
        ),

        # Speed & Pressure
        html.Div(
            [
                dbc.InputGroup(
                    [
                        dbc.InputGroupText("Vehicle Speed (km/h)"),
                        dbc.Button("-", id="speed-minus", color="secondary"),
                        dbc.Input(
                            id="speed-input",
                            type="number",
                            value=60,
                            min=0,
                            max=200,
                        ),
                        dbc.Button("+", id="speed-plus", color="secondary"),
                    ],
                    className="mb-2",
                ),
                dbc.InputGroup(
                    [
                        dbc.InputGroupText("Tyre Pressure (PSI)"),
                        dbc.Button("-", id="pressure-minus", color="secondary"),
                        dbc.Input(
                            id="pressure-input",
                            type="number",
                            value=32,
                            min=10,
                            max=50,
                        ),
                        dbc.Button("+", id="pressure-plus", color="secondary"),
                    ],
                    className="mb-2",
                ),
            ],
            style={"marginTop": "20px", "maxWidth": "500px"},
        ),

        dbc.Button(
            "Start Detection",
            id="start-detection-btn",
            color="primary",
            className="mt-3",
        ),
        html.Div(id="detection-status", className="mt-3"),

        html.Hr(),

        # Stats + Vehicle Dash
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H4("Risk Stats"),
                        html.Ul(
                            [
                                html.Li(id="risk-current"),
                                html.Li(id="risk-average"),
                            ]
                        ),
                        html.H4("Confidence Stats"),
                        html.Ul(
                            [
                                html.Li(id="conf-min"),
                                html.Li(id="conf-max"),
                                html.Li(id="conf-avg"),
                            ]
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        html.H4("Road Condition Stats"),
                        html.Ul(
                            [
                                html.Li(id="cond-dry"),
                                html.Li(id="cond-puddle"),
                                html.Li(id="cond-standing"),
                                html.Li(id="cond-overall"),
                            ]
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        html.H4("Vehicle Dash"),
                        html.Div(
                            id="vehicle-speed",
                            style={"fontSize": "24px", "fontWeight": "bold"},
                        ),
                        html.Div(
                            id="vehicle-input",
                            style={"fontSize": "20px"},
                        ),
                        html.Div(
                            id="vehicle-warning",
                            style={
                                "fontSize": "22px",
                                "fontWeight": "bold",
                                "color": "red",
                            },
                        ),
                        html.Div(
                            id="vehicle-v2x",
                            style={"fontSize": "18px", "color": "#00eaff"},
                        ),
                    ],
                    md=4,
                ),
            ]
        ),

        html.Hr(),
        html.H4("Video & Map"),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Img(
                            id="video-stream",
                            src="",
                            style={
                                "width": "100%",
                                "border": "2px solid #444",
                                "maxHeight": "450px",
                                "objectFit": "cover",
                            },
                        ),
                    ],
                    md=8,
                ),
                dbc.Col(
                    [
                        dcc.Graph(
                            id="gps-map",
                            style={
                                "height": "450px",
                                "border": "2px solid #444",
                            },
                        )
                    ],
                    md=4,
                ),
            ]
        ),

        html.Hr(),

        dcc.Interval(id="stats-interval", interval=1000, n_intervals=0),
    ],
    className="p-4",
)

app.layout = html.Div([dcc.Location(id="url"), overview_layout])

# -----------------------------
# Callbacks
# -----------------------------
@app.callback(
    Output("video-stream", "src"),
    Output("detection-status", "children"),
    Input("start-detection-btn", "n_clicks"),
    State("video-select", "value"),
    State("speed-input", "value"),
    State("pressure-input", "value"),
    prevent_initial_call=True,
)
def start_detection(n, selected_video, speed_value, pressure_value):
    global current_video_path

    if not selected_video:
        return "", "Please select a video first."

    stats["speed"] = speed_value
    stats["pressure"] = pressure_value
    stats["speed_input_value"] = speed_value

    # Reset stats
    stats["min_conf"] = None
    stats["max_conf"] = None
    stats["sum_conf"] = 0.0
    stats["count_conf"] = 0
    stats["dry"] = 0
    stats["puddle"] = 0
    stats["standing"] = 0
    stats["overall"] = "N/A"
    stats["risk"] = 0.0
    stats["avg_risk"] = 0.0
    stats["risk_count"] = 0
    stats["user_input"] = 100
    stats["warning"] = False
    stats["v2x_message"] = ""

    # Reset GPS
    stats["gps_points"] = load_gps_file(selected_video)
    stats["gps_index"] = 0
    stats["gps_lat"] = None
    stats["gps_lon"] = None

    current_video_path = os.path.join(VIDEO_FOLDER, selected_video)
    return "/video_feed", f"Detection started on {selected_video}"


# Speed adjust
@app.callback(
    Output("speed-input", "value"),
    Input("speed-minus", "n_clicks"),
    Input("speed-plus", "n_clicks"),
    State("speed-input", "value"),
    prevent_initial_call=True,
)
def adjust_speed(minus, plus, current):
    ctx = dash.callback_context
    if not ctx.triggered:
        return current
    button = ctx.triggered[0]["prop_id"].split(".")[0]
    if button == "speed-minus":
        return max(0, current - 1)
    if button == "speed-plus":
        return min(200, current + 1)
    return current


# Pressure adjust
@app.callback(
    Output("pressure-input", "value"),
    Input("pressure-minus", "n_clicks"),
    Input("pressure-plus", "n_clicks"),
    State("pressure-input", "value"),
    prevent_initial_call=True,
)
def adjust_pressure(minus, plus, current):
    ctx = dash.callback_context
    if not ctx.triggered:
        return current
    button = ctx.triggered[0]["prop_id"].split(".")[0]
    if button == "pressure-minus":
        return max(10, current - 1)
    if button == "pressure-plus":
        return min(50, current + 1)
    return current


# Live stats update + GPS advance
@app.callback(
    [
        Output("risk-current", "children"),
        Output("risk-average", "children"),
        Output("conf-min", "children"),
        Output("conf-max", "children"),
        Output("conf-avg", "children"),
        Output("cond-dry", "children"),
        Output("cond-puddle", "children"),
        Output("cond-standing", "children"),
        Output("cond-overall", "children"),
        Output("vehicle-speed", "children"),
        Output("vehicle-input", "children"),
        Output("vehicle-warning", "children"),
        Output("vehicle-v2x", "children"),
    ],
    Input("stats-interval", "n_intervals"),
)
def update_stats(_):
    # Advance GPS index once per second
    advance_gps_index()

    if stats["count_conf"] > 0:
        avg_conf = stats["sum_conf"] / stats["count_conf"]
    else:
        avg_conf = 0.0

    warning_text = ""
    if stats["warning"]:
        warning_text = "REDUCE SPEED — Disabling Cruise Control"

    return (
        f"Risk: {stats['risk']:.1f}%",
        f"Avg Risk: {stats['avg_risk']:.1f}%",
        f"Min Confidence: {stats['min_conf']:.2f}" if stats["min_conf"] else "Min Confidence: N/A",
        f"Max Confidence: {stats['max_conf']:.2f}" if stats["max_conf"] else "Max Confidence: N/A",
        f"Avg Confidence: {avg_conf:.2f}" if stats["count_conf"] else "Avg Confidence: N/A",
        f"Dry: {stats['dry']}",
        f"Puddle: {stats['puddle']}",
        f"Standing Water: {stats['standing']}",
        f"Overall: {stats['overall']}",
        f"Speed: {stats['speed']:.1f} km/h",
        f"User Available Input: {stats['user_input']}%",
        warning_text,
        stats["v2x_message"],
    )


# Map update
@app.callback(
    Output("gps-map", "figure"),
    Input("stats-interval", "n_intervals"),
)
def update_map(_):
    lat = stats["gps_lat"]
    lon = stats["gps_lon"]

    if lat is None or lon is None:
        return go.Figure(
            layout=go.Layout(
                template="plotly_dark",
                title="GPS Position (Waiting for data)",
            )
        )

    fig = go.Figure()

    # BLUE DOT — current car position
    fig.add_trace(
        go.Scattermapbox(
            lat=[lat],
            lon=[lon],
            mode="markers",
            marker=dict(size=16, color="blue"),
            name="Current Position",
        )
    )

    # RED DOT — V2X event (same position, only when message present)
    if stats["v2x_message"]:
        fig.add_trace(
            go.Scattermapbox(
                lat=[lat],
                lon=[lon],
                mode="markers",
                marker=dict(size=20, color="red"),
                name="Standing Water",
            )
        )

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            zoom=15,
            center=dict(lat=lat, lon=lon),
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        template="plotly_dark",
        showlegend=False,
    )

    return fig


if __name__ == "__main__":
    app.run(debug=True)
