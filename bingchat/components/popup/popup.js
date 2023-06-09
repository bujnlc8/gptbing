// components/popup/popup.js
Component({
  /**
   * 组件的属性列表
   */
  properties: {
    message: String,
    openType: {
      type: String,
      value: "",
    },
    title: {
      type: String,
      value: "提示",
    },
    cancelText: {
      type: String,
      value: "取消",
    },
    confirmText: {
      type: String,
      value: "确定",
    },
  },

  /**
   * 组件的初始数据
   */
  data: {},

  /**
   * 组件的方法列表
   */
  methods: {
    closePop: function (e) {
      this.triggerEvent(
        "PopButtonClick",
        {
          t: e.currentTarget.dataset.t,
        },
        {}
      );
    },
  },
});
