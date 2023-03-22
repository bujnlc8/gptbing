docker pull yy194131/new-bing:$1
docker stop new-bing && docker rm new-bing
docker run --restart always --name new-bing --env-file $(pwd)/env -p 8000:8000 -d yy194131/new-bing:$1
