# Complete Setup Guide: Containerlab → SR Linux → Netmiko → NAPALM
**Platform:** Windows 11 + WSL2  
**Goal:** Network automation hands-on with Nokia SR Linux

---

## PHASE 1 — Install WSL-Containerlab Distro (Windows PowerShell)

### Step 1 — Check WSL version
```powershell
wsl --version
# WSL version must be 2.4.4 or higher
# If not, run: wsl --update
```

### Step 2 — Download WSL-Containerlab
Go to: https://github.com/srl-labs/wsl-containerlab/releases  
Download the latest `.wsl` file (e.g. `clab-0.76.1-1.0.wsl`)

### Step 3 — Install it
Double-click the `.wsl` file → it installs automatically.  
Open **"Containerlab"** from the Windows Start menu.  
When prompted, select **option 3 (bash)** as your shell.

### Step 4 — Disable Docker Desktop integration
Open Docker Desktop → Settings → Resources → WSL Integration  
→ Turn **OFF** for the Containerlab distro  
→ Click **Apply & Restart**

### Step 5 — Verify Containerlab and Docker
```bash
containerlab version   # Should show version 0.76.x
docker ps              # Should show empty table (no error)
```

---

## PHASE 2 — Deploy SR Linux Lab

### Step 6 — Pull the SR Linux image
```bash
docker pull ghcr.io/nokia/srlinux
# No login required — fully public image
# Takes 2-3 mins on first pull
```

### Step 7 — Create lab directory and topology file
```bash
cd ~
mkdir clab-lab && cd clab-lab

cat > lab.yml << 'EOF'
name: mylab
topology:
  nodes:
    router1:
      kind: nokia_srlinux
      image: ghcr.io/nokia/srlinux
EOF
```

### Step 8 — Deploy the lab
```bash
sudo containerlab deploy -t lab.yml
# Wait ~60 seconds for SR Linux to fully boot
```

### Step 9 — Check the lab and note the IP
```bash
sudo containerlab inspect -t lab.yml
# Note the IPv4 address of router1 — typically 172.20.20.2
```

### Step 10 — Verify SSH access
```bash
ssh admin@172.20.20.2
# Password: NokiaSrl1!
# Type 'yes' when asked about fingerprint

# Once inside, verify:
show version

# Exit when done
exit
```

---

## PHASE 3 — Python Environment Setup

### Step 11 — Install Python and pip
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv
```

### Step 12 — Create virtual environment
```bash
cd ~
python3 -m venv venv
source venv/bin/activate
# Your prompt should now show (venv)
```

> **Note:** Every time you open a new Containerlab WSL terminal, activate the venv with:
> ```bash
> source ~/venv/bin/activate
> ```

---

## PHASE 4 — Netmiko

### Step 13 — Install Netmiko
```bash
pip install netmiko
```

### Step 14 — Create Netmiko script
```bash
cat > ~/netmiko_srlinux.py << 'EOF'
from netmiko import ConnectHandler

device = {
    'device_type': 'nokia_srl',
    'host': '172.20.20.2',
    'username': 'admin',
    'password': 'NokiaSrl1!',
}

print("Connecting to SR Linux via Netmiko...")
conn = ConnectHandler(**device)

print("\n--- Show Version ---")
print(conn.send_command('show version'))

print("\n--- Show Interfaces ---")
print(conn.send_command('show interface brief'))

print("\n--- Show Network Instance ---")
print(conn.send_command('show network-instance summary'))

conn.disconnect()
print("\nDisconnected successfully!")
EOF
```

### Step 15 — Run Netmiko script
```bash
python3 ~/netmiko_srlinux.py
```

---

## PHASE 5 — NAPALM

### Step 16 — Install NAPALM and SR Linux driver
```bash
pip install napalm napalm-srl
```

> **Why two packages?**  
> `napalm` is the core library. `napalm-srl` is a community plugin — Nokia SR Linux  
> is not built into NAPALM by default, so it needs a separate driver.

### Step 17 — Create NAPALM script
```bash
cat > ~/napalm_srlinux.py << 'EOF'
from napalm import get_network_driver

driver = get_network_driver('srl')

device = driver(
    hostname='172.20.20.2',
    username='admin',
    password='NokiaSrl1!',
    optional_args={
        'insecure': True,   # Skip TLS cert validation (lab only)
        'port': 57400,      # gRPC port used by SR Linux
    }
)

print("Connecting via NAPALM...")
device.open()

print("\n--- Facts ---")
facts = device.get_facts()
for k, v in facts.items():
    print(f"{k}: {v}")

print("\n--- Interfaces ---")
interfaces = device.get_interfaces()
for name, data in interfaces.items():
    print(f"{name}: up={data['is_up']}, speed={data['speed']}")

device.close()
print("\nDone!")
EOF
```

### Step 18 — Run NAPALM script
```bash
python3 ~/napalm_srlinux.py
```

---

## Lab Management Commands

```bash
# Stop the lab (keeps config)
sudo containerlab destroy -t ~/clab-lab/lab.yml

# Start it again
sudo containerlab deploy -t ~/clab-lab/lab.yml

# List running labs
sudo containerlab inspect --all
```

---

## Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `Link not found` | Wrong WSL distro | Use Containerlab WSL distro, not default Ubuntu |
| `docker: command not found` | Docker Desktop integration ON | Disable it in Docker Desktop → WSL Integration |
| `pip: command not found` | Python not installed | Run Phase 3 steps |
| `Cannot import srl` | Missing driver | `pip install napalm-srl` |
| `TLS handshake failed` | Missing insecure flag | Add `'insecure': True` to `optional_args` |
| SR Linux not responding | Still booting | Wait 60 seconds after deploy |

---

## Key Credentials

| Item | Value |
|---|---|
| SR Linux IP | `172.20.20.2` |
| Username | `admin` |
| Password | `NokiaSrl1!` |
| gRPC Port (NAPALM) | `57400` |
| SSH Port (Netmiko) | `22` |
