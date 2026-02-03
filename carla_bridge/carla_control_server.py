#!/usr/bin/env python3
import socket
import json
import time

import carla  # Python 3.5 uyumlu

CARLA_HOST = "localhost"
CARLA_PORT = 2000

CONTROL_HOST = "0.0.0.0"
CONTROL_PORT = 9001


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
        print("Araç bulunamadı! CARLA'da vehicle spawn olduğuna emin ol.")
        return

    print("Araç bulundu:", hero.id, hero.type_id)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((CONTROL_HOST, CONTROL_PORT))
    server.listen(1)

    print("[CONTROL] Dinleniyor: {}:{}".format(CONTROL_HOST, CONTROL_PORT))

    conn, addr = server.accept()
    print("[CONTROL] ROS2 bağlandı:", addr)

    f = conn.makefile("rb")

    while True:
        line = f.readline()
        if not line:
            break

        try:
            cmd = json.loads(line.decode("utf-8"))
        except Exception as e:
            print("JSON parse hatası:", e)
            continue

        if cmd.get("msg_type") != "vehicle_control":
            continue

        throttle = float(cmd.get("throttle", 0.0))
        steer = float(cmd.get("steer", 0.0))
        brake = float(cmd.get("brake", 0.0))
        reverse = bool(cmd.get("reverse", False))
        hand_brake = bool(cmd.get("hand_brake", False))

        control = carla.VehicleControl(
            throttle=throttle,
            steer=steer,
            brake=brake,
            reverse=reverse,
            hand_brake=hand_brake
        )

        hero.apply_control(control)
        time.sleep(0.01)


if __name__ == "__main__":
    main()

