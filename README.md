# multi-ssh-commander

A tool that allows you to run commands sequentially on specified ssh targets.  
Python script with a web interface.

![screenshot](screenshot.png)

# Start in Docker from dockerhub
```
docker run -d --name multisshcommander -p 8000:8080 robinpecha/dockerhub:multisshcommander
```
Then open http://localhost:8080/ in your browser


# Download, build and start (Linux)
1. Clone / download this repo

```
# clone repo:

git clone https://github.com/robinpecha/multi-ssh-commander.git

# or download and unpack zip file:

wget https://github.com/robinpecha/multi-ssh-commander/archive/refs/heads/main.zip
unzip main.zip 
mv multi-ssh-commander-main multi-ssh-commander
rm main.zip
```


2. Jump to directory

```
cd multi-ssh-commander
```

3. Run script or start container

To start script localy, install requirements and run script:
```
pip install --no-cache-dir -r requirements.txt
python multisshcommander.py
```

Or start docker container with app:
```
docker compose up -d
```

4. Open http://localhost:8080/ in your browser


