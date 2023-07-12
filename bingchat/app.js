import { doRequest, sidPrefix } from "./config";

App({
  onShow: function () {},
  onLaunch: function () {
    var that = this;
    wx.getStorage({
      key: "selectedChatType",
      success: (res) => {
        that.globalData.chatType = res.data;
      },
    });
    if (that.globalData.sid) {
      that.upload_cache_conversation(that.globalData.sid);
      doRequest("/channel", "GET", { sid: that.globalData.sid }).then((res) => {
        that.globalData.channel = res.data.data;
      });
    } else {
      wx.getStorage({
        key: "sid1",
        success: (res) => {
          that.upload_cache_conversation(res.data);
          doRequest("/channel", "GET", { sid: res.data }).then((res) => {
            that.globalData.channel = res.data.data;
          });
        },
      });
    }
  },
  onHide: function () {
    // this.upload_conversation()
  },
  globalData: {
    chatType: "bing",
    channel: [{ name: "New Bing", value: "bing" }],
  },
  upload_cache_conversation: function (sid) {
    var that = this;
    wx.getStorage({
      key: "chatList",
      success: function (res) {
        var data = res.data || [];
        data = data.slice(-5);
        doRequest("/save", "POST", {
          sid: sidPrefix + sid,
          conversations: data,
        }).then((res) => {
          that.globalData["channel"] = res.data["channel"];
          console.log("upload " + data.length + " conversations success!");
        });
      },
    });
  },
  upload_conversation: function (conversations = []) {
    var that = this;
    if (conversations.length == 0) {
      that.getSid((sid) => {
        that.upload_cache_conversation(sid);
      });
    } else {
      that.getSid((sid) => {
        doRequest("/save", "POST", {
          sid: sidPrefix + sid,
          conversations: conversations,
        }).then((res) => {
          that.globalData["channel"] = res.data["channel"];
          console.log(
            "upload " + conversations.length + " conversations success!"
          );
        });
      });
    }
  },
  getSid: function (callback) {
    var that = this;
    if (!this.globalData.sid) {
      var sid = wx.getStorageSync("sid1");
      if (!sid) {
        wx.login({
          success: (res) => {
            doRequest("/openid", "GET", {
              code: res.code,
            })
              .then((data) => {
                if (data.statusCode != 200) {
                  callback("anonymous");
                  return;
                }
                that.globalData.sid = data.data.data.openid;
                that.globalData.channel = data.data.data.channel;
                wx.setStorageSync("sid1", that.globalData.sid);
                callback(data.data.data.openid);
              })
              .catch((err) => {
                console.log(err);
                callback("");
              });
          },
        });
      } else {
        this.globalData.sid = sid;
        wx.setStorageSync("sid1", this.globalData.sid);
        callback(sid);
      }
    } else {
      callback(this.globalData.sid);
    }
  },
});
