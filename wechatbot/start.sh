docker pull yy194131/chatgpt:$1

count=$(docker ps -a | grep wechatbot | wc -l)
if [ $count -gt 0 ]; then
  docker stop wechatbot && docker rm wechatbot
fi

# 代理地址改成实际的地址
docker run --name wechatbot -d -e https_proxy=代理地址 -v $(pwd)/config.json:/app/config.json yy194131/chatgpt:$1
