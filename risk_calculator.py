# risk_calculator.py

def calculate_risk(confidence, label, speed, pressure):
    weights = {
        "dry": 0.1,
        "puddle": 0.5,
        "standingwater": 1.0
    }
    cond_weight = weights.get(label, 0.1)

    speed_factor = min(speed / 120, 1)

    if pressure < 28:
        pressure_factor = 1.4
    elif pressure > 32:
        pressure_factor = 0.8
    else:
        pressure_factor = 1.0

    risk = cond_weight * confidence * speed_factor * pressure_factor
    return min(risk, 1.0)
