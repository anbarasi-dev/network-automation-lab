# Network Automation Lab — Containerlab + Netmiko + NAPALM

A hands-on network automation lab running entirely on a local Windows 11 + WSL2 machine using Docker — no physical hardware, no vendor account, no licensing required.

---

## 🧰 Stack

| Tool | Purpose |
|---|---|
| [Containerlab](https://containerlab.dev) | Spin up network topologies using Docker |
| [Nokia SR Linux](https://learn.srlinux.dev) | Free, open NOS running as a container |
| [Netmiko](https://github.com/ktbyers/netmiko) | SSH-based device interaction |
| [NAPALM](https://napalm.readthedocs.io) | Vendor-neutral network automation |
| [napalm-srl](https://github.com/napalm-automation-community/napalm-srl) | NAPALM community driver for SR Linux |

---

## 🖥️ Environment

- **OS:** Windows 11 with WSL2
- **Containerlab:** Dedicated WSL distro (see setup guide)
- **Python:** 3.11 with virtual environment

---

## 📁 Repository Structure

```
network-automation-lab/
│
├── lab.yml                      # Containerlab topology file
├── netmiko_srlinux.py           # Netmiko connection script
├── napalm_srlinux.py            # NAPALM connection script
├── containerlab_napalm_setup.md # Complete step-by-step setup guide
└── README.md                    # This file
```

---

## 🚀 Quick Start

### Prerequisites
- Windows 11 with WSL2 (version 2.4.4+)
- Docker Desktop installed
- Containerlab WSL distro installed (see setup guide)

### 1 — Clone this repo (inside Containerlab WSL terminal)
```bash
git clone https://github.com/anbarasi-dev/network-automation-lab.git
cd network-automation-lab
```

### 2 — Pull SR Linux image
```bash
docker pull ghcr.io/nokia/srlinux
```

### 3 — Deploy the lab
```bash
sudo containerlab deploy -t lab.yml
```

### 4 — Set up Python environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install netmiko napalm napalm-srl
```

### 5 — Run Netmiko script
```bash
python3 netmiko_srlinux.py
```

### 6 — Run NAPALM script
```bash
python3 napalm_srlinux.py
```

---

## 📡 Lab Details

| Item | Value |
|---|---|
| SR Linux IP | `172.20.20.2` |
| Username | `admin` |
| Password | `NokiaSrl1!` |
| SSH Port (Netmiko) | `22` |
| gRPC Port (NAPALM) | `57400` |

---

## 🔧 Lab Management

```bash
# Stop the lab
sudo containerlab destroy -t lab.yml

# Start the lab again
sudo containerlab deploy -t lab.yml

# List all running labs
sudo containerlab inspect --all
```

---

## 📖 Full Setup Guide

See [containerlab_napalm_setup.md](./containerlab_napalm_setup.md) for the complete step-by-step guide covering every phase from installation to working scripts.

---

## 🗺️ Roadmap

This repo will grow as I progress through my network automation learning journey:

- [x] Containerlab + SR Linux setup
- [x] Netmiko — SSH-based automation
- [x] NAPALM — vendor-neutral automation
- [ ] Nornir — Python-based automation at scale
- [ ] Ansible — YAML playbook automation
- [ ] Paramiko — low-level SSH
- [ ] gNMI / OpenConfig — model-driven telemetry
- [ ] SONiC NOS — open-source network OS

---

## 👩‍💻 About

Experienced Technical Manager with 15+ years of expertise in software development within the networking industry, leading teams in the design, development, and delivery of scalable, carrier-grade networking solutions. Committed to continuous professional growth, I am actively enhancing my skills in Python, network automation, Linux, containerized networking, and AI-driven engineering practices. This repository showcases my hands-on learning journey through practical projects, automation frameworks, and technology explorations, demonstrating a proactive approach to adopting modern software engineering and network automation methodologies.

Connect with me on [LinkedIn] (https://www.linkedin.com/in/anbarasi-gnanaprakasam-26b95222)

---

## 📜 License

MIT License — free to use, modify, and share.
