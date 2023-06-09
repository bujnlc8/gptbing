const app = getApp();

import { doRequest, sidPrefix, systemInfo, cacheChatNum } from "../../config";

var closeShareOnCopy = false;
try {
  if (wx.getStorageSync("closeShareOnCopy")) {
    closeShareOnCopy = true;
  }
} catch (e) {
  closeShareOnCopy = false;
}

Component({
  options: {
    addGlobalClass: true,
    multipleSlots: true,
  },
  properties: {
    chatType: {
      type: String,
      value: "bing",
    },
    mode: {
      type: String,
      value: "normal",
    },
    showPrevBt: {
      type: Boolean,
      value: false,
    },
    loadData: {
      type: Boolean,
      value: true,
    },
  },
  pageLifetimes: {
    show: function () {
      this.initMessageHistory();
      if (this.data.mode != "normal") {
        this.setData({
          height: systemInfo.windowHeight - 15,
        });
      } else {
        this.setData({
          height:
            systemInfo.windowHeight - (systemInfo.platform == "ios" ? 75 : 65),
        });
      }
    },
  },
  lifetimes: {
    attached() {
      //this.initMessageHistory()
    },
    detached() {
      try {
      } catch (error) {}
    },
  },
  data: {
    chatList: [],
    receiveData: false,
    autoIncrConversation: 1,
    closeShareOnCopy: closeShareOnCopy,
    showShare: false,
    shareContent: "",
    loadingData: false,
    systemInfo: systemInfo,
    height: systemInfo.windowHeight - (systemInfo.platform == "ios" ? 75 : 65),
  },
  methods: {
    bindscrolltoupper: function (e) {
      var that = this;
      if (that.data.loadingData) {
        return;
      }
      that.setData({
        loadingData: true,
      });
      wx.showLoading({
        title: "加载记录...",
      });
      app.getSid((sid) => {
        var page = 1;
        if (that.data.chatList.length > 0) {
          page = Math.ceil((that.data.chatList.length + 1) / 10);
        }
        doRequest(
          this.data.mode == "normal" ? "/query" : "/collect_query",
          "GET",
          {
            sid: sidPrefix + sid,
            page: page,
            size: 10,
          }
        )
          .then((res) => {
            var data = res.data["data"];
            data.reverse();
            var oldData = that.data.chatList;
            var filterData = [];
            if (that.data.mode == "normal") {
              if (oldData.length > 0) {
                data.forEach((k) => {
                  if (k["dt"] < oldData[0]["dt"]) {
                    filterData.push(k);
                  }
                });
              } else {
                filterData = data;
              }
            } else {
              data.forEach((k) => {
                var exist = false;
                for (var i = 0; i < oldData.length; i++) {
                  if (
                    k &&
                    k["dt"] == oldData[i]["dt"] &&
                    k["originContent"] == oldData[i]["originContent"]
                  ) {
                    exist = true;
                    break;
                  }
                }
                if (!exist) {
                  filterData.push(k);
                }
              });
            }
            var newData = filterData.concat(oldData);
            that.setData(
              {
                chatList: newData,
                loadingData: false,
              },
              () => {
                if (
                  oldData.length < cacheChatNum &&
                  that.data.mode == "normal"
                ) {
                  wx.setStorage({
                    key: "chatList",
                    data: newData.slice(-cacheChatNum),
                  });
                }
                if (filterData.length == 0 && e) {
                  setTimeout(() => {
                    wx.showToast({
                      title: "已全部加载完成",
                    });
                  }, 100);
                } else {
                  setTimeout(() => {
                    wx.hideLoading();
                  }, 100);
                }
              }
            );
          })
          .catch((res) => {
            wx.hideLoading();
            console.log(res);
          });
      });
    },
    initMessageHistory() {
      if (!this.data.loadData) {
        return;
      }
      var that = this;
      wx.getStorage({
        key: that.data.mode == "normal" ? "chatList" : "chatListCollected",
        success: function (res) {
          var data = res.data;
          data = data ? data : [];
          if (data.length > 0) {
            that.setData({
              chatList: data,
            });
          } else {
            that.bindscrolltoupper();
          }
        },
        fail: function () {
          that.bindscrolltoupper();
        },
      });
    },
    clearChat: function (e) {
      if (this.data.mode != "normal") {
        return;
      }
      var that = this;
      var index = e.currentTarget.dataset.index;
      var data = this.data.chatList;
      wx.showModal({
        content: "是否清除该条聊天？",
        complete: (res) => {
          if (res.confirm) {
            var deleteData = data[index];
            app.getSid((sid) => {
              doRequest("/delete", "POST", {
                sid: sidPrefix + sid,
                conversation: deleteData,
              }).then((res) => {
                if (
                  res.data.num < 1 &&
                  deleteData["originContent"] != "搜索中🔍..."
                ) {
                  return;
                }
                data.splice(index, 1);
                that.setData({
                  chatList: data,
                });
                wx.setStorage({
                  key: "chatList",
                  data: data.slice(data.length - cacheChatNum),
                });
              });
            });
          }
        },
      });
    },
    copyRenderedContentToClipBoard: function (index) {
      var ctx = this.selectComponent("#mp_html_" + index);
      if (!ctx) {
        wx.showToast({
          title: "复制出错",
        });
        return;
      }
      wx.setClipboardData({
        data: ctx.getText(),
        success: function () {
          wx.showToast({
            title: "复制成功",
          });
        },
      });
    },
    copyContentToClipBoard: function (content, index) {
      if (!content) {
        return;
      }
      var that = this;
      wx.setClipboardData({
        data: content,
        success: function () {
          wx.showToast({
            title: "复制成功",
          });
          if (
            that.data.chatList[index]["type"] == "man" &&
            !that.data.closeShareOnCopy &&
            that.data.mode == "normal"
          ) {
            var shareContent = content;
            if (shareContent.length > 8) {
              shareContent = shareContent.substr(0, 8) + "...";
            }
            setTimeout(() => {
              that.setData({
                showShare: true,
                shareContent: shareContent,
              });
              wx.setStorage({
                key: "shareContent",
                data: {
                  q: content,
                  validTime: new Date().getTime() + 300 * 1000,
                },
              });
            }, 1200);
          }
        },
      });
    },
    copyContent: function (e) {
      var index = e.currentTarget.dataset.index;
      var content = this.data.chatList[index].originContent;
      var that = this;
      var items = ["复制内容", "发送至Flomo", "发送至Memos", "发送至为知笔记"];
      var title = "";
      if (that.data.chatList[index]["type"] != "man") {
        items.push("Copy as plain text");
        title =
          that.data.chatList[index - 1]["originContent"].substr(0, 16) + ".md";
      } else {
        title =
          that.data.chatList[index]["originContent"].substr(0, 16) + ".md";
      }
      wx.showActionSheet({
        itemList: items,
        success: function (res) {
          if (res.tapIndex == 0) {
            that.copyContentToClipBoard(content, index);
          } else if (
            res.tapIndex == 1 ||
            res.tapIndex == 2 ||
            res.tapIndex == 3
          ) {
            var app_type = 0;
            if (res.tapIndex == 1) {
              app_type = 1;
            } else if (res.tapIndex == 3) {
              app_type = 2;
            }
            var cache_key = "memos_openapi";
            if (app_type == 1) {
              cache_key = "flomo_api";
            } else if (app_type == 2) {
              cache_key = "wiz_api";
            }
            wx.getStorage({
              key: cache_key,
              success: function (res) {
                wx.showLoading({
                  title: "发送中...",
                });
                app.getSid((sid) => {
                  doRequest("/share", "POST", {
                    url: res.data,
                    content: content,
                    sid: sid,
                    app_type: app_type,
                    title: title,
                  })
                    .then((res) => {
                      if (res.data.sent == 1) {
                        wx.showToast({
                          title: "发送成功",
                          icon: "none",
                        });
                      } else {
                        wx.showToast({
                          title: "发送失败",
                          icon: "none",
                        });
                      }
                    })
                    .catch((e) => {
                      wx.showToast({
                        title: "发送失败:" + e.errMsg,
                        icon: "none",
                      });
                    });
                });
              },
              fail: function (e) {
                wx.showToast({
                  title: "请先设置API地址",
                  icon: "none",
                });
              },
            });
          } else if (res.tapIndex == 4) {
            that.copyRenderedContentToClipBoard(index);
          }
        },
      });
    },
    renderMd: function (e) {
      var index = e.currentTarget.dataset.index;
      var data = this.data.chatList[index];
      var content = data.originContent;
      if (!this.data.chatList[index].content) {
        var matches = content.match(/```markdown[\s\S]*```/g);
        if (null == matches) {
          matches = content.match(/```markdown[\s\S]*/g);
        }
        if (null != matches) {
          matches.forEach((m) => {
            var m1 = m.replace("```markdown", "").trim();
            if (m1.endsWith("```")) {
              m1 = m1.substring(0, m1.length - 3);
            }
            content = content.replace(m, m1);
          });
        }
        data.content = content;
      } else {
        data.content = null;
      }
      this.setData({
        chatList: this.data.chatList,
      });
    },
    suggestSubmit: function (e) {
      if (this.data.mode != "normal") {
        return;
      }
      var suggest = e.currentTarget.dataset.suggest;
      this.triggerEvent(
        "suggestSubmit",
        {
          suggest,
        },
        {}
      );
    },
    cancelReceive: function () {
      this.triggerEvent("cancelReceive", {}, {});
    },
    showOriginContent: function (e) {
      var index = e.currentTarget.dataset.index;
      var data = this.data.chatList[index];
      if (data.showOrigin) {
        data.showOrigin = null;
      } else {
        data.showOrigin = true;
      }
      this.setData({
        chatList: this.data.chatList,
      });
    },
    onPopButtonClick: function (e) {
      if (e.detail.t !== "confirm") {
        wx.removeStorage({
          key: "shareContent",
        });
        wx.showToast({
          title: "可在设置中关闭分享",
          icon: "none",
        });
      }
      this.setData({
        showShare: false,
      });
    },
    operateCollect: function (e) {
      var index = e.currentTarget.dataset.index;
      var that = this;
      var data = this.data.chatList[index];
      var operateType = 1;
      if (data["collected"]) {
        data["collected"] = false;
        operateType = 0;
      } else {
        data["collected"] = true;
      }
      app.getSid((sid) => {
        doRequest("/collect", "POST", {
          sid: sidPrefix + sid,
          conversation: data,
          operate_type: operateType,
        }).then((res) => {
          that.setData({
            chatList: that.data.chatList,
          });
          if (!data["collected"]) {
            wx.showToast({
              title: "取消成功",
              icon: "none",
            });
          } else {
            wx.showToast({
              title: "收藏成功",
              icon: "none",
            });
          }
          if (that.data.mode == "normal") {
            wx.setStorage({
              key: "chatList",
              data: that.data.chatList.slice(
                that.data.chatList.length - cacheChatNum
              ),
            });
          } else {
            wx.getStorage({
              key: "chatList",
              success(res) {
                var cached = res["data"];
                cached.forEach((k) => {
                  if (
                    k["dt"] == data["dt"] &&
                    k["originContent"] == data["originContent"]
                  ) {
                    k["collected"] = data["collected"];
                  }
                });
                wx.setStorage({
                  key: "chatList",
                  data: cached,
                });
              },
            });
            if (!data["collected"]) {
              var oldData = that.data.chatList;
              oldData.forEach((k, v) => {
                if (
                  k["dt"] == data["dt"] &&
                  k["originContent"] == data["originContent"]
                ) {
                  oldData.splice(v, 1);
                }
              });
              that.setData({
                chatList: oldData,
              });
            }
          }
        });
      });
    },
  },
});
