from napalm import get_network_driver

driver = get_network_driver('srl')

device = driver(
    hostname='172.20.20.2',
    username='admin',
    password='NokiaSrl1!',
    optional_args={
        'insecure': True,
        'port': 57400,
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
