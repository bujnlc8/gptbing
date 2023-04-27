docker pull yy194131/new-bing:$1
count=$(docker ps -a | grep new-bing | wc -l)
if [ $count -gt 0 ]; then
  docker stop new-bing && docker rm new-bing
fi

docker run --restart always \
  --name new-bing \
  -v /etc/localtime:/etc/localtime \
  -v $(pwd)/logs:/sanic/logs \
  -v $(pwd)/cookies:/sanic/cookies \
  --env-file $(pwd)/env \
  -p 8000:8000 -d yy194131/new-bing:$1
