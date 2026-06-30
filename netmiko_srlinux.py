from netmiko import ConnectHandler

device = {
    'device_type': 'nokia_srl',
    'host': '172.20.20.2',
    'username': 'admin',
    'password': 'NokiaSrl1!',
}

print("Connecting to SR Linux router...")
conn = ConnectHandler(**device)

print("\n--- Show Version ---")
print(conn.send_command('show version'))

print("\n--- Show Interfaces ---")
print(conn.send_command('show interface brief'))

print("\n--- Show Network Instance ---")
print(conn.send_command('show network-instance summary'))

conn.disconnect()
print("\nDisconnected successfully!")
