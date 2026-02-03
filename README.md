# CARLA 0.9.8 - ROS2 Humble TCP Bridge

Bu proje, **CARLA 0.9.8** simülatörü ile **ROS2 Humble** arasında hafif ve esnek bir köprü (bridge) kurar. CARLA 0.9.8'in eski Python sürümlerine (3.5/3.6) bağımlı olması ile ROS2 Humble'ın güncel Python (3.10) gereksinimi arasındaki uyumsuzluğu **TCP Socket** haberleşmesi ile çözer.

## 🏗 Mimari

Sistem iki farklı ortamda (environment) çalışan bileşenlerden oluşur ve TCP üzerinden JSON/Binary veri paketleri ile haberleşir:

1.  **CARLA Tarafı (Conda Env - Python 3.5):**
    *   Simülatörden verileri (Kamera, Lidar, GNSS, IMU, Odometry) toplar.
    *   TCP Client olarak ROS2 tarafına bağlanır ve verileri gönderir.
    *   TCP Server olarak ROS2'den gelen kontrol komutlarını dinler.
2.  **ROS2 Tarafı (ROS2 Humble Env - Python 3.10):**
    *   `carla_tcp_bridge` paketi (C++) TCP üzerinden gelen verileri alır ve ROS2 topic'lerine yayınlar.
    *   ROS2 üzerinden gelen sürüş komutlarını (Ackermann/Twist) TCP üzerinden CARLA tarafına iletir.

## 📂 Dosya Yapısı

*   `carla_bridge/`: CARLA tarafında çalışan Python scriptleri.
    *   `carla_telemetry_sender.py`: Sensör verilerini (Kamera, Lidar vb.) toplayıp ROS2'ye gönderir.
    *   `carla_control_server.py`: ROS2'den gelen kontrol komutlarını dinler ve araca uygular.
    *   `carla_pose_sender.py` / `carla_odom_sender.py`: Sadece konum ve odometri verisi gönderen hafif scriptler.
    *   `run_carla_stack.sh`: Tüm sistemi (Environment geçişlerini yöneterek) başlatan ana script.
    *   `stop_carla_stack.sh`: Tüm sistemi güvenli bir şekilde kapatan script.

## 🚀 Kurulum

### 1. Ön Gereksinimler
*   Ubuntu 22.04 (Önerilen)
*   CARLA 0.9.8 Simülatörü
*   ROS2 Humble
*   Miniconda veya Anaconda

### 2. CARLA Ortamının Hazırlanması
CARLA 0.9.8 için Python 3.5 tabanlı bir conda ortamı oluşturun:

```bash
conda create -n carla35 python=3.5
conda activate carla35
pip install numpy
# CARLA PythonAPI egg dosyasını yolunuza eklemeyi unutmayın (run scripti içinde otomatik yapılır)
```

### 3. ROS2 Workspace Kurulumu
Bu repodaki `carla_tcp_bridge` ROS2 paketini workspace'inize dahil edin ve derleyin:

```bash
cd ~/ros2_ws/src
# Bu repoyu klonlayın veya carla_tcp_bridge klasörünü buraya kopyalayın
cd ~/ros2_ws
colcon build --packages-select carla_tcp_bridge
source install/setup.bash
```

## 🎮 Kullanım

Sistemi başlatmak için tek bir script yeterlidir. Bu script otomatik olarak Conda ortamını aktif eder, ROS2 ortamını kaynak gösterir ve scriptleri sırasıyla çalıştırır.

### Başlatma

Terminalde `carla_bridge` klasörüne gidin:

```bash
cd carla_bridge
chmod +x run_carla_stack.sh
./run_carla_stack.sh
```

**Scriptin yaptığı işlemler:**
1.  Eski process'leri temizler.
2.  `spawn_hero_keepalive.py` ile haritada "hero" isminde bir araç oluşturur.
3.  `carla_control_server.py`'yi başlatır (Port 9001 dinlenir).
4.  Conda'dan çıkıp ROS2 ortamına geçer ve `bridge_node`'u başlatır.
5.  Tekrar Conda ortamına dönüp `carla_telemetry_sender.py`'yi başlatır.

### Durdurma

Sistemi kapatmak için `Ctrl+C` yapmak yerine aşağıdaki scripti kullanın, aksi halde arka planda asılı processler kalabilir:

```bash
./stop_carla_stack.sh
```

## ⚙️ Konfigürasyon

Varsayılan port ve IP ayarları scriptlerin başında tanımlıdır:

*   **Telemetry (Data)**: `127.0.0.1:9000` (CARLA -> ROS2)
*   **Control (Komut)**: `0.0.0.0:9001` (ROS2 -> CARLA)
*   **CARLA Bağlantısı**: `localhost:2000`

Bu ayarları değiştirmek için `carla_telemetry_sender.py` ve `carla_control_server.py` dosyalarındaki `TELEMETRY_HOST` ve `CONTROL_PORT` değişkenlerini düzenleyebilirsiniz.

## 🛠 Sorun Giderme

*   **"Hero/vehicle bulunamadı" hatası:** CARLA simülatörünün açık olduğundan ve haritada bir araç spawn olduğundan emin olun. `spawn_hero_keepalive.py` bu işi otomatik yapmaya çalışır.
*   **Bağlantı hataları:** Firewall'un 9000 ve 9001 portlarına izin verdiğinden emin olun.
*   **Loglar:** Tüm çıktı logları `~/carla_bridge/logs` klasöründe saklanır. Hata ayıklamak için `tail -f logs/telemetry.log` komutunu kullanabilirsiniz.
