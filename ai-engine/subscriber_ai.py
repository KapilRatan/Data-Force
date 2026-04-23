import paho.mqtt.client as mqtt
import json
import joblib
import numpy as np
import os

# ── Config ───────────────────────────────────────────────────
BROKER      = "localhost"
PORT        = 1883
TOPIC       = "iot/device/logs"
MODELS_DIR  = os.path.join(os.path.dirname(__file__), "..", "models")

# ── Load models ──────────────────────────────────────────────
print("🔄 Loading AI models...")
anomaly_model = joblib.load(os.path.join(MODELS_DIR, "anomaly_model.pkl"))
rca_model     = joblib.load(os.path.join(MODELS_DIR, "rca_model.pkl"))
label_encoder = joblib.load(os.path.join(MODELS_DIR, "label_encoder.pkl"))
FEATURES      = joblib.load(os.path.join(MODELS_DIR, "features.pkl"))
print(f"✅ Models loaded | Features: {FEATURES}\n")

# ── Rule engine — human-readable explanations ────────────────
EXPLANATIONS = {
    "bearing_failure": {
        "reason": "High vibration + sustained overload + elevated temperature detected",
        "action": "Shut down motor immediately. Schedule urgent bearing inspection and replacement.",
        "severity": "CRITICAL"
    },
    "cooling_failure": {
        "reason": "Temperature spike + pressure drop + repeated restart events",
        "action": "Inspect cooling unit. Check refrigerant level and condenser coil.",
        "severity": "CRITICAL"
    },
    "compressor_fault": {
        "reason": "Extreme temperature + pressure loss + overload flag + restart loop",
        "action": "Power off unit immediately. Call HVAC technician.",
        "severity": "CRITICAL"
    },
    "motor_overload": {
        "reason": "Sustained high current + elevated temperature + overload event",
        "action": "Reduce load. Check power supply, motor windings, and mechanical resistance.",
        "severity": "HIGH"
    },
    "pump_failure": {
        "reason": "Critically low pressure + repeated restart events + no flow signal",
        "action": "Check pump inlet for blockage. Inspect impeller and pipe connections.",
        "severity": "HIGH"
    },
    "hvac_failure": {
        "reason": "Server room temperature rising + high humidity + reduced airflow pressure",
        "action": "Inspect HVAC filters and fan units. Activate backup cooling if available.",
        "severity": "HIGH"
    },
    "power_backup_failure": {
        "reason": "Voltage drop detected + multiple connection failures + restart events",
        "action": "Check UPS battery and mains connection. Activate emergency protocol.",
        "severity": "CRITICAL"
    },
    "network_fault": {
        "reason": "High connection failure count + frequent restarts + signal instability",
        "action": "Check network cable, router, and device firmware. Restart network stack.",
        "severity": "MEDIUM"
    },
}

SEVERITY_COLORS = {
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MEDIUM":   "🟡",
}

# ── AI Analysis ──────────────────────────────────────────────
def analyze(payload: dict):
    # Build feature vector — must match training order exactly
    try:
        X = np.array([[payload[f] for f in FEATURES]])
    except KeyError as e:
        print(f"⚠️  Missing feature in payload: {e} — skipping")
        return

    # ── Step 1: Anomaly detection ─────────────────────────
    anomaly_score = anomaly_model.decision_function(X)[0]
    prediction    = anomaly_model.predict(X)[0]  # -1 = anomaly, 1 = normal
    is_anomaly    = prediction == -1

    device_id   = payload.get("deviceId", "unknown")
    device_type = payload.get("deviceType", "unknown")
    domain      = payload.get("domain", "unknown")

    if not is_anomaly:
        print(f"✅ [{device_id}] Normal  |  score: {anomaly_score:.4f}")
        return

    # ── Step 2: Root cause prediction ─────────────────────
    rca_encoded  = rca_model.predict(X)[0]
    rca_proba    = rca_model.predict_proba(X)[0]
    confidence   = round(float(max(rca_proba)) * 100, 1)
    root_cause   = label_encoder.inverse_transform([rca_encoded])[0]

    info = EXPLANATIONS.get(root_cause, {
        "reason":   "Unusual sensor pattern detected across multiple parameters",
        "action":   "Inspect device immediately. Contact maintenance team.",
        "severity": "HIGH"
    })

    severity_icon = SEVERITY_COLORS.get(info["severity"], "🟡")

    # ── Step 3: Print alert ───────────────────────────────
    print("\n" + "╔" + "═" * 57 + "╗")
    print(f"║  {severity_icon}  ALERT — {info['severity']:<46}║")
    print("╠" + "═" * 57 + "╣")
    print(f"║  Device ID   : {device_id:<41}║")
    print(f"║  Device Type : {device_type:<41}║")
    print(f"║  Domain      : {domain:<41}║")
    print("╠" + "═" * 57 + "╣")
    print(f"║  Root Cause  : {root_cause.replace('_', ' ').upper():<41}║")
    print(f"║  Confidence  : {str(confidence) + '%':<41}║")
    print("╠" + "═" * 57 + "╣")
    reason_parts = [info['reason'][i:i+41] for i in range(0, len(info['reason']), 41)]
    for i, part in enumerate(reason_parts):
        label = "  Reason      : " if i == 0 else "                "
        print(f"║{label}{part:<41}║")
    action_parts = [info['action'][i:i+41] for i in range(0, len(info['action']), 41)]
    for i, part in enumerate(action_parts):
        label = "  Action      : " if i == 0 else "                "
        print(f"║{label}{part:<41}║")
    print("╠" + "═" * 57 + "╣")
    print(f"║  Anomaly Score: {str(round(anomaly_score, 4)):<40}║")
    ts = payload.get("timestamp", "N/A")[:19]
    print(f"║  Timestamp   : {ts:<41}║")
    print("╚" + "═" * 57 + "╝\n")

# ── MQTT callbacks ───────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ AI Engine connected to MQTT at {BROKER}:{PORT}")
        print(f"   Subscribed to: {TOPIC}")
        print(f"   Waiting for sensor data...\n")
        print("-" * 59)
        client.subscribe(TOPIC)
    else:
        print(f"❌ MQTT connection failed — code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        analyze(payload)
    except json.JSONDecodeError as e:
        print(f"⚠️  JSON decode error: {e}")
    except Exception as e:
        print(f"⚠️  Unexpected error: {e}")

# ── Start ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🤖 AI Engine starting...")
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=60)
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n🛑 AI Engine stopped")
        client.disconnect()