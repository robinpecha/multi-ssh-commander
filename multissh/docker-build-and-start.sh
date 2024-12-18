#docker rm multissh-webui --force
#docker rmi multissh-webui --force
docker build -t multissh-webui .
docker compose up -d 

