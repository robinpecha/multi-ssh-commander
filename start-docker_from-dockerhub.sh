docker run -d --name multisshcommander -p 8080:8080 robinpecha/dockerhub:multisshcommander
echo
read -p "You will now see the log output from the container. You can interrupt it by pressing Ctrl+C, but the container will continue running in the background. Press any key to continue."
docker logs multisshcommander -f
