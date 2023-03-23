# wechatbot
最近chatGPT异常火爆，想到将其接入到个人微信是件比较有趣的事，所以有了这个项目。项目基于[openwechat](https://github.com/eatmoreapple/openwechat)开发，支持chatGPT和New Bing[依赖于new-bing项目](../new-bing)

### 目前实现了以下功能
 + 群聊@回复
 + 私聊回复
 + 自动通过回复
 
# 注册openai
chatGPT注册可以参考[这里](https://juejin.cn/post/7173447848292253704)

# 安装使用

```
# 获取项目
git clone https://github.com/bujnlc8/gptbing

# 进入项目目录
cd gptbing/wechatbot

# 复制配置文件
copy config.dev.json config.json

# 启动项目
go run main.go

```

本项目fork至[https://github.com/djun/wechatbot](https://github.com/djun/wechatbot)，修改使之支持`chatGPT`和`New bing`，在此致谢！

**⚠️  有一定的几率导致被微信封号，请谨慎使用，由此导致的封号，本人概不负责**
