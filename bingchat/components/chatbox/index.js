const app = getApp()

Component({
  options: {
    addGlobalClass: true,
    multipleSlots: true,
  },
  properties: {},
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
      var content = this.data.chatList[index].originContent
      wx.setClipboardData({
        data: content,
        success: function () {
          wx.showToast({
            title: "复制成功",
          })
        },
      })
    },
    renderMd: function (e) {
      var index = e.currentTarget.dataset.index
      var data = this.data.chatList[index]
      var content = data.originContent
      if (!this.data.chatList[index].content) {
        var matches = content.match(/```markdown[\s\S]*(```)?/g)
        if (null != matches) {
          matches.forEach(m => {
            var m1 = m.replace('```markdown', '')
            if (m1.trim().endsWith('```')) {
              m1 = m1.substring(0, m1.trim().length - 3)
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
    deletAllChat: function (e) {
      var that = this
      wx.showModal({
        content: "是否删除全部聊天？",
        complete: (res) => {
          if (res.confirm) {
            that.setData({
              chatList: [],
            })
            wx.setStorage({
              key: "chatList",
              data: [],
            })
          }
        },
      })
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
    }
  },
})
