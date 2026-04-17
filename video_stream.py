import cv2
import os
from inference_sdk import InferenceHTTPClient

# -----------------------------
# Roboflow Setup
# -----------------------------
CLIENT = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key="5TZn9YOxt8duqqEw5eSV"
)

MODEL_ID = "roadclass/2"

# Shared flag controlled by Dash
warning_flag = False

# Shared callback (Dash will set this)
stats_callback = None


def set_warning_flag(value: bool):
    global warning_flag
    warning_flag = value


def set_stats_callback(cb):
    global stats_callback
    stats_callback = cb


# -----------------------------
# Frame Generator for Dash
# -----------------------------
def frame_stream(video_path):
    global warning_flag, stats_callback

    cap = cv2.VideoCapture(video_path)

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 30

    frames_per_2_seconds = int(fps * 1)
    frame_count = 0

    last_label = "..."
    last_conf = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        frame_count += 1

        # Run inference every N frames
        if frame_count % frames_per_2_seconds == 0:
            small = cv2.resize(frame, (640, 360))
            result = CLIENT.infer(small, model_id=MODEL_ID)
            predictions = result.get("predictions", [])

            if len(predictions) == 0:
                last_label = "dry"
                last_conf = 1.0
            else:
                pred = predictions[0]
                last_label = pred["class"]
                last_conf = pred["confidence"]

            # Send stats back to Dash
            if stats_callback:
                stats_callback(last_conf, last_label)

        # Draw prediction
        cv2.putText(
            frame,
            f"{last_label} ({last_conf:.2f})",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            (0, 255, 0),
            3
        )

        # Draw warning overlay
        if warning_flag:
            cv2.putText(
                frame,
                "REDUCE SPEED",
                (200, 80),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.5,
                (0, 0, 255),
                4
            )

        # Encode frame for streaming
        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )
