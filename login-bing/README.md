## 定时刷新 Bing Cookie

Bing的cookie有效期大概是15天，15天之后就必须重新导出cookie，使[new-bing](../new-bing)继续运行，人工操作显然是很繁琐的，特别是有多个账号的情况下。因此，自动刷新cookie就显得重要了。

原理很简单，就是在一个无头的Chrome里，用[selenium](https://github.com/SeleniumHQ/selenium)自动点击操作，登录成功之后将cookie导出。再用`crontab`实现定时执行。
