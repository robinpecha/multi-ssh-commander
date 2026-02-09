from flask import Flask, render_template, request, Response
import paramiko
import logging
import time
import json
from queue import Queue
import os
from werkzeug.utils import secure_filename

# Initialize Flask app
app = Flask(__name__)
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
    'timeout': 3,
    'auth_method': 'password',
    'key_path': '',
    'key_passphrase': ''
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
                connect_kwargs = {
                    'hostname': ip,
                    'username': form_data['username'],
                    'port': form_data['port'],
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