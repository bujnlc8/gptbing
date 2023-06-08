## New Bing 接口

包括 http 和 websocket 两种协议的接口，可根据实际情况选用

## 部署

[登录 bing 账号](https://login.live.com/)， 使用[Cookie-Editor 扩展](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)将 cookie 以 json 格式导出，保存为`cookie0.json`文件，同时将`COOKIE_FILES`环境变量的值指向该文件。

```
1.git clone https://github.com/bujnlc8/gptbing
2.cd gptbing/new-bing
3.mkdir cookies && mv cookie0.json cookies # 通过COOKIE_FILES环境变量可以支持n个账号的自动切换，目前微软对每个账号每天的聊天限制是200条
4.cp env.example env  # 根据实际情况修改
5.bash start.sh 0.0.3
6.curl -X POST 'http://127.0.0.1:8000/bing/chat' -H 'content-type: application/json' -H 'Referer: servicewechat.com/wxee7496be5b68b740' --data '{"q":"你是谁?","t":1,"sid":"1"}' # 验证是否成功
```

## 说明

`EdgeGPT.py`文件 fork 至[https://github.com/acheong08/EdgeGPT](https://github.com/acheong08/EdgeGPT)，并做了些许修改，在此表示感谢！

**⚠️ 目前中国大陆的 IP 会返回 404，自备代理** 见[https://github.com/acheong08/EdgeGPT/issues/178](https://github.com/acheong08/EdgeGPT/issues/178)
