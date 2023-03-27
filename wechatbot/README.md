## 微信机器人 

最近ChatGPT异常火爆，想到将其接入到个人微信是件比较有趣的事，所以有了这个项目。项目基于[openwechat](https://github.com/eatmoreapple/openwechat)开发，支持ChatGPT和New Bing，其中New Bing[依赖于new-bing项目](../new-bing)提供的http接口。

## 目前实现了以下功能
 + 群聊@回复
 + 私聊回复
 + 自动通过回复
 
## 注册openai
ChatGPT注册可以参考[这里](https://juejin.cn/post/7173447848292253704)

## 部署

```
# 获取项目
git clone https://github.com/bujnlc8/gptbing

# 进入项目目录
cd gptbing/wechatbot

# 复制配置文件, 改成实际的值，注意去掉#注释
copy config.json.example config.json

# 启动项目
go run main.go


或者docker部署

bash start.sh 0.0.2   # 代理地址根据实际情况修改，运行之后`docker logs wechatbot`会打印出登录地址

```

## 说明

本项目fork至[https://github.com/djun/wechatbot](https://github.com/djun/wechatbot)，修改使之支持`ChatGPT`和`New Bing`，在此致谢！

**⚠️  有一定的几率导致被微信封号，请谨慎使用，由此导致的封号，本人概不负责**
