import {
  doRequest
} from "../../config";

const systemInfo = wx.getSystemInfoSync()

function inputPop() {
  return systemInfo.platform == "ios" || systemInfo.platform == "android"
}

const initHeight = inputPop() ? 20 : 2

Date.prototype.format = function (fmt) {
  var o = {
    "M+": this.getMonth() + 1, //月份
    "d+": this.getDate(), //日
    "h+": this.getHours(), //小时
    "m+": this.getMinutes(), //分
    "s+": this.getSeconds(), //秒
    "q+": Math.floor((this.getMonth() + 3) / 3), //季度
    S: this.getMilliseconds(), //毫秒
  };
  if (/(y+)/.test(fmt)) {
    fmt = fmt.replace(
      RegExp.$1,
      (this.getFullYear() + "").substr(4 - RegExp.$1.length)
    );
  }
  for (var k in o) {
    if (new RegExp("(" + k + ")").test(fmt)) {
      fmt = fmt.replace(
        RegExp.$1,
        RegExp.$1.length == 1 ? o[k] : ("00" + o[k]).substr(("" + o[k]).length)
      );
    }
  }
  return fmt;
};

function getNow() {
  return new Date().format("yyyy-MM-dd hh:mm:ss");
}

const app = getApp();
const robAvatar = "../../image/bing-avatar.png";
const personAvatar = "../../image/person.jpeg";

Page({
  data: {
    InputBottom: initHeight,
    content: "",
    systemInfo: systemInfo,
    textareaFocus: false,
    searching: false,
  },
  InputFocus(e) {
    if (inputPop()) {
      this.setData({
        InputBottom: e.detail.height,
      });
    }
  },
  InputBlur(e) {
    this.setData({
      InputBottom: initHeight,
    });
  },
  processContent(content) {
    return content.replace(/\\n/g, "\n");
  },
  resetConversation: function (callback) {
    app.getSid(sid => {
      doRequest("/reset", "GET", {
        sid: sid,
      }).then(res => {
        if (callback) {
          callback(res)
        }
      })
    })
  },
  onShow() {
    const cht = app.globalData.cht;
    if (cht.data.chatList.length > 1) {
      cht.setData({
        scrollId: "item" + (cht.data.chatList.length - 2),
      });
    }
  },
  onLoad() {},
  submitContent: function (content) {
    if (this.data.searching) {
      wx.showToast({
        title: '请等待完成',
        icon: 'error'
      })
      return
    } else {
      this.setData({
        searching: true
      })
    }
    var that = this;
    const cht = app.globalData.cht;
    that.pushStorageMessage(cht, content, "man", [], false)
    that.setData({
      content: "",
    });
    if (content == "重新对话！") {
      that.resetConversation(() => {
        that.pushStorageMessage(cht, "现在我们可以开始新的对话😊", "rob", [], false)
      });
      return;
    } else {
      that.pushStorageMessage(cht, "搜索中🔍...", "rob", [], true)
    }
    app.getSid(sid => {
      doRequest("/chat", "POST", {
        q: content,
        sid: sid,
      }).then(res => {
        try {
          var robContent = "";
          var suggests = [];
          if (res.statusCode != 200) {
            robContent =
              "抱歉😭，网络异常，请稍后重试 [" + res.statusCode + "]";
            suggests.push(content);
          } else {
            robContent = res.data["data"]["status"];
            if (robContent == "Success") {
              robContent = res.data["data"]["text"];
              suggests = res.data["data"]["suggests"];
              if (robContent.indexOf("New topic") != -1) {
                robContent += "\n\n发送“重新对话！”开始新的对话";
                suggests.push("重新对话！");
                suggests.push(content);
              }
            } else {
              if (robContent == "Throttled") {
                robContent = "这真是愉快，但你已达到每日限制。是否明天再聊？";
                suggests.push("重新对话！");
                suggests.push(content);
              } else {
                var msg = res.data["data"]["message"];
                if (msg.indexOf("has expired") != -1) {
                  that.resetConversation();
                  robContent = "本轮对话已过期，请重新开始。";
                  suggests.push(content);
                } else {
                  robContent = "抱歉😭，发生错误：" + msg + "，请重试";
                  suggests.push(content);
                }
              }
            }
          }
          that.pushStorageMessage(cht, robContent, "rob", suggests, false, true)
        } catch (error) {
          wx.showToast({
            title: "fatal error",
          });
          that.pushStorageMessage(cht, "发生致命错误😱", "rob", [], false, true)
        }
      }).catch(e => {
        that.pushStorageMessage(cht, e.errMsg, "rob", [], false, true)
      })
    })
  },
  pushStorageMessage: function (cht, content, role, suggests, blink, pop) {
    if (pop) {
      cht.data.chatList.pop();
    }
    cht.data.chatList.push({
      type: role,
      avatarUrl: role == "rob" ? robAvatar : personAvatar,
      dt: getNow(),
      originContent: this.processContent(content),
      suggests: suggests,
      blink: blink,
    });
    cht.setData({
      chatList: cht.data.chatList,
    });
    if (role == "rob" && !blink) {
      this.setData({
        searching: false
      })
    }
    wx.setStorage({
      key: "chatList",
      data: cht.data.chatList,
    });
    setTimeout(() => {
      cht.setData({
        scrollId: "item" + (cht.data.chatList.length - 1),
      });
    }, 50);
  },
  submit() {
    var content = this.data.content;
    if (content.length == 0 || content.trim().length == 0) {
      return;
    }
    this.submitContent(content);
  },
  onShareAppMessage() {
    return {
      title: "New Bing Bot 🤖",
      path: "/pages/index/index",
    };
  },
  onSuggestSubmit: function (e) {
    var suggest = e.detail.suggest;
    this.submitContent(suggest);
  },
  focus: function (e) {
    this.setData({
      textareaFocus: true
    })
  }
});
