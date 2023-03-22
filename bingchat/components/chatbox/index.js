const app = getApp();

Component({
  options: {
    addGlobalClass: true,
    multipleSlots: true,
  },
  properties: {},
  pageLifetimes: {
    show: function () {
      this.initMessageHistory();
    },
  },
  lifetimes: {
    attached() {
      var that = this;
      app.globalData.cht = that;
      //that.initMessageHistory();
      wx.getSystemInfo({
        success: function (res) {
          that.setData({
            systemInfo: res,
          });
        },
      });
    },
    detached() {
      try {
      } catch (error) {}
    },
  },
  data: {
    chatList: [],
  },
  methods: {
    initMessageHistory() {
      var that = this;
      var data = wx.getStorageSync("chatList");
      data = data ? data : [];
      data.forEach((v) => {
        if (v["suggests"] === undefined) {
          v["suggests"] = [];
        }
      });
      if (data.length > 0) {
        that.setData({
          chatList: data,
        });
      }
    },
    clearChat: function (e) {
      var that = this;
      var index = e.currentTarget.dataset.index;
      var data = this.data.chatList;
      wx.showModal({
        content: "是否删除该条记录？",
        complete: (res) => {
          if (res.confirm) {
            data.splice(index, 1);
            that.setData({
              chatList: data,
            });
            wx.setStorage({
              key: "chatList",
              data: data,
            });
          }
        },
      });
    },
    copyContent: function (e) {
      var index = e.currentTarget.dataset.index;
      var content = this.data.chatList[index].originContent;
      wx.setClipboardData({
        data: content,
        success: function () {
          wx.showToast({
            title: "复制成功",
          });
        },
      });
    },
    suggestSubmit: function (e) {
      var suggest = e.currentTarget.dataset.suggest;
      this.triggerEvent(
        "suggestSubmit",
        {
          suggest,
        },
        {}
      );
    },
  },
});
