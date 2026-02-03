#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import json
import time
import threading

import carla
import numpy as np


CARLA_HOST = "localhost"
CARLA_PORT = 2000

TELEMETRY_HOST = "127.0.0.1"
TELEMETRY_PORT = 9000

MAIN_LOOP_DT = 0.05  # 20 Hz


def find_hero(world):
    for a in world.get_actors():
        try:
            if "vehicle" in a.type_id and a.attributes.get("role_name") == "hero":
                return a
        except Exception:
            pass
    for a in world.get_actors():
        try:
            if "vehicle" in a.type_id:
                return a
        except Exception:
            pass
    return None


def connect_retry(host, port, retry_sec=0.5):
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            return s
        except Exception as e:
            print("[TELEMETRY] baglanamadi ({}:{}) -> {}. tekrar deniyorum...".format(host, port, e))
            time.sleep(retry_sec)


def main():
    client = carla.Client(CARLA_HOST, CARLA_PORT)
    client.set_timeout(10.0)
    world = client.get_world()

    hero = find_hero(world)
    if hero is None:
        print("Hero/vehicle bulunamadı")
        return

    sock = connect_retry(TELEMETRY_HOST, TELEMETRY_PORT)
    print("[TELEMETRY] ROS2'ye baglandi: {}:{}".format(TELEMETRY_HOST, TELEMETRY_PORT))

    bp_lib = world.get_blueprint_library()

    # --------- IMU ----------
    imu_bp = bp_lib.find("sensor.other.imu")
    if imu_bp.has_attribute("sensor_tick"):
        imu_bp.set_attribute("sensor_tick", "0.05")  # 20 Hz
    imu_sensor = world.spawn_actor(imu_bp, carla.Transform(), attach_to=hero)

    # --------- GNSS ----------
    gnss_bp = bp_lib.find("sensor.other.gnss")
    if gnss_bp.has_attribute("sensor_tick"):
        gnss_bp.set_attribute("sensor_tick", "0.2")  # 5 Hz
    gnss_sensor = world.spawn_actor(
        gnss_bp,
        carla.Transform(carla.Location(x=1.0, z=2.8)),
        attach_to=hero
    )

    # --------- CAMERA (istersen kapatabilirsin) ----------
    cam_bp = bp_lib.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", "640")
    cam_bp.set_attribute("image_size_y", "360")
    cam_bp.set_attribute("fov", "90")
    if cam_bp.has_attribute("sensor_tick"):
        cam_bp.set_attribute("sensor_tick", "0.05")  # 20 Hz
    cam_transform = carla.Transform(carla.Location(x=1.6, z=1.7))
    cam_sensor = world.spawn_actor(cam_bp, cam_transform, attach_to=hero)

    # --------- LiDAR ----------
    lidar_bp = bp_lib.find("sensor.lidar.ray_cast")
    lidar_bp.set_attribute("range", "50")
    lidar_bp.set_attribute("rotation_frequency", "10")      # 10 Hz
    lidar_bp.set_attribute("channels", "32")
    lidar_bp.set_attribute("points_per_second", "56000")
    lidar_bp.set_attribute("upper_fov", "10")
    lidar_bp.set_attribute("lower_fov", "-30")
    if lidar_bp.has_attribute("sensor_tick"):
        lidar_bp.set_attribute("sensor_tick", "0.1")        # 10 Hz
    lidar_tf = carla.Transform(carla.Location(x=0.0, z=1.8))
    lidar_sensor = world.spawn_actor(lidar_bp, lidar_tf, attach_to=hero)

    lock = threading.Lock()

    latest_imu = {"ax": 0.0, "ay": 0.0, "az": 0.0, "gx": 0.0, "gy": 0.0, "gz": 0.0, "compass": 0.0}
    latest_gnss = {"lat": 0.0, "lon": 0.0, "alt": 0.0}
    latest_cam = {"w": 0, "h": 0, "step": 0, "bytes": b""}

    # LiDAR: SADECE XYZ float32 -> 12 bytes/point
    latest_lidar = {"bytes": b"", "width": 0, "ok": False}

    imu_ready = [False]
    gnss_ready = [False]
    cam_ready = [False]
    lidar_ready = [False]

    def on_imu(data):
        with lock:
            latest_imu["ax"] = float(data.accelerometer.x)
            latest_imu["ay"] = float(data.accelerometer.y)
            latest_imu["az"] = float(data.accelerometer.z)
            latest_imu["gx"] = float(data.gyroscope.x)
            latest_imu["gy"] = float(data.gyroscope.y)
            latest_imu["gz"] = float(data.gyroscope.z)
            latest_imu["compass"] = float(data.compass)
            imu_ready[0] = True

    def on_gnss(data):
        with lock:
            latest_gnss["lat"] = float(data.latitude)
            latest_gnss["lon"] = float(data.longitude)
            latest_gnss["alt"] = float(data.altitude)
            gnss_ready[0] = True

    def on_cam(image):
        with lock:
            latest_cam["w"] = int(image.width)
            latest_cam["h"] = int(image.height)
            latest_cam["step"] = int(image.width * 4)   # BGRA
            latest_cam["bytes"] = bytes(image.raw_data)
            cam_ready[0] = True

    def on_lidar(meas):
        raw = bytes(meas.raw_data)
        blen = len(raw)
        if blen == 0:
            return

        # CARLA LiDAR raw_data burada XYZ float32 (12 bytes/point) olarak geliyor.
        if blen % 12 != 0:
            # bu durumda frame'i drop et
            # print("[LIDAR] drop: blen {} 12'nin kati degil".format(blen))
            return

        arr = np.frombuffer(raw, dtype=np.float32)
        if arr.size % 3 != 0:
            return

        pts = arr.reshape((-1, 3)).copy()  # copy -> writable
        pts[:, 1] *= 1.0  # CARLA y(right) -> ROS y(left)

        b = pts.astype(np.float32, copy=False).tobytes()
        with lock:
            latest_lidar["bytes"] = b
            latest_lidar["width"] = int(pts.shape[0])
            latest_lidar["ok"] = True
            lidar_ready[0] = True

    imu_sensor.listen(on_imu)
    gnss_sensor.listen(on_gnss)
    cam_sensor.listen(on_cam)
    lidar_sensor.listen(on_lidar)

    try:
        while True:
            t = hero.get_transform()
            loc = t.location
            rot = t.rotation

            v = hero.get_velocity()
            w = hero.get_angular_velocity()

            # POSE
            pose_msg = {
                "msg_type": "pose",
                "x": float(loc.x), "y": float(loc.y), "z": float(loc.z),
                "roll": float(rot.roll), "pitch": float(rot.pitch), "yaw": float(rot.yaw)
            }
            sock.sendall((json.dumps(pose_msg) + "\n").encode("utf-8"))

            # ODOM
            odom_msg = {
                "msg_type": "odom",
                "x": float(loc.x), "y": float(loc.y), "z": float(loc.z),
                "roll": float(rot.roll), "pitch": float(rot.pitch), "yaw": float(rot.yaw),
                "vx": float(v.x), "vy": float(v.y), "vz": float(v.z),
                "wx": float(w.x), "wy": float(w.y), "wz": float(w.z)
            }
            sock.sendall((json.dumps(odom_msg) + "\n").encode("utf-8"))

            with lock:
                # IMU
                if imu_ready[0]:
                    imu_msg = {
                        "msg_type": "imu",
                        "ax": latest_imu["ax"], "ay": latest_imu["ay"], "az": latest_imu["az"],
                        "gx": latest_imu["gx"], "gy": latest_imu["gy"], "gz": latest_imu["gz"],
                        "compass": latest_imu["compass"]
                    }
                    sock.sendall((json.dumps(imu_msg) + "\n").encode("utf-8"))

                # GNSS
                if gnss_ready[0]:
                    gnss_msg = {
                        "msg_type": "gnss",
                        "lat": latest_gnss["lat"],
                        "lon": latest_gnss["lon"],
                        "alt": latest_gnss["alt"]
                    }
                    sock.sendall((json.dumps(gnss_msg) + "\n").encode("utf-8"))

                # CAMERA (istersen kaldır)
                if cam_ready[0] and latest_cam["bytes"]:
                    b = latest_cam["bytes"]
                    cam_header = {
                        "msg_type": "camera",
                        "width": latest_cam["w"],
                        "height": latest_cam["h"],
                        "encoding": "bgra8",
                        "step": latest_cam["step"],
                        "data_len": len(b)
                    }
                    sock.sendall((json.dumps(cam_header) + "\n").encode("utf-8"))
                    sock.sendall(b)

                # LIDAR (XYZ only)
                if lidar_ready[0] and latest_lidar["ok"] and latest_lidar["bytes"]:
                    b = latest_lidar["bytes"]
                    w_pts = latest_lidar["width"]

                    lidar_header = {
                        "msg_type": "lidar",
                        "width": int(w_pts),
                        "height": 1,
                        "fields": 3,
                        "point_step": 12,
                        "data_len": len(b)
                    }
                    sock.sendall((json.dumps(lidar_header) + "\n").encode("utf-8"))
                    sock.sendall(b)

            time.sleep(MAIN_LOOP_DT)

    finally:
        for s in [imu_sensor, gnss_sensor, cam_sensor, lidar_sensor]:
            try:
                s.stop()
            except Exception:
                pass
        for s in [imu_sensor, gnss_sensor, cam_sensor, lidar_sensor]:
            try:
                s.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    main()
