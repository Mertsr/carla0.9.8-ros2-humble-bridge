#!/usr/bin/env python3
import time
import random
import carla

CARLA_HOST = "localhost"
CARLA_PORT = 2000

def main():
    client = carla.Client(CARLA_HOST, CARLA_PORT)
    client.set_timeout(5.0)
    world = client.get_world()
    m = world.get_map()

    # Zaten hero varsa tekrar spawn etme
    for a in world.get_actors():
        if "vehicle" in a.type_id and a.attributes.get("role_name") == "hero":
            print("Zaten hero var, id:", a.id)
            while True:
                time.sleep(1.0)
            return

    bp_lib = world.get_blueprint_library()
    bp = bp_lib.find("vehicle.tesla.model3")
    bp.set_attribute("role_name", "hero")

    spawns = m.get_spawn_points()
    #sp = random.choice(spawns)
    
    sp = carla.Transform(
        carla.Location(x=0, y=20, z=0.5),
        carla.Rotation(yaw=0.0)
    )

    
    veh = world.try_spawn_actor(bp, sp)
    if veh is None:
        print("Spawn basarisiz. Tekrar dene.")
        return

    print("Hero spawn OK. id:", veh.id)

    # KEEP ALIVE: hiçbir kontrol basmıyoruz
    while True:
        time.sleep(1.0)

if __name__ == "__main__":
    main()
