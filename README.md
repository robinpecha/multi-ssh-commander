# multi-ssh-commander

A tool that allows you to run commands sequentially on specified ssh targets.  
Python script with a web interface.

![screenshot](screenshot.png)

# How to start in docker (linux)

1. Clone / download this repo

```
# clone repo:

git clone https://github.com/robinpecha/multi-ssh-commander.git

# or download and unpack in zip file:

wget https://github.com/robinpecha/multi-ssh-commander/archive/refs/heads/main.zip
unzip main.zip 
mv multi-ssh-commander-main multi-ssh-commander
rm main.zip
```

2. Jump in directory

```
cd multi-ssh-commander/multissh
```

3. Start with docker compose

```
docker compose up -d
```

4. Open http://localhost:8080/ in your browser


