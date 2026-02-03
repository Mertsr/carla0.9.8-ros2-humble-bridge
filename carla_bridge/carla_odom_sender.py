#!/usr/bin/env python3
import socket
import json
import time
import carla

CARLA_HOST = "localhost"
CARLA_PORT = 2000

TELEMETRY_HOST = "127.0.0.1"
TELEMETRY_PORT = 9000

def find_hero(world):
    for a in world.get_actors():
        if "vehicle" in a.type_id and a.attributes.get("role_name") == "hero":
            return a
    for a in world.get_actors():
        if "vehicle" in a.type_id:
            return a
    return None

def main():
    client = carla.Client(CARLA_HOST, CARLA_PORT)
    client.set_timeout(5.0)
    world = client.get_world()

    hero = find_hero(world)
    if hero is None:
        print("Hero/vehicle bulunamadı")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((TELEMETRY_HOST, TELEMETRY_PORT))
    print("[TELEMETRY] ROS2'ye baglandi: {}:{}".format(TELEMETRY_HOST, TELEMETRY_PORT))

    while True:
        t = hero.get_transform()
        loc = t.location
        rot = t.rotation

        v = hero.get_velocity()         # m/s (world frame)
        w = hero.get_angular_velocity() # rad/s (world frame)

        header = {
            "msg_type": "odom",
            "x": loc.x, "y": loc.y, "z": loc.z,
            "roll": rot.roll, "pitch": rot.pitch, "yaw": rot.yaw,
            "vx": v.x, "vy": v.y, "vz": v.z,
            "wx": w.x, "wy": w.y, "wz": w.z
        }

        sock.sendall((json.dumps(header) + "\n").encode("utf-8"))
        time.sleep(0.05)  # 20 Hz

if __name__ == "__main__":
    main()
