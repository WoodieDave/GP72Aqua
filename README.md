# Aquaplaning Detection Dashboard

A real‑time aquaplaning detection dashboard that combines:

- Roboflow computer vision inference  
- Risk scoring  
- Vehicle telemetry (speed, tyre pressure, throttle availability)  
- V2X event signalling  
- GPS‑based map tracking  
- Video playback with live overlays  

The system processes dashcam footage, detects road surface conditions, calculates aquaplaning risk, and displays the vehicle’s real‑time position on a map. GPS logs are aligned 1:1 with each video (start → start, end → end).

---

## 🚗 Features

### **Computer Vision (Roboflow)**
- Detects: `dry`, `puddle`, `standingwater`
- Runs inference once per second
- Displays label + confidence on the video feed

### **Risk Engine**
- Calculates risk based on:
  - Detection confidence  
  - Road condition  
  - Vehicle speed  
  - Tyre pressure  
- Automatic throttle reduction when risk is high  
- Automatic recovery when safe  

### **Vehicle Dashboard**
- Live speed  
- User available throttle input  
- Warning overlay (“REDUCE SPEED”)  
- V2X event messages  

### **GPS Tracking**
- GPS file matches video name (e.g., `WetRoad.mp4` → `WetRoad.txt`)
- Each line contains:  
  `timestamp: lon: lat`
- Timestamps are ignored (you guarantee alignment)
- Blue dot = current vehicle position  
- Red dot = standing water V2X event  
- Map updates once per second  

### **UI Layout**
- Stats panels at the top  
- Video + Map side‑by‑side underneath  
- Dark theme (Dash + Bootstrap)  

---

## 📁 File Structure

