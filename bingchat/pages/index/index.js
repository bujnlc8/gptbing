import {
  doRequest,
  SERVER_WSS_HOST
} from "../../config"

const systemInfo = wx.getSystemInfoSync()
// 各平台对话分离
const sid_prefix = systemInfo.platform == "ios" || systemInfo.platform == "android" ? "" : systemInfo.platform
const initHeight = inputPop() ? 20 : 5
// 是否使用websocket请求
var useWebsocket = true
try {
  var notuseWebsocket = wx.getStorageSync("notuseWebsocket")
  if (notuseWebsocket) {
    useWebsocket = false
  }
} catch (e) {
  useWebsocket = true
}

function inputPop() {
  return systemInfo.platform == "ios" || systemInfo.platform == "android"
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
  }
  if (/(y+)/.test(fmt)) {
    fmt = fmt.replace(
      RegExp.$1,
      (this.getFullYear() + "").substr(4 - RegExp.$1.length)
    )
  }
  for (var k in o) {
    if (new RegExp("(" + k + ")").test(fmt)) {
      fmt = fmt.replace(
        RegExp.$1,
        RegExp.$1.length == 1 ? o[k] : ("00" + o[k]).substr(("" + o[k]).length)
      )
    }
  }
  return fmt
}

function getNow() {
  return new Date().format("yyyy-MM-dd hh:mm:ss")
}

const app = getApp()
const robAvatar = "../../image/bing-avatar.png"
const personAvatar = "../../image/person.jpeg"

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
  },
  inputFocus(e) {
    if (inputPop()) {
      this.setData({
        inputBottom: e.detail.height,
      })
    }
  },
  inputBlur(e) {
    this.setData({
      inputBottom: initHeight,
      textareaFocus: false,
    })
  },
  processContent(content) {
    return content.replace(/\\n/g, "\n").replace(/\[\^\d+\^\]/g, "")
  },
  resetConversation: function (callback) {
    app.getSid(sid => {
      doRequest("/reset", "GET", {
        sid: sid_prefix + sid,
      }).then(res => {
        if (callback) {
          callback(res)
        }
      })
    })
  },
  onShow() {
    const cht = app.globalData.cht
    if (cht.data.chatList.length > 1) {
      cht.setData({
        scrollId: "item" + (cht.data.chatList.length - 2),
      })
    }
  },
  onLoad() {},
  processData: function (data, suggests, content) {
    var robContent = data["data"]["status"]
    if (robContent == "Success") {
      robContent = data["data"]["text"]
      suggests.push(...data["data"]["suggests"])
      if (robContent.indexOf("New topic") != -1) {
        robContent += "\n发送“重新对话！”开始新的对话"
        suggests.push("重新对话！")
        suggests.push(content)
      }
    } else {
      if (robContent == "Throttled") {
        robContent = "这真是愉快，但你已达到每日限制。是否明天再聊？"
        suggests.push("重新对话！")
        suggests.push(content)
      } else {
        var msg = data["data"]["message"]
        if (msg.indexOf("has expired") != -1) {
          this.resetConversation()
          robContent = "本轮对话已过期，请重新开始。"
          suggests.push(content)
        } else {
          robContent = "抱歉😭，发生错误：" + msg
          suggests.push("重新对话！")
          suggests.push(content)
        }
      }
    }
    return robContent
  },
  sendWSRequest: function (content) {
    var that = this
    app.getSid(sid => {
      that.sendSocketMessage({
        "q": content,
        "sid": sid_prefix + sid,
        "t": new Date().getTime()
      })
    })
  },
  sendHttpRequest: function (content) {
    var that = this
    const cht = app.globalData.cht
    app.getSid(sid => {
      doRequest("/chat", "POST", {
        q: content,
        sid: sid_prefix + sid,
      }).then(res => {
        try {
          var robContent = ""
          var suggests = []
          var num_in_conversation = -1
          if (res.statusCode != 200) {
            robContent =
              "抱歉😭，网络异常，请稍后重试 [" + res.statusCode + "]"
            suggests.push(content)
          } else {
            robContent = that.processData(res.data, suggests, content)
            num_in_conversation = res.data["data"]["num_in_conversation"]
          }
          that.pushStorageMessage(cht, robContent, "rob", suggests, false, true, num_in_conversation)
        } catch (error) {
          wx.showToast({
            title: "fatal error",
            icon: "error"
          })
          that.pushStorageMessage(cht, "发生致命错误😱", "rob", [], false, true)
        }
      }).catch(e => {
        that.pushStorageMessage(cht, e.errMsg, "rob", [], false, true)
      })
    })
  },
  submitContent: function (content) {
    if (this.data.searching) {
      wx.showToast({
        title: "请等待完成",
        icon: "error"
      })
      return
    } else {
      this.setData({
        searching: true
      })
    }
    var that = this
    const cht = app.globalData.cht
    that.pushStorageMessage(cht, content, "man", [], false)
    that.setData({
      content: "",
      lastContent: content,
    })
    if (content == "重新对话！") {
      that.resetConversation(() => {
        that.pushStorageMessage(cht, "现在我们可以开始新的对话😊", "rob", [], false)
      })
      return
    } else {
      that.pushStorageMessage(cht, "搜索中🔍...", "rob", [], true)
    }
    if (that.data.useWebsocket) {
      that.sendWSRequest(content)
    } else {
      that.sendHttpRequest(content)
    }
  },
  pushStorageMessage: function (cht, content, role, suggests, blink, pop, num_in_conversation = -1, final = true) {
    if (pop) {
      cht.data.chatList.pop()
    }
    cht.data.chatList.push({
      type: role,
      avatarUrl: role == "rob" ? robAvatar : personAvatar,
      dt: getNow(),
      originContent: this.processContent(content),
      suggests: suggests,
      blink: blink,
      num_in_conversation: num_in_conversation,
    })
    cht.setData({
      chatList: cht.data.chatList,
    })
    if (role == "rob" && !blink && final) {
      this.setData({
        searching: false
      })
    }
    wx.setStorage({
      key: "chatList",
      data: cht.data.chatList,
    })
    setTimeout(() => {
      cht.setData({
        scrollId: "item" + (cht.data.chatList.length + "9999"),
      })
    }, 50)
  },
  submit() {
    var content = this.data.content
    if (content.length == 0 || content.trim().length == 0) {
      return
    }
    this.submitContent(content)
  },
  onShareAppMessage() {
    return {
      title: "New Bing Bot 🤖",
      path: "/pages/index/index",
      imageUrl: "../../image/newBing.png"
    }
  },
  onSuggestSubmit: function (e) {
    var suggest = e.detail.suggest
    this.submitContent(suggest)
  },
  focus: function (e) {
    this.setData({
      textareaFocus: true
    })
  },
  openSocket(callback) {
    if (this.data.socket.isOpen) {
      return
    }
    var that = this
    const cht = app.globalData.cht
    const socket = wx.connectSocket({
      url: SERVER_WSS_HOST + "/chat",
      fail: function () {
        wx.showToast({
          title: "打开websocket失败",
          icon: "none",
        })
      }
    })
    socket.onOpen(() => {
      console.log("Socket onOpen", socket)
      if (socket.readyState == 1) {
        that.setData({
          socket: {
            socket: socket,
            isOpen: true
          }
        })
        setTimeout(() => {
          if (callback) {
            callback()
          }
        }, 50)
      }
    })
    socket.onClose((code, reason) => {
      console.log("Socket onClose", code, reason)
      that.setData({
        socket: {
          socket: null,
          isOpen: false
        },
        searching: false,
      })
      cht.setData({
        receiveData: false
      })
    })
    socket.onError(msg => {
      console.log("Socket onError", msg)
      that.setData({
        socket: {
          socket: null,
          isOpen: false
        },
        searching: false
      })
      wx.showToast({
        title: "网络异常 " + msg.errMsg,
        icon: "none",
      })
      cht.setData({
        receiveData: false
      })
    })
    socket.onMessage(data => {
      const cht = app.globalData.cht
      var data = JSON.parse(data.data)
      var suggests = []
      var robContent = ""
      var num_in_conversation = -1
      if (!data["final"]) {
        robContent = data["data"] + " ..."
        cht.setData({
          receiveData: true
        })
      } else {
        robContent = that.processData(data["data"], suggests, that.data.lastContent)
        num_in_conversation = data["data"]["data"]["num_in_conversation"]
        cht.setData({
          receiveData: false
        })
      }
      that.pushStorageMessage(cht, robContent, "rob", suggests, false, true, num_in_conversation, data["final"])
    })
  },
  sendSocketMessage: function (data) {
    if (!this.data.socket.isOpen) {
      this.openSocket(() => {
        this.data.socket.socket.send({
          data: JSON.stringify(data),
          fail: err => {
            console.log(err)
            wx.showToast({
              title: "消息发送失败",
              icon: "error",
            })
          }
        })
      })
    } else {
      this.data.socket.socket.send({
        data: JSON.stringify(data),
        fail: err => {
          console.log(err)
          wx.showToast({
            title: "消息发送失败",
            icon: "error",
          })
        }
      })
    }
  },
  onUnload: function () {
    if (this.data.socket.isOpen) {
      this.data.socket.socket.close({
        code: 1000,
        reason: "Page Unload"
      })
    }
  },
  inputData: function (e) {
    var that = this
    var value = e.detail.value
    that.setData({
      content: value
    })
    // 特定用户在桌面版本下触发提交，因为textarea在桌面版下回车是换行，并且无法监听快捷键输入，只能出此下策
    if (systemInfo.platform != "windows" && systemInfo.platform != "mac") {
      return
    }
    if (value.indexOf("》》》\n") != -1 || value.indexOf(">>>\n") != -1) {
      that.setData({
        content: value.replace("》》》\n", "").replace(">>>\n", ""),
      }, () => {
        that.submit()
      })
    }
  },
  onCancelReceive: function (e) {
    if (this.data.socket.isOpen) {
      this.data.socket.socket.close({
        code: 1000,
        reason: "User cancel"
      })
    }
  },
  swithRequestMethod: function (e) {
    var that = this
    if (this.data.useWebsocket) {
      wx.setStorage({
        key: "notuseWebsocket",
        data: 1,
        success: (res) => {
          that.setData({
            useWebsocket: false
          })
          wx.showToast({
            title: "已切换成Https接口",
            icon: "none"
          })
        }
      })
    } else {
      wx.removeStorage({
        key: "notuseWebsocket",
        success: (res) => {
          that.setData({
            useWebsocket: true
          })
          wx.showToast({
            title: "已切换成Websocket接口",
            icon: "none"
          })
        }
      })
    }
  }
})
