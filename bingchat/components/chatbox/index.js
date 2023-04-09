const app = getApp()

import {
  doRequest,
  sidPrefix,
  systemInfo
} from "../../config"

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
      //this.initMessageHistory()
    },
  },
  lifetimes: {
    attached() {
      app.globalData.cht = this
      this.initMessageHistory()
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
    loadingData: false,
    systemInfo: systemInfo,
    height: systemInfo.windowHeight - parseInt(100 / 750 * systemInfo.windowWidth) - ((systemInfo.platform == "ios" || systemInfo.platform == "android") ? 22 : 0)
  },
  methods: {
    bindscrolltoupper: function (e) {
      var that = this
      if (that.data.loadingData) {
        return
      }
      that.setData({
        loadingData: true
      })
      wx.showLoading({
        title: "加载历史记录...",
      })
      app.getSid(sid => {
        var page = 1
        if (that.data.chatList.length > 0) {
          page = Math.ceil((that.data.chatList.length + 1) / 10)
        }
        doRequest("/query", "GET", {
          "sid": sidPrefix + sid,
          "page": page,
          "size": 10,
        }).then(res => {
          var data = res.data["data"]
          data.reverse()
          var oldData = that.data.chatList
          var filterData = []
          if (oldData.length > 0) {
            data.forEach(k => {
              if (k["dt"] < oldData[0]["dt"]) {
                filterData.push(k)
              }
            })
          } else {
            filterData = data
          }
          var newData = filterData.concat(oldData)
          that.setData({
            chatList: newData,
            loadingData: false
          }, () => {
            if (oldData.length < 10) {
              wx.setStorage({
                key: "chatList",
                data: newData.slice(-10),
              })
            }
            if (filterData.length == 0 && e) {
              setTimeout(() => {
                wx.showToast({
                  title: "已全部加载完成"
                })
              }, 100)
            } else {
              setTimeout(() => {
                wx.hideLoading()
              }, 100)
            }
          })
        }).catch(res => {
          wx.hideLoading()
          console.log(res)
        })
      })
    },
    initMessageHistory() {
      var that = this
      wx.getStorage({
        key: "chatList",
        success: function (res) {
          var data = res.data
          data = data ? data : []
          if (data.length > 0) {
            that.setData({
              chatList: data,
            })
          } else {
            that.bindscrolltoupper()
          }
        },
        fail: function () {
          that.bindscrolltoupper()
        }
      })
    },
    clearChat: function (e) {
      var that = this
      var index = e.currentTarget.dataset.index
      var data = this.data.chatList
      wx.showModal({
        content: "是否删除该条聊天？",
        complete: (res) => {
          if (res.confirm) {
            var deleteData = data[index]
            data.splice(index, 1)
            that.setData({
              chatList: data,
            })
            app.getSid(sid => {
              doRequest("/delete", "POST", {
                "sid": sidPrefix + sid,
                "conversation": deleteData
              }).then(res => {
                console.log(res)
                wx.setStorage({
                  key: "chatList",
                  data: data.slice(data.length - 10),
                })
              })
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
