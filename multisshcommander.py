from flask import Flask, render_template, request, Response, send_from_directory
import paramiko
import logging
import time
import json
from queue import Queue
import os
from werkzeug.utils import secure_filename

# Initialize Flask app - use current directory for templates
app = Flask(__name__, template_folder='.')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.expanduser('~/.ssh'), 'uploaded_keys')

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], mode=0o700)

# Initialize queue for results
results_queue = Queue()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('log.txt'),
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
    'timeout': 3,
    'auth_method': 'password',
    'key_path': '',
    'key_passphrase': ''
}

def parse_host_port(host_string, default_port):
    """Parse host:port string. Returns (host, port) tuple.
    If no port specified, returns default_port.
    Examples: 
      '192.168.1.1:2222' -> ('192.168.1.1', 2222)
      '192.168.1.1' -> ('192.168.1.1', 22)
      'example.com:11111' -> ('example.com', 11111)
    """
    if ':' in host_string:
        parts = host_string.rsplit(':', 1)
        try:
            return parts[0], int(parts[1])
        except ValueError:
            # Invalid port number, use default
            return host_string, default_port
    return host_string, default_port

@app.route('/stream')
def stream():
    def generate():
        while True:
            if not results_queue.empty():
                result = results_queue.get()
                yield f"data: {json.dumps(result)}\n\n"
    return Response(generate(), mimetype='text/event-stream')

@app.route('/styles.css')
def serve_css():
    return send_from_directory('.', 'styles.css')

@app.route('/log.txt')
def serve_log():
    return send_from_directory('.', 'log.txt')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        auth_method = request.form.get('auth_method', 'password')
        key_path = request.form.get('key_path', '')
        
        # Handle file upload if key auth and file uploaded
        if auth_method == 'key' and 'key_file' in request.files:
            key_file = request.files['key_file']
            if key_file.filename:
                filename = secure_filename(key_file.filename)
                key_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                key_file.save(key_path)
                os.chmod(key_path, 0o600)  # Set proper permissions
                logging.info(f"Key file uploaded: {key_path}")
        
        form_data = {
            'username': request.form.get('username'),
            'password': request.form.get('password'),
            'port': int(request.form.get('port')),
            'command': request.form.get('command'),
            'ips': request.form.get('ips'),
            'timeout': int(request.form.get('timeout', default_values['timeout'])),
            'auth_method': auth_method,
            'key_path': key_path,
            'key_passphrase': request.form.get('key_passphrase', '')
        }

        def process_ssh(host_string):
            # Parse host and port (host:port or just host)
            ip, port = parse_host_port(host_string, form_data['port'])
            
            logging.info("")  # Log an empty line before each connection
            logging.info(f"Connecting to {ip}:{port}...")
            client = paramiko.SSHClient()
            
            # Load known hosts if file exists
            if os.path.exists(known_hosts_path):
                client.load_host_keys(known_hosts_path)
            
            # Still use RejectPolicy but we'll handle key verification manually
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
            
            start_time = time.time()
            try:
                # Get remote server's key
                transport = paramiko.Transport((ip, port))
                transport.start_client()
                remote_key = transport.get_remote_server_key()
                
                # Save the key with proper hostname format
                # For non-standard ports, use [hostname]:port format
                hostname_for_key = f"[{ip}]:{port}" if port != 22 else ip
                client._host_keys.add(hostname_for_key, remote_key.get_name(), remote_key)
                
                # Save to known_hosts file
                client.save_host_keys(known_hosts_path)
                
                transport.close()
                
                # Now connect with verified key
                connect_kwargs = {
                    'hostname': ip,
                    'username': form_data['username'],
                    'port': port,
                    'timeout': form_data['timeout']
                }
                
                # Add authentication method
                if form_data['auth_method'] == 'password':
                    connect_kwargs['password'] = form_data['password']
                    logging.info(f"Using password authentication for {ip}")
                elif form_data['auth_method'] == 'key':
                    if form_data['key_path']:
                        # Expand path for ~ or environment variables
                        key_path = os.path.expanduser(form_data['key_path'])
                        if os.path.exists(key_path):
                            connect_kwargs['key_filename'] = key_path
                            if form_data['key_passphrase']:
                                connect_kwargs['passphrase'] = form_data['key_passphrase']
                            logging.info(f"Using key authentication for {ip} with key: {key_path}")
                        else:
                            raise Exception(f"Key file not found: {key_path}")
                    else:
                        # Try default keys in ~/.ssh/
                        connect_kwargs['look_for_keys'] = True
                        logging.info(f"Using default SSH keys for {ip}")
                
                client.connect(**connect_kwargs)
                
                logging.info(f"Connected to {ip}:{port}, executing command...")
                stdin, stdout, stderr = client.exec_command(form_data['command'])
                output = stdout.read().decode()
                response_time = round(time.time() - start_time, 2)
                error = None
                logging.info(f"Command execution completed on {ip}:{port} in {response_time} seconds")
                
            except Exception as e:
                response_time = round(time.time() - start_time, 2)
                output = None
                error = str(e)
                logging.error(f"Error on {ip}:{port}: {error}")
            
            finally:
                client.close()
            
            # Display host:port if non-standard port
            display_host = f"{ip}:{port}" if port != 22 else ip
            results_queue.put({
                'ip': display_host,
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