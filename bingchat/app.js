import {
  doRequest,
  sidPrefix
} from "./config"

App({
  onShow: function () {},
  onLaunch: function () {
    this.getSid(sid => {
      console.log(sid)
    })
    this.upload_conversation()
  },
  onHide: function () {
    this.upload_conversation()
  },
  globalData: {},
  upload_cache_conversation: function (sid) {
    var that = this
    wx.getStorage({
      key: "chatList",
      success: function (res) {
        var data = res.data
        if (data && data.length > 0) {
          data = data.slice(-5)
          doRequest("/save", "POST", {
            "sid": sidPrefix + sid,
            "conversations": data
          }).then(res => {
            that.globalData["saved"] = res.data["saved"]
            console.log("upload " + data.length + " conversations success!")
          })
        }
      }
    })
  },
  upload_conversation: function (conversations = []) {
    var that = this
    if (conversations.length == 0) {
      that.getSid(sid => {
        that.upload_cache_conversation(sid)
      })
    } else {
      that.getSid(sid => {
        doRequest("/save", "POST", {
          "sid": sidPrefix + sid,
          "conversations": conversations,
        }).then(res => {
          console.log("upload " + conversations.length + " conversations success!")
        })
      })
    }
  },
  getSid: function (callback) {
    var that = this
    if (!this.globalData.sid) {
      var sid = wx.getStorageSync("sid1")
      if (!sid) {
        wx.login({
          success: (res) => {
            doRequest("/openid", "GET", {
              code: res.code
            }).then(data => {
              if (data.statusCode != 200) {
                console.log(data)
                callback("")
                return
              }
              that.globalData.sid = data.data.data.openid
              wx.setStorageSync("sid1", that.globalData.sid)
              callback(data.data.data.openid)
            }).catch(err => {
              console.log(err)
              callback("")
            })
          },
        })
      } else {
        this.globalData.sid = sid
        wx.setStorageSync("sid1", this.globalData.sid)
        callback(sid)
      }
    } else {
      callback(this.globalData.sid)
    }
  },
})
