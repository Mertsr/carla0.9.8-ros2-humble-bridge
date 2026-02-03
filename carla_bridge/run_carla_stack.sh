#!/usr/bin/env bash
set -e

########################################
# 1️⃣ CARLA / CONDA ORTAMI
########################################
CONDA_BASE="$HOME/miniconda3"
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate carla35

pkill -f "/opt/ros/humble/bin/ros2 run carla_tcp_bridge bridge_node" 2>/dev/null || true
pkill -f "install/carla_tcp_bridge/lib/carla_tcp_bridge/bridge_node" 2>/dev/null || true
pkill -f "carla_telemetry_sender.py" 2>/dev/null || true
pkill -f "carla_control_server.py" 2>/dev/null || true
pkill -f "spawn_hero_keepalive.py" 2>/dev/null || true


EGG="/home/mertsrc/carla098/PythonAPI/carla/dist/carla-0.9.8-py3.5-linux-x86_64.egg"
export PYTHONPATH="$EGG"

LOGDIR="$HOME/carla_bridge/logs"
mkdir -p "$LOGDIR"

echo "[1/5] spawn_hero_keepalive"
python3 "$HOME/carla_bridge/spawn_hero_keepalive.py" > "$LOGDIR/spawn.log" 2>&1 &
sleep 1

echo "[2/5] carla_control_server"
python3 "$HOME/carla_bridge/carla_control_server.py" > "$LOGDIR/control.log" 2>&1 &
sleep 2   # ⬅️ ROS2 bundan sonra bağlanacak

########################################
# 2️⃣ ROS2 ORTAMI (conda'dan ÇIK!)
########################################
echo "[3/5] ROS2 bridge_node"

conda deactivate
source "$HOME/ros2_ws/install/setup.bash"

ros2 run carla_tcp_bridge bridge_node > "$LOGDIR/ros2_bridge.log" 2>&1 &
sleep 2   # ⬅️ CARLA sender'lar bundan sonra

########################################
# 3️⃣ TEKRAR CARLA / CONDA
########################################
conda activate carla35
export PYTHONPATH="$EGG"

echo "[4/5] carla_telemetry_sender"
wpython3 "$HOME/carla_bridge/carla_telemetry_sender.py" > "$LOGDIR/telemetry.log" 2>&1 &

echo "[5/5] DONE"
echo "CARLA + ROS2 stack ayakta 🚀"
echo "Loglar: $LOGDIR"

