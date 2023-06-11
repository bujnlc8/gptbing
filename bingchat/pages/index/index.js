import {
  doRequest,
  SERVER_WSS_HOST,
  systemInfo,
  sidPrefix,
  cacheChatNum,
} from "../../config";

const initHeight = systemInfo.platform == "ios" ? 15 : 5;
// 是否使用websocket请求
var useWebsocket = true;
// try {
// 	var notuseWebsocket = wx.getStorageSync("notuseWebsocket")
// 	if (notuseWebsocket) {
// 		useWebsocket = false
// 	}
// } catch (e) {
// 	useWebsocket = true
// }
// var showHelpTip = false;
// try {
//   var closeHelpTip = wx.getStorageSync("closeHelpTip");
//   if (closeHelpTip) {
//     showHelpTip = false;
//   }
// } catch (e) {
//   showHelpTip = true;
// }
var showTopTip = true;

try {
  var closeTopTip = wx.getStorageSync("closeTopTip");
  if (closeTopTip) {
    showTopTip = false;
  }
} catch (e) {
  showTopTip = true;
}

function inputPop() {
  return systemInfo.platform == "ios" || systemInfo.platform == "android";
}
// 自增对话
var autoIncrConversation = 0;

// 默认采用new bing
var chatType = "bing";
try {
  if (wx.getStorageSync("usechatgpt")) {
    chatType = "chatgpt";
  }
} catch (e) {
  chatType = "bing";
}
// 对话模式
var chatStyleList = ["creative", "balanced", "precise"];
var chatStyle = chatStyleList[0];
try {
  var chatStyle = wx.getStorageSync("chatStyle");
  if (!chatStyle) {
    chatStyle = chatStyleList[0];
  }
} catch (e) {
  chatStyle = chatStyleList[0];
}

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
    inputBottom: initHeight,
    content: "",
    lastContent: "",
    systemInfo: systemInfo,
    textareaFocus: false,
    searching: false,
    socket: {
      socket: null,
      isOpen: false,
    },
    useWebsocket: useWebsocket,
    showSearchPop: false,
    searchPopMessage: "",
    chatType: chatType,
    chatStyle: chatStyle,
    chatStyleBg: {
      creative: "#62102e",
      balanced: "#1B4AEF",
      precise: "#005366",
    },
    chatBoxHeight: systemInfo.windowHeight - (initHeight + 60),
    showHelpTip: false,
    loadData: true,
    showTopTip: showTopTip,
  },
  inputFocus(e) {
    if (inputPop()) {
      this.setData({
        inputBottom: e.detail.height,
      });
    }
  },
  inputBlur(e) {
    this.setData({
      inputBottom: initHeight,
      textareaFocus: false,
    });
  },
  processContent(content) {
    return content.replace(/\\n/g, "\n").replace(/\[\^\d+\^\]/g, "");
  },
  resetConversation: function (callback) {
    app.getSid((sid) => {
      doRequest("/reset", "GET", {
        sid: sidPrefix + sid,
      }).then((res) => {
        if (callback) {
          callback(res);
        }
      });
    });
  },
  getOptions: function () {
    var pages = getCurrentPages();
    var currentPage = pages[pages.length - 1];
    return currentPage.options;
  },
  onPopButtonClick: function (e) {
    if (e.detail.t === "confirm") {
      this.submitContent(e.currentTarget.dataset.q);
    }
    this.setData({
      showSearchPop: false,
      q: "",
    });
  },
  onShow() {
    // 切换title
    this.switchTitle();
  },
  switchTitle: function () {
    if (this.data.chatType == "bing") {
      wx.setNavigationBarTitle({
        title: "New Bing",
      });
    } else {
      wx.setNavigationBarTitle({
        title: "ChatGPT",
      });
    }
  },
  scrollBottom: function () {
    var cht = this.selectComponent("#chat-id");
    if (cht.data.chatList.length > 1 && !this.data.textareaFocus) {
      cht.setData({
        scrollId: "item" + (cht.data.chatList.length - 2),
      });
    }
  },
  onLoad() {
    var cht = this.selectComponent("#chat-id");
    setTimeout(() => {
      if (cht.data.chatList.length > 1) {
        cht.setData({
          scrollId: "item" + (cht.data.chatList.length - 2),
        });
      }
    }, 300);
    var options = this.getOptions();
    if (options && options["from"] == "friend") {
      this.setData({
        loadData: false,
      });
    }
    if (options && options["q"]) {
      var q = decodeURIComponent(options["q"]);
      var chatType = this.data.chatType;
      var chatStyle = this.data.chatStyle;
      if (options["chatType"]) {
        chatType = options["chatType"];
        // 聊天方式不同，关闭websocket
        if (chatType != this.data.chatType) {
          this.onCancelReceive();
        }
      }
      if (options["chatStyle"]) {
        chatStyle = options["chatStyle"];
      }
      this.setData({
        searchPopMessage: "即将搜索「" + q + "」",
        showSearchPop: true,
        q: q,
        chatType: chatType,
        chatStyle: chatStyle,
      });
    } else {
      options["q"] = null;
    }
  },
  processData: function (data, suggests, content) {
    var robContent = data["data"]["status"];
    if (robContent == "Success") {
      robContent = data["data"]["text"];
      suggests.push(...data["data"]["suggests"]);
      if (
        robContent.indexOf("New topic") != -1 &&
        this.data.chatType == "bing"
      ) {
        robContent += "\n发送「重新对话！」开始新的对话";
        suggests.push("重新对话！");
        suggests.push(content);
      }
    } else {
      if (robContent == "Throttled") {
        robContent = "这真是愉快，但你已达到每日限制。是否明天再聊？";
        suggests.push("重新对话！");
        suggests.push(content);
      } else {
        var msg = data["data"]["message"];
        if (msg.indexOf("has expired") != -1) {
          this.resetConversation();
          robContent = "本轮对话已过期，请重新开始。";
          suggests.push(content);
        } else {
          robContent = "抱歉，发生错误：" + msg;
          if (this.data.chatType == "bing") {
            suggests.push("重新对话！");
          }
          suggests.push(content);
        }
      }
    }
    return robContent;
  },
  sendWSRequest: function (content) {
    var that = this;
    app.getSid((sid) => {
      that.sendSocketMessage({
        q: content,
        sid: sidPrefix + sid,
        t: new Date().getTime(),
        style: that.data.chatStyle,
      });
    });
  },
  sendHttpRequest: function (content) {
    var that = this;
    var cht = this.selectComponent("#chat-id");
    var api = that.data.chatType == "bing" ? "/chat" : "/openai_chat";
    app.getSid((sid) => {
      doRequest(api, "POST", {
        q: content,
        sid: sidPrefix + sid,
        style: that.data.chatStyle,
      })
        .then((res) => {
          try {
            var robContent = "";
            var suggests = [];
            var num_in_conversation = -1;
            if (res.statusCode != 200) {
              robContent =
                "抱歉，网络异常，请稍后重试 [" + res.statusCode + "]";
              suggests.push(content);
            } else {
              robContent = that.processData(res.data, suggests, content);
              num_in_conversation = res.data["data"]["num_in_conversation"];
            }
            that.pushStorageMessage(
              cht,
              robContent,
              "rob",
              suggests,
              false,
              true,
              num_in_conversation
            );
          } catch (error) {
            wx.showToast({
              title: "fatal error",
              icon: "error",
            });
            that.pushStorageMessage(
              cht,
              "发生致命错误😱",
              "rob",
              [],
              false,
              true
            );
          }
        })
        .catch((e) => {
          that.pushStorageMessage(cht, e.errMsg, "rob", [], false, true);
        });
    });
  },
  submitContent: function (content) {
    if (!content || !content.trim()) {
      return;
    }
    var that = this;
    if (that.data.searching) {
      wx.showToast({
        title: "请等待完成",
        icon: "error",
      });
      return;
    } else {
      that.setData({
        searching: true,
      });
    }
    if (content.startsWith("memos_openapi#")) {
      var url = content.split("#")[1];
      if (!url || !url.startsWith("http")) {
        wx.showToast({
          title: "格式错误",
          icon: "none",
        });
      } else {
        wx.setStorage({
          key: "memos_openapi",
          data: url,
          success: (res) => {
            wx.showToast({
              title: "设置成功",
              icon: "none",
            });
          },
        });
      }
      that.setData({
        content: "",
        searching: false,
      });
      return;
    }
    if (content.startsWith("flomo_api#")) {
      var url = content.split("#")[1];
      if (!url || !url.startsWith("https")) {
        wx.showToast({
          title: "格式错误",
          icon: "none",
        });
      } else {
        wx.setStorage({
          key: "flomo_api",
          data: url,
          success: (res) => {
            wx.showToast({
              title: "设置成功",
              icon: "none",
            });
          },
        });
      }
      that.setData({
        content: "",
        searching: false,
      });
      return;
    }
    var cht = this.selectComponent("#chat-id");
    that.pushStorageMessage(cht, content, "man", [], false);
    that.setData({
      content: "",
      lastContent: content,
    });
    if (content == "重新对话！" && that.data.chatType == "bing") {
      that.resetConversation(() => {
        that.pushStorageMessage(
          cht,
          "现在我们可以开始新的对话😊",
          "rob",
          [],
          false
        );
      });
      return;
    } else {
      that.pushStorageMessage(
        cht,
        "搜索中🔍...",
        "rob",
        [],
        true,
        false,
        -1,
        false
      );
    }
    if (that.data.useWebsocket) {
      that.sendWSRequest(content);
    } else {
      that.sendHttpRequest(content);
    }
  },
  pushStorageMessage: function (
    cht,
    content,
    role,
    suggests,
    blink,
    pop,
    num_in_conversation = -1,
    final = true
  ) {
    if (pop) {
      cht.data.chatList.pop();
    }
    var rAvatar =
      this.data.chatType == "bing" ? robAvatar : "../../image/chatgpt.png";
    cht.data.chatList.push({
      type: role,
      avatarUrl: role == "rob" ? rAvatar : personAvatar,
      dt: getNow(),
      originContent: this.processContent(content),
      suggests: suggests,
      blink: blink,
      num_in_conversation: num_in_conversation,
    });
    autoIncrConversation += 1;
    cht.setData({
      chatList: cht.data.chatList,
      autoIncrConversation: autoIncrConversation,
    });
    if (role == "rob" && !blink && final) {
      this.setData({
        searching: false,
      });
    }
    // 只保留最新的cacheChatNum条
    wx.setStorage({
      key: "chatList",
      data: cht.data.chatList.slice(cht.data.chatList.length - cacheChatNum),
    });
    if (final) {
      app.upload_conversation(
        cht.data.chatList.slice(cht.data.chatList.length - 3)
      );
    }
    setTimeout(() => {
      cht.setData({
        scrollId: "item" + (autoIncrConversation + "9999"),
      });
    }, 100);
  },
  submit() {
    var content = this.data.content;
    if (!content || content.length == 0 || content.trim().length == 0) {
      wx.showToast({
        title: "请输入问题",
        icon: "none",
      });
      return;
    }
    this.submitContent(content);
  },
  onShareAppMessage() {
    var title =
      this.data.chatType == "bing" ? "New Bing Bot，聊你想聊！" : "ChatGPT Bot";
    var content = this.data.content.trim();
    if (content.length > 0) {
      title = content;
    } else {
      var cache = wx.getStorageSync("shareContent");
      if (cache) {
        if (cache["validTime"] > new Date().getTime()) {
          content = cache["q"];
          title = content;
          wx.removeStorage({
            key: "shareContent",
          });
        }
      }
    }
    return {
      title: title,
      path:
        "/pages/index/index?q=" +
        encodeURIComponent(content) +
        "&chatType=" +
        this.data.chatType +
        "&chatStyle=" +
        this.data.chatStyle,
      imageUrl:
        this.data.chatType == "bing"
          ? "../../image/newBing.png"
          : "../../image/chatgptShare.png",
    };
  },
  onShareTimeline: function () {
    return {
      title: "New Bing Bot，聊你想聊！",
      imageUrl: "../../image/pyq.png",
      query: "chatType=bing&from=friend",
    };
  },
  onSuggestSubmit: function (e) {
    var suggest = e.detail.suggest;
    if (suggest) {
      this.submitContent(suggest);
    }
  },
  focus: function (e) {
    this.setData({
      textareaFocus: true,
    });
  },
  openSocket(callback) {
    if (this.data.socket.isOpen) {
      return;
    }
    var that = this;
    var cht = this.selectComponent("#chat-id");
    var apiPath = that.data.chatType == "bing" ? "/chat" : "/ws_openai_chat";
    const socket = wx.connectSocket({
      url: SERVER_WSS_HOST + apiPath,
      fail: function () {
        wx.showToast({
          title: "打开websocket失败",
          icon: "none",
        });
      },
    });
    socket.onOpen(() => {
      console.log("Socket onOpen", socket);
      if (socket.readyState == 1) {
        that.setData({
          socket: {
            socket: socket,
            isOpen: true,
          },
        });
        setTimeout(() => {
          if (callback) {
            callback();
          }
        }, 50);
      }
    });
    socket.onClose((code, reason) => {
      console.log("Socket onClose", code, reason);
      that.setData({
        socket: {
          socket: null,
          isOpen: false,
        },
        searching: false,
      });
      cht.setData({
        receiveData: false,
      });
    });
    socket.onError((msg) => {
      console.log("Socket onError", msg);
      that.setData({
        socket: {
          socket: null,
          isOpen: false,
        },
        searching: false,
      });
      wx.showToast({
        title: "网络异常 " + msg.errMsg,
        icon: "none",
      });
      cht.setData({
        receiveData: false,
      });
    });
    socket.onMessage((data) => {
      var cht = this.selectComponent("#chat-id");
      if (!this.data.socket.isOpen) {
        cht.setData({
          receiveData: false,
        });
        return;
      }
      var data = JSON.parse(data.data);
      var suggests = [];
      var robContent = "";
      var num_in_conversation = -1;
      if (!data["final"]) {
        if (data["data"]["data"]) {
          robContent = data["data"]["data"]["text"] + " ...";
        } else {
          robContent = data["data"] + " ...";
        }
        cht.setData({
          receiveData: true,
        });
      } else {
        robContent = that.processData(
          data["data"],
          suggests,
          that.data.lastContent
        );
        num_in_conversation = data["data"]["data"]["num_in_conversation"];
        cht.setData({
          receiveData: false,
        });
      }
      that.pushStorageMessage(
        cht,
        robContent,
        "rob",
        suggests,
        false,
        true,
        num_in_conversation,
        data["final"]
      );
    });
  },
  sendSocketMessage: function (data) {
    if (!this.data.socket.isOpen) {
      this.openSocket(() => {
        this.data.socket.socket.send({
          data: JSON.stringify(data),
          fail: (err) => {
            console.log(err);
            wx.showToast({
              title: "消息发送失败",
              icon: "error",
            });
          },
        });
      });
    } else {
      this.data.socket.socket.send({
        data: JSON.stringify(data),
        fail: (err) => {
          console.log(err);
          wx.showToast({
            title: "消息发送失败",
            icon: "error",
          });
        },
      });
    }
  },
  onUnload: function () {
    if (this.data.socket.isOpen) {
      this.data.socket.socket.close({
        code: 1000,
        reason: "Page Unload",
      });
    }
  },
  inputData: function (e) {
    var that = this;
    var value = e.detail.value;
    that.setData({
      content: value,
    });
    // 特定用户在桌面版本下触发提交，因为textarea在桌面版下回车是换行，并且无法监听快捷键输入，只能出此下策
    if (systemInfo.platform != "windows" && systemInfo.platform != "mac") {
      return;
    }
    if (value.indexOf("》》》\n") != -1 || value.indexOf(">>>\n") != -1) {
      that.setData(
        {
          content: value.replace("》》》\n", "").replace(">>>\n", ""),
        },
        () => {
          that.submit();
        }
      );
    }
  },
  onCancelReceive: function (e) {
    if (this.data.socket.isOpen) {
      this.setData({
        socket: {
          socket: this.data.socket.socket,
          isOpen: false,
        },
        searching: false,
      });
      this.data.socket.socket.close({
        code: 1000,
        reason: "User Cancel",
      });
      var cht = this.selectComponent("#chat-id");
      cht.setData({
        receiveData: false,
      });
      app.upload_conversation(
        cht.data.chatList.slice(cht.data.chatList.length - 3)
      );
    }
  },
  switchRequestMethod: function (e) {
    var that = this;
    if (this.data.useWebsocket) {
      wx.setStorage({
        key: "notuseWebsocket",
        data: 1,
        success: (res) => {
          that.setData({
            useWebsocket: false,
          });
          wx.showToast({
            title: "已切换成Https",
            icon: "none",
          });
        },
      });
    } else {
      wx.removeStorage({
        key: "notuseWebsocket",
        success: (res) => {
          that.setData({
            useWebsocket: true,
          });
          wx.showToast({
            title: "已切换成Websocket",
            icon: "none",
          });
        },
      });
    }
  },
  deleteAllChat: function () {
    var cht = this.selectComponent("#chat-id");
    wx.showModal({
      content: "是否清除全部聊天？",
      complete: (res) => {
        if (res.confirm) {
          cht.setData({
            chatList: [],
          });
          app.getSid((sid) => {
            doRequest("/delete_all", "POST", {
              sid: sidPrefix + sid,
            }).then((res) => {
              console.log("delete all");
              wx.setStorage({
                key: "chatList",
                data: [],
              });
            });
          });
        }
      },
    });
  },
  chooseChatStyle: function () {
    var that = this;
    var items = ["更多创造力", "更多平衡", "更多精确"];
    items.forEach((v, k) => {
      if (that.data.chatStyle == chatStyleList[k]) {
        items[k] += "(已选)";
      }
    });
    wx.showActionSheet({
      title: "选择对话模式",
      itemList: items,
      success(res) {
        wx.showToast({
          title: ("已选择「" + items[res.tapIndex] + "」").replace(
            "(已选)",
            ""
          ),
          icon: "none",
        });
        var chatStyle = chatStyleList[res.tapIndex];
        if (that.data.chatStyle != chatStyle) {
          that.resetConversation();
          that.setData({
            chatStyle: chatStyle,
          });
          wx.setStorage({
            key: "chatStyle",
            data: chatStyle,
          });
        }
      },
    });
  },
  longPress: function (e) {
    var that = this;
    var cht = this.selectComponent("#chat-id");
    var itemList = ["设置 🔨 ", "显示帮助", "跳转收藏", "清除聊天"];
    if (
      (app.globalData["saved"] && app.globalData["saved"] == 1) ||
      that.data.chatType == "chatgpt"
    ) {
      itemList = [
        "设置 🔨 ",
        "显示帮助",
        "跳转收藏",
        "清除聊天",
        that.data.chatType == "bing" ? "切换成ChatGPT" : "切换成New Bing",
      ];
    }
    wx.showActionSheet({
      itemList: itemList,
      success(res) {
        if (res.tapIndex == 0) {
          wx.showActionSheet({
            itemList: [
              "选择对话模式",
              "Flomo API 地址",
              "Memos OpenAPI 地址",
              cht.data.closeShareOnCopy
                ? "打开复制问题后弹出分享"
                : "关闭复制问题后弹出分享",
            ],
            success: function (res) {
              if (res.tapIndex == 0) {
                that.chooseChatStyle();
              } else if (res.tapIndex == 3) {
                if (cht.data.closeShareOnCopy) {
                  cht.setData({
                    closeShareOnCopy: false,
                  });
                  wx.showToast({
                    title: "已打开复制后分享",
                    icon: "none",
                  });
                  wx.removeStorage({
                    key: "closeShareOnCopy",
                  });
                } else {
                  cht.setData({
                    closeShareOnCopy: true,
                  });
                  wx.showToast({
                    title: "已关闭复制后分享",
                    icon: "none",
                  });
                  wx.setStorage({
                    key: "closeShareOnCopy",
                    data: 1,
                  });
                }
              } else if (res.tapIndex == 2) {
                var oldUrl = wx.getStorageSync("memos_openapi");
                if (!oldUrl) {
                  if (
                    systemInfo.platform != "ios" &&
                    systemInfo.platform != "android"
                  ) {
                    oldUrl =
                      "抱歉，电脑版不支持在此输入，请将OpenApI地址以下面的格式发送到聊天来完成设置:\nmemos_openapi#http... 注意，将#后面的部分替换成真实地址，一般以http开头。";
                  }
                }
                wx.showModal({
                  title: "请输入Memos的OpenAPI地址",
                  placeholderText: "https://...",
                  content: oldUrl,
                  editable: true,
                  success(res) {
                    if (res.confirm) {
                      var i = res.content;
                      if (!i) {
                        return;
                      }
                      if (i.startsWith("抱歉，电脑版不支持")) {
                        return;
                      }
                      if (!i || !i.startsWith("http")) {
                        wx.showToast({
                          title: "格式错误",
                          icon: "none",
                        });
                      } else {
                        wx.setStorage({
                          key: "memos_openapi",
                          data: i,
                          success: (res) => {
                            wx.showToast({
                              title: "设置成功",
                              icon: "none",
                            });
                          },
                        });
                      }
                    }
                  },
                });
              } else if (res.tapIndex == 1) {
                {
                  var oldUrl = wx.getStorageSync("flomo_api");
                  if (!oldUrl) {
                    if (
                      systemInfo.platform != "ios" &&
                      systemInfo.platform != "android"
                    ) {
                      oldUrl =
                        "抱歉，电脑版不支持在此输入，请将API地址以下面的格式发送到聊天来完成设置:\nflomo_api#https://flomoapp.com... 注意，将#后面的部分替换成真实地址。";
                    }
                  }
                  wx.showModal({
                    title: "请输入Flomo的API地址",
                    placeholderText: "https://flomoapp.com...",
                    content: oldUrl,
                    editable: true,
                    success(res) {
                      if (res.confirm) {
                        var i = res.content;
                        if (!i) {
                          return;
                        }
                        if (i.startsWith("抱歉，电脑版不支持")) {
                          return;
                        }
                        if (!i || !i.startsWith("http")) {
                          wx.showToast({
                            title: "格式错误",
                            icon: "none",
                          });
                        } else {
                          wx.setStorage({
                            key: "flomo_api",
                            data: i,
                            success: (res) => {
                              wx.showToast({
                                title: "设置成功",
                                icon: "none",
                              });
                            },
                          });
                        }
                      }
                    },
                  });
                }
              }
            },
          });
        } else if (res.tapIndex == 1) {
          that.setData({
            showHelpTip: true,
          });
        } else if (res.tapIndex == 2) {
          wx.navigateTo({
            url: "/pages/collected/collected",
          });
        } else if (res.tapIndex == 3) {
          wx.showActionSheet({
            itemList: ["清除本机缓存", "清除全部记录"],
            success: (res) => {
              if (res.tapIndex == 0) {
                app.upload_conversation();
                setTimeout(() => {
                  wx.removeStorage({
                    key: "chatList",
                    success: (res) => {
                      cht.setData({
                        chatList: [],
                      });
                      wx.showToast({
                        title: "清除成功",
                      });
                    },
                  });
                }, 500);
              } else {
                that.deleteAllChat();
              }
            },
          });
        } else if (res.tapIndex == 10) {
          //that.switchRequestMethod()
        } else if (res.tapIndex == 4) {
          if (that.data.chatType == "chatgpt") {
            wx.removeStorage({
              key: "usechatgpt",
            });
            that.setData({
              chatType: "bing",
            });
            wx.showToast({
              title: "已切换成New Bing",
              icon: "none",
            });
          } else {
            wx.setStorage({
              key: "usechatgpt",
              data: 1,
            });
            that.setData({
              chatType: "chatgpt",
            });
            wx.showToast({
              title: "已切换成ChatGPT",
              icon: "none",
            });
          }
          // 关闭websocket
          that.onCancelReceive();
          setTimeout(() => {
            that.switchTitle();
          }, 100);
        }
      },
    });
  },
  closeHelpTip: function () {
    var that = this;
    wx.setStorage({
      key: "closeHelpTip",
      data: 1,
      success: (res) => {
        that.setData({
          showHelpTip: false,
        });
        wx.getStorage({
          key: "showHelpTipTip",
          fail: () => {
            wx.showToast({
              title: "可在弹出菜单中打开",
              icon: "none",
            });
            wx.setStorage({
              key: "showHelpTipTip",
              data: 1,
            });
          },
        });
      },
    });
  },
  closeTopTip: function () {
    var that = this;
    wx.showModal({
      content: "确定关闭？",
      complete: (res) => {
        if (res.confirm) {
          wx.setStorage({
            key: "closeTopTip",
            data: 1,
            success: function () {
              that.setData({
                showTopTip: false,
              });
            },
          });
        }
      },
    });
  },
  sendResetConversation: function () {
    this.submitContent("重新对话！");
    this.setData({
      showHelpTip: false,
    });
  },
});
