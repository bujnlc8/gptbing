import SERVER_HOST from '../../config';

App({
  onShow: function () {},
  onLaunch: function () {
    this.getSid();
  },
  globalData: {},
  getSid: function () {
    var that = this;
    if (!this.globalData.sid) {
      var sid = wx.getStorageSync('sid1');
      if (!sid) {
        wx.login({
          success: (res) => {
            wx.request({
              url: SERVER_HOST + '/bing/openid',
              data: {
                code: res.code,
              },
              success: (res) => {
                that.globalData.sid = res.data.data.openid;
                wx.setStorageSync('sid1', that.globalData.sid);
              },
            });
          },
        });
      } else {
        this.globalData.sid = sid;
        wx.setStorageSync('sid1', this.globalData.sid);
      }
    }
    return this.globalData.sid ? this.globalData.sid : '';
  },
});
