import {
  SERVER_HOST
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
  resetConversation: function () {
    wx.request({
      url: SERVER_HOST + "/bing/reset",
      data: {
        t: new Date().getTime(),
        sid: app.getSid(),
      },
      enableHttp2: true,
    });
  },
  onShow() {
    const cht = app.globalData.cht;
    if (cht.data.chatList.length > 1) {
      cht.setData({
        scrollId: "item" + (cht.data.chatList.length - 2),
      });
    }
  },
  onLoad() {
  },
  submitContent: function (content) {
    var that = this;
    const cht = app.globalData.cht;
    content = this.processContent(content);
    cht.data.chatList.push({
      type: "man",
      avatarUrl: personAvatar,
      dt: getNow(),
      originContent: content,
    });
    cht.setData({
      chatList: cht.data.chatList,
    });
    that.setData({
      content: "",
    });
    if (content == "重新对话！") {
      this.resetConversation();
      cht.data.chatList.push({
        type: "rob",
        avatarUrl: robAvatar,
        dt: getNow(),
        originContent: "现在我们可以开始新的对话😊",
        suggests: [],
      });
      cht.setData({
        chatList: cht.data.chatList,
      });
      that.scrollTo(cht);
      return;
    } else {
      cht.data.chatList.push({
        type: "rob",
        avatarUrl: robAvatar,
        dt: getNow(),
        originContent: "搜索中🔍...",
        suggests: [],
        blink: true,
      });
      cht.setData({
        chatList: cht.data.chatList,
      });
    }
    wx.request({
      url: SERVER_HOST + "/bing/chat",
      method: "POST",
      data: {
        q: content,
        t: new Date().getTime(),
        sid: app.getSid(),
      },
      enableHttp2: true,
      success(res) {
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
                robContent += "\n发送“重新对话！”开始新的对话";
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
          cht.data.chatList.pop();
          cht.data.chatList.push({
            type: "rob",
            avatarUrl: robAvatar,
            dt: getNow(),
            originContent: that.processContent(robContent),
            suggests: suggests,
          });
          cht.setData({
            chatList: cht.data.chatList,
          });
          wx.setStorage({
            key: "chatList",
            data: cht.data.chatList,
          });
        } catch (error) {
          console.log(error);
          wx.showToast({
            title: "fatal error",
          });
        }
      },
      fail(e) {
        console.log(e);
        cht.data.chatList.pop();
        cht.data.chatList.push({
          type: "rob",
          avatarUrl: robAvatar,
          dt: getNow(),
          originContent: e.errMsg,
          suggests: [],
        });
      },
    });
    that.scrollTo(cht);
  },
  scrollTo: function (cht) {
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
	focus: function(e){
		console.log(e)
		this.setData({
			textareaFocus: true
		})
	}
});
