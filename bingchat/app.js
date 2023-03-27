import {
  doRequest
} from "./config"

App({
  onShow: function () {},
  onLaunch: function () {
    this.getSid(sid => {
      console.log(sid)
    })
  },
  globalData: {},
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
