# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## NEFICS Overview

NEFICS (Network Emulation Framework for Industrial Control Systems) is a Mininet-based framework for simulating high-fidelity industrial control system devices. It creates virtual networks with emulated PLCs, RTUs, HMIs, and other ICS components.

## Key Commands

### Running Scenarios
```bash
# Run a scenario
sudo python3 -m run conf/[scenario].json

# Common scenarios
sudo python3 -m run conf/honeypot_watertank.json    # Water tank control system
sudo python3 -m run conf/simple_powergrid.json      # Power grid simulation
sudo python3 -m run conf/honeypot_warehouse.json    # Warehouse automation
```

### Running Individual Devices
```bash
# Using config file
python3 -m nefics.launcher -c config_file.json

# Using command line string
python3 -m nefics.launcher -C '{"module":"honeypot","device":"HoneyDevice","handler":"HoneyHandler","guid":1,"in":[],"out":[],"parameters":{"honeyconf":"conf/honeypot_watertank.conf"}}'
```

### Mininet Commands
```bash
# Clean up Mininet
sudo mn -c

# Inside Mininet CLI
mininet> [node] ps aux | grep [process]    # Check processes in a node
mininet> [node] ifconfig                   # Check network interfaces
mininet> [node] ping [ip]                  # Test connectivity
mininet> xterm [node]                      # Open terminal for node
```

### Dependencies
```bash
# Install requirements
pip3 install -r Requirements.txt

# Additional system requirements
sudo apt-get install honeyd  # For honeypot scenarios
```

## Architecture

### Core Components

1. **run.py**: Main entry point that:
   - Parses JSON configuration files
   - Creates Mininet virtual network topology
   - Launches device processes in network namespaces
   - Falls back to background mode if xterm fails

2. **nefics.launcher**: Device process launcher that:
   - Imports specified device modules
   - Instantiates device and handler classes
   - Manages protocol listeners and device lifecycle

3. **Device Architecture**:
   ```
   DeviceBase (Thread) → Specific Device (e.g., WaterTankPLC)
   DeviceHandler → Specific Handler (e.g., PLCHandler)
   ProtocolListener → HTTP, Modbus, IEC104, etc.
   ```

### Module Structure

- **nefics/modules/**: Device implementations
  - `devicebase.py`: Base classes for all devices
  - `honeypot.py`: Honeypot devices and PLC emulations
  - `simplepowergrid.py`: Power grid RTU devices
  - `swat.py`: Water treatment plant devices

- **nefics/protos/**: Protocol implementations
  - `http.py`: HTTP server for HMI/SCADA interfaces
  - `modbus.py`: Modbus TCP/RTU protocol
  - `iec10x/`: IEC 60870-5-101/104 protocols
  - `simproto.py`: Inter-device simulation protocol

### Configuration Schema

```json
{
    "switches": [{"name": "s1", "dpid": 1}],
    "devices": [{
        "name": "device_name",
        "interfaces": [{
            "name": "eth0",
            "ip": "10.0.0.1/24",
            "switch": "s1"
        }],
        "launcher": {
            "module": "module_name",
            "device": "DeviceClass",
            "handler": "HandlerClass",
            "guid": 1,
            "in": [],
            "out": [],
            "parameters": {}
        },
        "routes": [["default", "10.0.0.254"]]
    }],
    "localiface": {
        "switch": "s1",
        "iface": "eth0"
    }
}
```

## Common Issues and Solutions

### xterm Windows Not Opening
- The framework tries to open xterm windows for each device but falls back to background mode
- Check DISPLAY environment variable: `echo $DISPLAY`
- Run without xterm: `sudo DISPLAY= python3 -m run conf/[scenario].json`

### honeyd Not Starting
- Ensure honeyd is installed: `which honeyd`
- Check fingerprint file exists: `conf/honeypot_fingerprints.txt`
- Verify network interfaces in honeypot configuration

### Launcher Import Errors
- Ensure scapy is installed system-wide: `sudo pip3 install scapy`
- Check Python path includes NEFICS directory

### Device Initialization Errors
- HoneyDevice/PLCDevice: Ensure kwargs are properly popped before passing to parent
- Thread initialization: Use keyword arguments for parent class initialization

## Watertank Scenario Specifics

The watertank scenario emulates:
- **allen1756**: Allen-Bradley PLC (10.0.0.10) running WaterTankPLC
- **honeypot**: Honeyd instance for network deception
- **hmi**: Human-Machine Interface node
- **scanner**: Network scanning node

Key parameters:
- `phys_ip`: IP address of Factory I/O simulation (Windows host)
- `set_point`: Water level set point (0-3 meters)
- Modbus registers: Tank level (IR 0x0001), Valve controls (HR 0x0000-0x0001)

## Recent Fixes and Session Notes (July 29, 2025)

### Fixed Issues
1. **HoneyDevice Initialization**: Fixed `DeviceBase.__init__()` missing guid error by using keyword arguments
2. **HoneyHandler Initialization**: Fixed missing device parameter by passing `device=device`
3. **honeyd Integration**: Added automatic fingerprint file loading with `-p` option in honeypot.py
4. **Thread Initialization**: Fixed kwargs passing issue by popping device-specific parameters before calling super()
5. **xterm Execution**: Added fallback mechanism when xterm fails to open

### Key Code Changes
- `nefics/modules/honeypot.py`: 
  - HoneyDevice now pops 'honeyconf' before passing kwargs to parent
  - HoneyHandler uses keyword argument for device parameter
  - Added fingerprint file auto-loading in _respawn method
- `run.py`: Added try-except for xterm with automatic fallback to background mode
- `conf/honeypot_watertank.json`: Updated phys_ip and network interface settings

### Working Configuration
- honeyd must be installed system-wide: `/usr/bin/honeyd`
- scapy must be installed system-wide: `sudo pip3 install scapy`
- Network topology: honeypot (192.168.0.x and 10.0.0.250), allen1756 (10.0.0.10), hmi (10.0.0.5)
- honeypot_watertank.conf: bind address should match network topology

### Git Repository
- Fork: https://github.com/soledo/NEFICS
- Original: https://github.com/Cyphysecurity/NEFICS
- Recent commit: "Fix watertank scenario launcher and honeyd integration"