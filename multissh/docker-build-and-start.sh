#docker rm multissh-webui --force
#docker rmi multissh-webui --force
docker build -t multisshcommander .
docker compose up -d 

