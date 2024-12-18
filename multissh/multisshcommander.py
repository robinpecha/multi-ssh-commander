from flask import Flask, render_template, request, Response
import paramiko
import logging
import time
import json
from queue import Queue
import os

# Initialize Flask app
app = Flask(__name__)

# Initialize queue for results
results_queue = Queue()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('static/log.txt'),
        logging.StreamHandler()
    ]
)

# Ensure .ssh directory exists
ssh_dir = os.path.expanduser('~/.ssh')
known_hosts_path = os.path.join(ssh_dir, 'known_hosts')
if not os.path.exists(ssh_dir):
    os.makedirs(ssh_dir, mode=0o700)

# Default values for the form
default_values = {
    'username': 'admin',
    'password': '',
    'port': 22,
    'command': '/system/identity/print',
    'ips': '',
    'timeout': 3
}

@app.route('/stream')
def stream():
    def generate():
        while True:
            if not results_queue.empty():
                result = results_queue.get()
                yield f"data: {json.dumps(result)}\n\n"
    return Response(generate(), mimetype='text/event-stream')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        form_data = {
            'username': request.form.get('username'),
            'password': request.form.get('password'),
            'port': int(request.form.get('port')),
            'command': request.form.get('command'),
            'ips': request.form.get('ips'),
            'timeout': int(request.form.get('timeout', default_values['timeout']))
        }

        def process_ssh(ip):
            logging.info("")  # Log an empty line before each connection
            logging.info(f"Connecting to {ip}...")
            client = paramiko.SSHClient()
            
            # Load known hosts if file exists
            if os.path.exists(known_hosts_path):
                client.load_host_keys(known_hosts_path)
            
            # Still use RejectPolicy but we'll handle key verification manually
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
            
            start_time = time.time()
            try:
                # Get remote server's key
                transport = paramiko.Transport((ip, form_data['port']))
                transport.start_client()
                remote_key = transport.get_remote_server_key()
                
                # Save the key
                client._host_keys.add(ip, remote_key.get_name(), remote_key)
                
                # Save to known_hosts file
                client.save_host_keys(known_hosts_path)
                
                transport.close()
                
                # Now connect with verified key
                client.connect(
                    ip,
                    username=form_data['username'],
                    password=form_data['password'],
                    port=form_data['port'],
                    timeout=form_data['timeout']
                )
                
                logging.info(f"Connected to {ip}, executing command...")
                stdin, stdout, stderr = client.exec_command(form_data['command'])
                output = stdout.read().decode()
                response_time = round(time.time() - start_time, 2)
                error = None
                logging.info(f"Command execution completed on {ip} in {response_time} seconds")
                
            except Exception as e:
                response_time = round(time.time() - start_time, 2)
                output = None
                error = str(e)
                logging.error(f"Error on {ip}: {error}")
            
            finally:
                client.close()
            
            results_queue.put({
                'ip': ip,
                'response': response_time,
                'output': output,
                'error': error
            })

        # Process SSH connections sequentially
        for ip in form_data['ips'].split('\n'):
            if ip.strip():
                process_ssh(ip.strip())
        
        logging.info("All connections completed")
        results_queue.put({'completed': True})  
        return render_template('index.html', form_data=form_data)

    return render_template('index.html', form_data=default_values)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)