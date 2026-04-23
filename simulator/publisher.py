import paho.mqtt.client as mqtt
import json
import time
import random
import datetime

# ── Config ───────────────────────────────────────────────────
BROKER = "localhost"
PORT   = 1883
TOPIC  = "iot/device/logs"

# ── Preset demo scenarios ────────────────────────────────────
# Each scenario simulates one real-world failure case
# Edit ACTIVE_SCENARIO at the bottom to switch

SCENARIOS = {

    "normal_factory": {
        "description": "Factory motor — healthy operation",
        "deviceId": "factory-motor-01",
        "deviceType": "industrial_motor",
        "domain": "factory",
        "base": {
            "temperature": 58.0, "vibration": 3.2, "pressure": 52.0,
            "voltage": 235.0, "current": 14.0, "humidity": 45.0,
            "restart_count": 0, "overload_flag": 0, "connection_failures": 0
        },
        "noise": {
            "temperature": 2.0, "vibration": 0.3, "pressure": 2.0,
            "voltage": 1.5, "current": 0.5, "humidity": 2.0,
            "restart_count": 0, "overload_flag": 0, "connection_failures": 0
        }
    },

    "bearing_failure": {
        "description": "Factory motor — bearing failure developing",
        "deviceId": "factory-motor-01",
        "deviceType": "industrial_motor",
        "domain": "factory",
        "base": {
            "temperature": 90.0, "vibration": 10.5, "pressure": 44.0,
            "voltage": 232.0, "current": 22.0, "humidity": 46.0,
            "restart_count": 4, "overload_flag": 1, "connection_failures": 0
        },
        "noise": {
            "temperature": 2.0, "vibration": 0.5, "pressure": 1.5,
            "voltage": 1.0, "current": 1.0, "humidity": 1.5,
            "restart_count": 1, "overload_flag": 0, "connection_failures": 0
        }
    },

    "cooling_failure": {
        "description": "Smart home AC — cooling failure",
        "deviceId": "home-ac-01",
        "deviceType": "home_ac",
        "domain": "smart_home",
        "base": {
            "temperature": 97.0, "vibration": 2.8, "pressure": 18.0,
            "voltage": 223.0, "current": 8.0, "humidity": 58.0,
            "restart_count": 7, "overload_flag": 0, "connection_failures": 1
        },
        "noise": {
            "temperature": 1.5, "vibration": 0.2, "pressure": 1.5,
            "voltage": 1.0, "current": 0.5, "humidity": 2.0,
            "restart_count": 1, "overload_flag": 0, "connection_failures": 0
        }
    },

    "compressor_fault": {
        "description": "Smart home AC — compressor fault",
        "deviceId": "home-ac-02",
        "deviceType": "home_ac",
        "domain": "smart_home",
        "base": {
            "temperature": 98.0, "vibration": 5.5, "pressure": 16.0,
            "voltage": 220.0, "current": 9.0, "humidity": 60.0,
            "restart_count": 8, "overload_flag": 1, "connection_failures": 1
        },
        "noise": {
            "temperature": 1.5, "vibration": 0.3, "pressure": 1.0,
            "voltage": 1.0, "current": 0.5, "humidity": 2.0,
            "restart_count": 1, "overload_flag": 0, "connection_failures": 0
        }
    },

    "pump_failure": {
        "description": "Agriculture — water pump failure",
        "deviceId": "agri-pump-01",
        "deviceType": "water_pump",
        "domain": "agriculture",
        "base": {
            "temperature": 68.0, "vibration": 1.5, "pressure": 8.0,
            "voltage": 210.0, "current": 12.0, "humidity": 80.0,
            "restart_count": 5, "overload_flag": 0, "connection_failures": 1
        },
        "noise": {
            "temperature": 2.0, "vibration": 0.2, "pressure": 1.0,
            "voltage": 2.0, "current": 0.5, "humidity": 3.0,
            "restart_count": 1, "overload_flag": 0, "connection_failures": 1
        }
    },

    "power_backup_failure": {
        "description": "Hospital — power backup failure",
        "deviceId": "hospital-monitor-01",
        "deviceType": "oxygen_monitor",
        "domain": "hospital",
        "base": {
            "temperature": 23.0, "vibration": 0.4, "pressure": 93.0,
            "voltage": 155.0, "current": 4.0, "humidity": 52.0,
            "restart_count": 5, "overload_flag": 0, "connection_failures": 7
        },
        "noise": {
            "temperature": 0.5, "vibration": 0.05, "pressure": 1.0,
            "voltage": 3.0, "current": 0.3, "humidity": 1.0,
            "restart_count": 1, "overload_flag": 0, "connection_failures": 1
        }
    },

    "hvac_failure": {
        "description": "Office server room — HVAC failure",
        "deviceId": "office-hvac-01",
        "deviceType": "hvac_unit",
        "domain": "office",
        "base": {
            "temperature": 34.0, "vibration": 3.5, "pressure": 30.0,
            "voltage": 229.0, "current": 16.0, "humidity": 82.0,
            "restart_count": 4, "overload_flag": 0, "connection_failures": 1
        },
        "noise": {
            "temperature": 1.5, "vibration": 0.3, "pressure": 1.5,
            "voltage": 1.0, "current": 0.5, "humidity": 2.0,
            "restart_count": 1, "overload_flag": 0, "connection_failures": 0
        }
    },

    "network_fault": {
        "description": "Hospital — network/connectivity fault",
        "deviceId": "hospital-monitor-02",
        "deviceType": "patient_monitor",
        "domain": "hospital",
        "base": {
            "temperature": 22.0, "vibration": 0.3, "pressure": 94.0,
            "voltage": 227.0, "current": 3.0, "humidity": 51.0,
            "restart_count": 8, "overload_flag": 0, "connection_failures": 10
        },
        "noise": {
            "temperature": 0.5, "vibration": 0.05, "pressure": 1.0,
            "voltage": 1.0, "current": 0.2, "humidity": 1.0,
            "restart_count": 1, "overload_flag": 0, "connection_failures": 2
        }
    },

    "motor_overload": {
        "description": "Factory motor — sustained overload",
        "deviceId": "factory-motor-02",
        "deviceType": "industrial_motor",
        "domain": "factory",
        "base": {
            "temperature": 93.0, "vibration": 7.5, "pressure": 46.0,
            "voltage": 218.0, "current": 28.0, "humidity": 47.0,
            "restart_count": 3, "overload_flag": 1, "connection_failures": 0
        },
        "noise": {
            "temperature": 2.0, "vibration": 0.4, "pressure": 1.5,
            "voltage": 1.5, "current": 1.0, "humidity": 1.5,
            "restart_count": 1, "overload_flag": 0, "connection_failures": 0
        }
    },

}

# ── MQTT setup ───────────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Connected to MQTT broker at {BROKER}:{PORT}")
    else:
        print(f"❌ MQTT connection failed — code {rc}")

client = mqtt.Client()
client.on_connect = on_connect
client.connect(BROKER, PORT, keepalive=60)
client.loop_start()

# ── Publisher ────────────────────────────────────────────────
def apply_noise(base, noise):
    result = {}
    for key in base:
        n = noise.get(key, 0)
        if n == 0:
            result[key] = base[key]
        elif key in ("restart_count", "connection_failures"):
            result[key] = max(0, int(base[key] + random.randint(-int(n), int(n))))
        elif key == "overload_flag":
            result[key] = int(base[key])
        else:
            result[key] = round(base[key] + random.uniform(-n, n), 2)
    return result

def publish_reading(scenario_name, interval=3.0):
    scenario = SCENARIOS[scenario_name]
    device   = {
        "deviceId":   scenario["deviceId"],
        "deviceType": scenario["deviceType"],
        "domain":     scenario["domain"]
    }
    noisy = apply_noise(scenario["base"], scenario["noise"])
    payload = {
        **device,
        **noisy,
        "scenario":  scenario_name,
        "timestamp": datetime.datetime.now().isoformat()
    }
    client.publish(TOPIC, json.dumps(payload))
    print(f"📡 [{payload['deviceId']}] temp={noisy['temperature']:.1f}°C  "
          f"vib={noisy['vibration']:.2f}g  "
          f"pres={noisy['pressure']:.1f}  "
          f"volt={noisy['voltage']:.1f}V  "
          f"restarts={noisy['restart_count']}")

# ============================================================
# ← CHANGE THIS to switch scenarios during your demo
ACTIVE_SCENARIO = "cooling_failure"
# ============================================================

if __name__ == "__main__":
    print(f"\n🚀 Simulator started")
    print(f"   Scenario : {ACTIVE_SCENARIO}")
    print(f"   Device   : {SCENARIOS[ACTIVE_SCENARIO]['deviceId']}")
    print(f"   Info     : {SCENARIOS[ACTIVE_SCENARIO]['description']}")
    print(f"   Topic    : {TOPIC}")
    print(f"   Interval : 3 seconds\n")
    print("Available scenarios:", list(SCENARIOS.keys()))
    print("-" * 60)

    while True:
        try:
            publish_reading(ACTIVE_SCENARIO)
            time.sleep(3)
        except KeyboardInterrupt:
            print("\n🛑 Simulator stopped")
            client.loop_stop()
            break