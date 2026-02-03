#!/usr/bin/env bash
set +e

echo "[STOP] CARLA + ROS2 stack durduruluyor..."

# ---- CARLA (conda python) ----
pkill -f spawn_hero_keepalive.py
pkill -f carla_control_server.py
pkill -f carla_telemetry_sender.py

# ---- ROS2 bridge ----
pkill -f "ros2 run carla_tcp_bridge bridge_node"

sleep 1

echo "[STOP] Kalan ilgili process'ler kontrol ediliyor..."

# Güvenlik: carla_bridge klasöründen çalışan python'lar
pkill -f "$HOME/carla_bridge/.*\.py"

echo "[STOP] Tamamlandı."

source ~/.bashrc

