const app = getApp()

var closeShareOnCopy = false
try {
  if (wx.getStorageSync("closeShareOnCopy")) {
    closeShareOnCopy = true
  }
} catch (e) {
  closeShareOnCopy = false
}

Component({
  options: {
    addGlobalClass: true,
    multipleSlots: true,
  },
  properties: {
    chatType: {
      type: String,
      value: "bing"
    }
  },
  pageLifetimes: {
    show: function () {
      this.initMessageHistory()
    },
  },
  lifetimes: {
    attached() {
      var that = this
      app.globalData.cht = that
      //that.initMessageHistory()
      wx.getSystemInfo({
        success: function (res) {
          that.setData({
            systemInfo: res,
          })
        },
      })
    },
    detached() {
      try {} catch (error) {}
    },
  },
  data: {
    chatList: [],
    receiveData: false,
    autoIncrConversation: 1,
    closeShareOnCopy: closeShareOnCopy,
    showShare: false,
  },
  methods: {
    initMessageHistory() {
      var that = this
      var data = wx.getStorageSync("chatList")
      data = data ? data : []
      data.forEach((v) => {
        if (v["suggests"] === undefined) {
          v["suggests"] = []
        }
      })
      if (data.length > 0) {
        that.setData({
          chatList: data,
        })
      }
    },
    clearChat: function (e) {
      var that = this
      var index = e.currentTarget.dataset.index
      var data = this.data.chatList
      wx.showModal({
        content: "是否删除该条聊天？",
        complete: (res) => {
          if (res.confirm) {
            data.splice(index, 1)
            that.setData({
              chatList: data,
            })
            wx.setStorage({
              key: "chatList",
              data: data,
            })
          }
        },
      })
    },
    copyContent: function (e) {
      var index = e.currentTarget.dataset.index
      var that = this
      var content = this.data.chatList[index].originContent
      wx.setClipboardData({
        data: content,
        success: function () {
          wx.showToast({
            title: "复制成功",
          })
          if (that.data.chatList[index]["type"] == "man" && !that.data.closeShareOnCopy) {
            setTimeout(() => {
              that.setData({
                showShare: true
              })
              wx.setStorage({
                key: "shareContent",
                data: {
                  q: content,
                  validTime: new Date().getTime() + 300 * 1000
                }
              })
            }, 1200)
          }
        }
      })
    },
    renderMd: function (e) {
      var index = e.currentTarget.dataset.index
      var data = this.data.chatList[index]
      var content = data.originContent
      if (!this.data.chatList[index].content) {
        var matches = content.match(/```markdown[\s\S]*```/g)
        if (null == matches) {
          matches = content.match(/```markdown[\s\S]*/g)
        }
        if (null != matches) {
          matches.forEach(m => {
            var m1 = m.replace("```markdown", "").trim()
            if (m1.endsWith("```")) {
              m1 = m1.substring(0, m1.length - 3)
            }
            content = content.replace(m, m1)
          })
        }
        data.content = content
      } else {
        data.content = null
      }
      this.setData({
        chatList: this.data.chatList
      })
    },
    suggestSubmit: function (e) {
      var suggest = e.currentTarget.dataset.suggest
      this.triggerEvent(
        "suggestSubmit", {
          suggest,
        }, {}
      )
    },
    cancelReceive: function () {
      this.triggerEvent(
        "cancelReceive", {}, {}
      )
    },
    showOriginContent: function (e) {
      var index = e.currentTarget.dataset.index
      var data = this.data.chatList[index]
      if (data.showOrigin) {
        data.showOrigin = null
      } else {
        data.showOrigin = true
      }
      this.setData({
        chatList: this.data.chatList
      })
    },
    onPopButtonClick: function (e) {
      if (e.detail.t !== "confirm") {
        wx.removeStorage({
          key: "shareContent",
        })
      }
      this.setData({
        showShare: false
      })
    }
  },
})
