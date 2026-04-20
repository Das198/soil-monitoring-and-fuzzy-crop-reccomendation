# 🏗️ Architecture - Sistem Monitoring Tanah

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MAIN ENTRY POINT                               │
│                          (main.py)                                      │
│              SoilMonitoringSystem Class                                 │
└────────┬─────────────┬────────────────────────────┬────────────────────┘
         │             │                            │
         ▼             ▼                            ▼
    ┌────────────┐ ┌──────────────┐          ┌─────────────┐
    │  ModbosTCP │ │  SensorData  │          │NodeREDTCP   │
    │ Connection │ │  Processor   │          │Connection   │
    └────────────┘ └──────────────┘          └─────────────┘
         │             │                            │
         └─────────────┴────────────────────────────┘
                       │
                 ┌─────▼──────┐
                 │ Data Flow  │
                 │  Pipeline  │
                 └────────────┘
```

## Data Flow

```
1. READ PHASE
   Modbus Gateway (10.10.100.254:8899)
   └─> Slave ID 1, 2, 3
       └─> Read Registers [0-7]
           └─> Raw Values: [50, 25, 2, 6.8, 100, 30, 100, 1]

2. PROCESS PHASE
   SensorData.process_registers()
   └─> Apply Mapping & Scaling
       ├─> kelembapan_tanah = 50 / 10.0 = 5.0
       ├─> suhu = 25 / 10.0 = 2.5
       └─> ... (7 parameters total)

3. SEND PHASE
   NodeREDSender.send_data()
   └─> Format JSON
       └─> Send via TCP to 127.0.0.1:5020
           └─> Node-RED receives JSON payload

4. OPTIONAL PHASES
   ├─> FuzzyLogic.evaluate() → Health Score
   ├─> DatabaseHandler.save_sensor_data() → MySQL
   └─> Logger → logs/monitoring.log
```

## Module Dependencies

```
main.py (Main Entry Point)
│
├─► src/config.py
│   └─► Configuration Constants
│
├─► src/core/modbus_handler.py
│   └─► pyModbusTCP library
│
├─► src/core/sensor_data.py
│   └─► Configuration (REGISTER_MAP, SCALED_PARAMETERS)
│
├─► src/core/node_red_sender.py
│   └─► socket library
│
├─► src/utils/logger.py
│   └─► logging library
│
└─► (Optional) Multiple features can use:
    ├─► src/calibration/calibrator.py
    ├─► src/fuzzy/fuzzy_logic.py (requires scikit-fuzzy, numpy)
    └─► src/db/database.py (requires mysql-connector-python)
```

## Class Hierarchy

```
SoilMonitoringSystem
├── modbus: ModbusHandler
│   ├── client: ModbusClient (pyModbusTCP)
│   ├── connect() → bool
│   ├── read_registers(unit_id, start, count) → List[int]
│   └── write_register(unit_id, address, value) → bool
│
├── sensor_processor: SensorData
│   ├── register_map: Dict[name: str, index: int]
│   ├── process_registers(raw_data) → Dict[str, float]
│   ├── format_output(data, unit_id, timestamp) → Dict
│   └── get_readable_output(data) → str
│
└── node_red: NodeREDSender
    ├── socket: socket.socket
    ├── connect() → bool
    ├── send_data(sensor_data, slave_id, timestamp) → bool
    └── send_batch(data_list) → int

PHCalibrator (Kalibrasi)
├── modbus: ModbusHandler
├── calibrate_single_point(...) → bool
└── calibrate_multi_point(...) → Dict[str, bool]

SoilFuzzyEvaluator (Fuzzy Logic)
├── ph, temp, moist, n, p, k, sal: Antecedents
├── health: Consequent
├── evaluate(sensor_data) → Dict
└── check_crop_compatibility(...) → Dict

DatabaseHandler (Database)
├── connection: mysql.connector.MySQLConnection
├── save_sensor_data(...) → bool
├── get_recent_data(...) → List[Dict]
└── create_tables() → bool
```

## Configuration Flow

```
src/config.py
├── MODBUS_*              → ModbusHandler
├── REGISTER_*            → SensorData
├── NODE_RED_*            → NodeREDSender
├── PH_*                  → PHCalibrator
├── CROP_REQUIREMENTS     → SoilFuzzyEvaluator
├── DB_*                  → DatabaseHandler
└── LOG_*                 → Logger
```

## Execution Flow (Main Loop)

```
main.py
  │
  ├─ SoilMonitoringSystem().__init__()
  │  ├─ ModbusHandler created
  │  ├─ SensorData created
  │  └─ NodeREDSender created
  │
  ├─ system.start()
  │  ├─ modbus.connect() ────────────►  [Modbus Gateway]
  │  └─ node_red.connect() ──────────►  [Node-RED on 127.0.0.1:5020]
  │
  ├─ system.run() (Main Loop)
  │  └─ for each cycle:
  │        │
  │        ├─ timestamp = now()
  │        │
  │        └─ for each slave_id in MODBUS_SLAVE_IDS:
  │              │
  │              ├─ modbus.read_registers(unit_id, 0, 8)
  │              │  └─► raw_registers = [50, 25, 2, ...]
  │              │
  │              ├─ sensor_data = processor.process_registers(raw_registers)
  │              │  └─► sensor_data = {kelembapan_tanah: 5.0, suhu: 2.5, ...}
  │              │
  │              ├─ print readable output
  │              │
  │              ├─ node_red.send_data(sensor_data, unit_id, timestamp)
  │              │  └─► JSON sent to Node-RED
  │              │
  │              └─ time.sleep(INTER_SLAVE_DELAY)
  │
  │        └─ time.sleep(INTER_CYCLE_DELAY)
  │
  └─ system.stop()
     ├─ modbus.disconnect()
     └─ node_red.disconnect()
```

## Error Handling

```
ModbusHandler
├─ Connection fails → Log error, return False
├─ Read fails → Check if open, reconnect, return None
└─ Write fails → Log error, return False

SensorData
├─ Invalid data length → Log warning, return None
├─ Index out of range → Log warning, skip parameter
└─ Process error → Log error, return None

NodeREDSender
├─ Connect fails → Log error, return False
├─ Send fails → Set is_connected=False, return False
└─ Socket error → Catch and handle gracefully

Main Loop
├─ KeyboardInterrupt → Graceful shutdown
├─ Read error → Log, sleep 1s, continue loop
└─ Send error → Log warning, still continue reading

PHCalibrator
├─ Write fails → Log error, return False
└─ Multi-point fails → Ask user to continue or abort

SoilFuzzyEvaluator
├─ Process error → Log error, return {health_score: None}
└─ Invalid crop name → Log warning, return {}

DatabaseHandler
├─ Connection error → Log error, return False
├─ Save error → Log error, return False
└─ Query error → Catch and handle, return None
```

## Scalability Considerations

### Horizontal Scaling
```
Multiple Sensors (Slave IDs)
└─ MODBUS_SLAVE_IDS = [1, 2, 3, 4, ...]
   └─ System reads from all slaves in one cycle
   └─ Each slave data sent to Node-RED separately

Multiple Monitoring Instances
└─ Can run multiple main.py on different machines
└─ Each monitoring different set of sensors
└─ All send to same Node-RED for centralized dashboard
```

### Vertical Scaling
```
Database Caching
└─ Batch insert sensor data every N cycles
└─ Reduces DB load

Async Operations (Future)
└─ Use asyncio for concurrent reads
└─ Parallel Modbus reads from multiple slaves
└─ Non-blocking Node-RED sends
```

## Security Considerations

```
Current Implementation (Development Stage)
├─ TCP connections without encryption
├─ Modbus without authentication
└─ Database password in plaintext

Production Improvements
├─ Use modbus-tcp with encryption (TLS)
├─ API key authentication for Node-RED
├─ Database credentials in environment variables
└─ SSL/TLS for all connections
```

## Performance Metrics

```
Typical Cycle Time (Single Slave)
├─ Modbus read: ~100-200ms
├─ Data processing: ~5-10ms
├─ JSON formatting: ~5ms
├─ TCP send to Node-RED: ~20-50ms
└─ Total per slave: ~150-260ms

System with 2 Slaves
├─ Total read time per cycle: ~200-300ms (with 100ms delay)
├─ Data rate: ~1 cycle every 2-3 seconds
├─ Data points per minute: ~20-30 per sensor

Data Volume (per sensor)
├─ 8 values per reading
├─ 1 cycle every 3 seconds
└─ ~960 data points per sensor per hour
```

## Extension Points

```
New Features Can Be Added Via:
├─ Custom rules in SoilFuzzyEvaluator
├─ New handlers in ModbusHandler (for different registers)
├─ New parameters in config.py
├─ New output destinations (e.g., InfluxDB, Kafka)
├─ Alert system based on health score
└─ Web dashboard integrations
```

---

## Deployment Architecture

```
┌──────────────────────────────────┐
│   Local Machine (Monitoring)     │
├──────────────────────────────────┤
│  main.py + src/                  │
├──────────────────────────────────┘
│       │
├───────┼────────────────────┬──────────────────┐
│       │                    │                  │
▼       ▼                    ▼                  ▼
[Modbus Gateway]    [Node-RED Server]    [MySQL Database]
10.10.100.254:8899  127.0.0.1:5020      localhost:3306
│                   │                    │
├─► Sensor 1        ├─► Dashboard        ├─► Data Storage
├─► Sensor 2        └─► UI               └─► Analytics
└─► Sensor 3
```

---

**Architecture Version:** 1.0  
**Last Updated:** 2026-04-15
