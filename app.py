# app.py
from flask import Flask, jsonify, render_template, send_from_directory
import json
import os
from datetime import datetime
from netmiko import ConnectHandler
import sys

app = Flask(__name__)

# Your existing router monitoring code
def get_interfaces(device):
    command = 'show ip interface brief'
    output = device.send_command(command)
    interfaces = []
    for line in output.splitlines()[1:]:  
        parts = line.split()
        if len(parts) >= 5:
            interface_data = {
                'interface': parts[0],
                'ip_address': parts[1],
                'status': parts[3],
                'protocol': parts[4]
            }
            interfaces.append(interface_data)
    return interfaces

def get_uptime(device):
    command = 'show version'
    output = device.send_command(command)
    for line in output.splitlines():
        if "uptime" in line.lower():
            return line.strip()
    return "Uptime info not found"

def get_memory_usage(device):
    command = 'show memory statistics'
    output = device.send_command(command)
    memory_info = {}
    for line in output.splitlines():
        if "Free" in line:
            memory_info["Free Memory"] = line.split()[0]
        elif "Used" in line:
            memory_info["Used Memory"] = line.split()[0]
    return memory_info

def get_logs(device):
    command = 'show logging'
    output = device.send_command(command)
    return output

def get_ssh_info(device):
    command = 'show ip ssh'
    output = device.send_command(command)
    return output

def collect_network_data(routers):
    output_data = {}
    for router in routers:
        try:
            with ConnectHandler(
                device_type=router['device_type'],
                ip=router['host'],
                username=router['username'],
                password=router['password']
            ) as device:
                interfaces_info = get_interfaces(device)
                uptime_info = get_uptime(device)
                memory_info = get_memory_usage(device)
                logs_info = get_logs(device)
                ssh_info = get_ssh_info(device)

                output_data[router['host']] = {
                    'device_info': {
                        'host': router['host'],
                        'platform': router['device_type'],
                        'uptime': uptime_info,
                        'memory_usage': memory_info
                    },
                    'interfaces_info': interfaces_info,
                    'logs_info': logs_info,
                    'ssh_info': ssh_info
                }
        except Exception as e:
            output_data[router['host']] = {
                'error': f"Failed to connect: {str(e)}"
            }
    
    return output_data

# API Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/network/info')
def get_network_info():
    try:
        # Import routers configuration
        sys.path.append(os.path.join(os.path.dirname(__file__), 'inventory'))
        import routers # type: ignore
        
        # Collect network data
        data = collect_network_data(routers.routers)
        
        # Save to file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"network_info_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        
        return jsonify({
            "status": "success",
            "data": data,
            "filename": filename
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/network/history')
def get_history():
    files = [f for f in os.listdir('.') if f.startswith('network_info_') and f.endswith('.json')]
    files.sort(reverse=True)
    return jsonify(files)

@app.route('/api/network/file/<filename>')
def get_file(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)