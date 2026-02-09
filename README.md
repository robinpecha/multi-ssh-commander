# multi-ssh-commander
A tool that allows you to run commands sequentially on specified ssh targets. Simple python script with a web interface.

**Features:**
- Execute commands on multiple SSH hosts sequentially
- Support for both **password** and **SSH key** authentication
- Upload SSH keys or use existing ones from filesystem
- Real-time output streaming
- Connection logging and monitoring

<ins>**THIS IS AN UNSTABLE DEVELOPMENT VERSION, USE IT AT YOUR OWN RISK.**</ins>
>I strongly recommend opening a side panel with logs to monitor whole process. HTML listing at the bottom can be not so accurate.




![screenshot](screenshot.png)

# Start in Docker from dockerhub

```
docker run -d --name multisshcommander -p 8080:8080 robinpecha/dockerhub:multisshcommander
```

Then open http://localhost:8080/ in your browser

# Download, build and start (Linux)

### Clone / download this repo

```
# clone repo:

git clone https://github.com/robinpecha/multi-ssh-commander.git

# or download and unpack zip file:

wget https://github.com/robinpecha/multi-ssh-commander/archive/refs/heads/main.zip
unzip main.zip 
mv multi-ssh-commander-main multi-ssh-commander
rm main.zip
```

### Jump to directory

```
cd multi-ssh-commander
```

### Start container or run script localy

Or start docker container with app:
```
docker compose up -d --force-recreate
```

To start script localy, install requirements and run script:
**CAUTION, this was not really tested, take care about known_hosts and user rights by yourself!**
```
pip install --no-cache-dir -r requirements.txt
python multisshcommander.py
```

### Open http://localhost:8080/ in your browser

## Authentication Methods

The tool supports two authentication methods:

### Password Authentication
Select "Password" from the authentication method dropdown and enter your SSH password.

### SSH Key Authentication
Select "SSH Key" from the authentication method dropdown. You have three options:

1. **Use default SSH keys**: Leave the key path empty, and the tool will look for keys in `~/.ssh/` (id_rsa, id_dsa, id_ecdsa, id_ed25519)

2. **Specify key path**: Enter the full path to your private key file (e.g., `~/.ssh/id_rsa` or `/home/user/.ssh/mykey.pem`)

3. **Upload key file**: Use the file upload button to upload your private key file. The file will be securely stored in `~/.ssh/uploaded_keys/` with proper permissions (600)

If your private key is encrypted, enter the passphrase in the "Key Passphrase" field.

**Security Note**: Uploaded keys are stored on the server. For production use, consider using key paths or mounting keys via Docker volumes instead of uploading.
