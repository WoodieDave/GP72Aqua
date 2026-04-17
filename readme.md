
---

## 🧠 How It Works

### **video_stream.py**
- Loads video frames with OpenCV  
- Sends frames to Roboflow for inference  
- Draws predictions and warnings  
- Streams frames to Dash via Flask route `/video_feed`

### **web_dashboard.py**
- Builds the dashboard UI  
- Lets the user select a video  
- Adjusts speed and tyre pressure  
- Displays:
  - Risk %
  - Confidence stats
  - Road condition counts
  - Vehicle speed, input, warnings
  - V2X messages

### **risk_calculator.py**
- Computes risk based on:
  - Road condition
  - Confidence
  - Speed
  - Tyre pressure

---

## 🛠 Requirements

- Python 3.10+
- Internet connection (Roboflow inference)
- A GPU is *not* required

---

## 📡 Notes

- The Roboflow API key is required for inference.
- The dashboard updates every second using a Dash `Interval` component.
- The system loops videos automatically when they reach the end.

---

## 🧩 Future Improvements (Optional)

- Add logging of risk events  
- Add a sidebar for navigation  
- Add a settings page for API keys  
- Add a real vehicle‑style gauge cluster  

---

## 📬 Support

If you want help restructuring the project again, adding new features, or cleaning up the UI, just ask.
