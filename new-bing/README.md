[登录 bing 账号](https://login.live.com/)， 使用[Cookie-Editor 扩展](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)将 cookie 以 json 格式导出，保存为`cookie.json`文件，同时将`COOKIE_FILE`环境变量的值指向该文件。

## 部署

```
1.新建cookies目录，将cookie.json放入该目录，支持3个cookie，可分别命名为cookie.json,cookie1.json,cookie2.json
2.cp env.example env  # 根据实际情况修改
3.bash start.sh 0.0.1
4.curl -X POST 'http://127.0.0.1:8000/chat' -H 'content-type: application/json' --data '{"q":"你是谁?","t":1,"sid":"1"}' 验证是否成功
```

**⚠️ 目前中国大陆的IP会返回404，自备代理** 见[https://github.com/acheong08/EdgeGPT/issues/178](https://github.com/acheong08/EdgeGPT/issues/178)

`EdgeGPT.py`文件 fork 至[https://github.com/acheong08/EdgeGPT](https://github.com/acheong08/EdgeGPT)，并做了些许修改，在此表示感谢！
