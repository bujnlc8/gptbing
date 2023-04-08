count=$(docker ps -a | grep login-bing | wc -l)
if [ $count -gt 0 ]; then
  docker stop login-bing && docker rm login-bing
fi

if [ ! -f cron.log ]; then
  touch cron.log
fi

docker run --name login-bing -d -v $(pwd)/cronfile:/etc/cron.d/loginbing -v $(pwd)/cookies:/bing/cookies -v $(pwd)/cron.log:/bing/cron.log -v $(pwd)/env:/bing/env yy194131/login-bing:$1
