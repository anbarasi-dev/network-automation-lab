# SONiC Architecture Deep Dive: Code-Level Flow of Configuring a VLAN

> **Goal of this note:** Trace exactly what happens inside SONiC, layer by layer, when an engineer runs a single CLI command to create a VLAN. This is meant to be readable by someone who is new to SONiC but already knows basic networking and Linux concepts.

## Why This Example Matters

SONiC (Software for Open Networking in the Cloud) is not one monolithic program. It is a collection of independent containers and daemons, written in **three different languages (Python, Go, C++/C)**, that talk to each other through a shared **Redis database** and **Linux kernel interfaces**. Understanding one config flow end-to-end is the fastest way to understand the whole architecture, because every other feature (ports, LAGs, routes, ACLs) follows the same pattern.

The example command used throughout this note:

```
config vlan add 100 6,27
```

This creates **VLAN 100** and adds ports **6 and 27** as members.

---

## 1. The Big Picture: One Diagram

```
[User CLI Input]
       │
       ▼  (Python — Click CLI, sends local REST request)
[REST Server]  (Go — Management Framework container)
       │
       ▼  (Go — Translib, writes over UNIX Domain Socket)
[CONFIG_DB]  (Redis — in-memory datastore, source of intent)
       │
       ▼  (C++ — VlanMgrd, subscribed via Redis Pub/Sub)
[Linux Kernel]  (Kernel space — provisioned via Netlink)
       │
       ▼  (C++ — VlanMgrd writes operational state)
[APPL_DB]  (Redis — application state datastore)
       │
       ▼  (C++ — Orchagent translates to hardware model)
[ASIC_DB]  (Redis — hardware-abstracted datastore)
       │
       ▼  (C++ — syncd, the synchronization daemon)
[SAI C-API]  (C/C++ — vendor's libsai.so dynamic library)
       │
       ▼
[Physical ASIC]  (programmed at line-rate)
```

**Key idea:** Every stage in this pipeline is a separate process. They don't call each other's functions directly — they **hand off state through a database** (mostly Redis) or a **kernel API (Netlink)**. This is what makes SONiC modular: you can swap the CLI, the REST server, or even the ASIC vendor without touching the rest of the pipeline.

---

## 2. The Databases You'll Keep Seeing

SONiC uses Redis as a message bus and state store, split into logical databases. For this VLAN example, three of them matter:

| Database    | Purpose                                                              | Who writes to it       | Who reads from it        |
|-------------|-----------------------------------------------------------------------|-------------------------|----------------------------|
| `CONFIG_DB` | Stores the **user's intent** — what the admin asked for               | Management framework (Go)| VlanMgrd (C++)             |
| `APPL_DB`   | Stores **application-level operational state** after kernel confirms  | VlanMgrd (C++)          | Orchagent (C++)            |
| `ASIC_DB`   | Stores a **hardware-neutral representation** ready for the ASIC       | Orchagent (C++)         | syncd (C++)                |

Think of it as a relay race: CONFIG_DB → APPL_DB → ASIC_DB, with a different daemon carrying the baton at each leg.

---

## Phase A — Command Input & Parsing (Python)

**Where:** CLI layer, written in Python.

1. The engineer types:
   ```
   config vlan add 100 6,27
   ```
2. SONiC's CLI is built on the **Click** library, wrapped inside a **Klish XML shell** (this is what gives you the familiar `sonic#` prompt with tab-completion and help text).
3. The CLI actioner script (`cli_client.py`) doesn't talk to Redis directly. Instead, it converts the command into a **RESTCONF-compliant JSON payload** that follows the OpenConfig YANG model:
   ```json
   {
     "openconfig-interfaces:config": {
       "name": "Vlan100"
     }
   }
   ```
4. **IPC used: local HTTPS.** The Python script sends this JSON as an HTTPS POST request to the REST Server running locally on port 443.

**Takeaway:** Even a CLI command in SONiC doesn't touch the database directly — it goes through the same REST API that a network automation tool (like Ansible or a custom script) would use. CLI and API are two doors into the same room.

---

## Phase B — Schema Validation & Intent Storage (Go)

**Where:** Management Framework container, written in Go.

1. The **REST Server** (Go) receives the HTTPS request and routes it internally to **Translib** (Translation Library — also Go).
2. Translib unmarshals (parses) the JSON into Go structures called **YGOT bindings** (YANG-Go Tools). This step **validates the request against the standard YANG schema** — catching invalid VLAN IDs, malformed names, etc. *before* anything is written to the database.
3. **IPC used: UNIX Domain Socket.** Once validated, Translib converts the high-level intent into a Redis key-value write and pushes it into `CONFIG_DB` over a local UNIX socket:
   ```
   HSET "VLAN|Vlan100" "vlanid" "100"
   ```

**Takeaway:** This is the boundary between "human/API intent" and "system state." Nothing below this line knows or cares that the request came from a CLI — from here on, it's just a row in Redis.

---

## Phase C — Kernel Mapping (C++ & Netlink)

**Where:** `swss` container, specifically the **VlanMgrd** daemon, written in C++.

1. **VlanMgrd** is a long-running daemon that **subscribes to the VLAN tables in `CONFIG_DB`** — it's always listening, not polling.
2. **IPC used: Redis Pub/Sub.** The moment `"VLAN|Vlan100"` is written, Redis's keyspace notification mechanism fires, and VlanMgrd wakes up to process the change.
3. **IPC used: Netlink socket.** VlanMgrd now needs to make this VLAN real *in the Linux kernel* (not just in Redis). It calls kernel networking functions over a Netlink socket — functionally equivalent to running:
   ```
   ip link add name Vlan100 type bridge
   ```
4. Once the kernel confirms the interface was created successfully, VlanMgrd writes the **operational** state into `APPL_DB`:
   ```
   HSET "VLAN_TABLE:Vlan100" "vlanid" "100"
   ```

**Takeaway:** This is the first point where the config becomes a *real* Linux network interface — useful for things like control-plane traffic (e.g., LACP, BGP) that use the kernel's networking stack. But the physical switch ASIC hasn't been touched yet — that happens in the next two phases.

---

## Phase D — State Translation & Orchestration (C++)

**Where:** `swss` container, the **Orchagent** daemon, written in C++.

1. **Orchagent** subscribes to `VLAN_TABLE` in `APPL_DB`.
2. **IPC used: Redis Pub/Sub.** Orchagent consumes the update and performs **logical orchestration** — for example, verifying which physical ports (6 and 27 in our example) should become members, checking neighbor/interface bindings, and resolving dependencies between features.
3. Orchagent then writes a **hardware-agnostic** representation of this state into `ASIC_DB`:
   ```
   HSET "ASIC_STATE:SAI_OBJECT_TYPE_VLAN:vlan_id_100" "vlan_id" "100"
   ```

**Takeaway:** Orchagent is the "brain" that decides *what* needs to happen on the hardware, but it deliberately knows nothing about *which vendor's chip* is underneath. That separation is the whole point of the next phase.

---

## Phase E — Hardware ASIC Synchronization (C++ & C)

**Where:** `syncd` container, plus the vendor's SAI driver library.

1. The **syncd** process (C++) subscribes directly to `ASIC_DB`.
2. **IPC used: Redis Pub/Sub.** syncd reads the hardware-neutral entry written by Orchagent.
3. **Hardware interface used: SAI C-API** (Switch Abstraction Interface). syncd maps the Redis entry to a standard C-language function call:
   ```c
   sai_vlan_api->create_vlan(&vlan_oid, switch_id, vlan_id, attr_count, attr_list);
   ```
4. This call executes **inside the vendor's dynamic driver library** (`libsai.so` — supplied by Broadcom, Mellanox/NVIDIA, Marvell, etc.), which translates it into vendor-specific SDK instructions.
5. The vendor SDK programs the **physical ASIC's L2 forwarding tables** at line-rate.

**Takeaway:** SAI is the contract that lets SONiC run on switches from different silicon vendors without changing a single line of Orchagent or syncd code. Only `libsai.so` changes per vendor — everything above it is common code.

---

## 3. End-to-End Summary Table

| Phase | Component      | Language | Input Source        | Output Destination | IPC / Interface Used     |
|-------|-----------------|----------|----------------------|----------------------|----------------------------|
| A     | CLI / cli_client.py | Python | User keyboard input  | REST Server           | Local HTTPS POST           |
| B     | REST Server + Translib | Go  | HTTPS JSON request   | CONFIG_DB              | UNIX Domain Socket         |
| C     | VlanMgrd         | C++      | CONFIG_DB change      | Linux Kernel, then APPL_DB | Redis Pub/Sub + Netlink |
| D     | Orchagent        | C++      | APPL_DB change        | ASIC_DB                | Redis Pub/Sub              |
| E     | syncd            | C++/C    | ASIC_DB change        | Physical ASIC           | Redis Pub/Sub + SAI C-API  |

---

## 4. Key Architectural Takeaways for Newcomers

- **No component calls another directly.** Every hop happens through either a Redis database (with Pub/Sub notifications) or a kernel socket (Netlink). This loose coupling is why SONiC containers can be restarted, upgraded, or replaced independently.
- **CONFIG_DB is intent, APPL_DB is confirmed application state, ASIC_DB is hardware-neutral state.** If you're debugging a VLAN that "isn't working," check these three databases in order — it tells you exactly how far the config actually propagated.
- **The kernel path (Phase C) and the ASIC path (Phase D–E) are parallel, not the same thing.** A VLAN can exist in the Linux kernel (useful for control-plane software) independently of whether it's been programmed into the ASIC's forwarding tables.
- **SAI is the vendor abstraction boundary.** Everything above `sai_vlan_api->create_vlan()` is common, open-source SONiC code. Everything below it (`libsai.so`) is vendor-proprietary.
- **Useful debug commands** that map to this flow:
  - `redis-cli -n 4 HGETALL "VLAN|Vlan100"` → inspect CONFIG_DB
  - `redis-cli -n 0 HGETALL "VLAN_TABLE:Vlan100"` → inspect APPL_DB
  - `redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_VLAN:*"` → inspect ASIC_DB
  - `ip link show Vlan100` → confirm kernel-side interface creation

---

*Notes compiled while studying SONiC architecture — part of a personal reference set for GitHub, adapted for a LinkedIn walkthrough post.*
