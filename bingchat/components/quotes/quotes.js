// components/quotes/quotes.js

var urlRe = /\[\d+\]:(\s)?http.*/g

Component({
  /**
   * 组件的属性列表
   */
  properties: {
    content: {
      type: String,
      value: "",
      observer(nv, ov, path) {
        if (nv) {
          var quoteUrls = this.getquoteUrls(nv)
          this.setData({
            quoteUrls: quoteUrls
          })
        } else {
          this.setData({
            quoteUrls: []
          })
        }
      }
    }
  },

  /**
   * 组件的初始数据
   */
  data: {
    quoteUrls: []
  },
  /**
   * 组件的方法列表
   */
  methods: {
    copyUrl: function (e) {
      var url = e.currentTarget.dataset.url
      wx.setClipboardData({
        data: url,
        success: function () {
          wx.showToast({
            title: "链接已复制",
          })
        }
      })
    },
    getquoteUrls: function (content) {
      var quoteUrls = content.match(urlRe)
      if (null == quoteUrls) {
        return []
      }
      var res = []
      quoteUrls.forEach(k => {
        k = k.split(" ")
        var i = k[0].match(/\[(\d+)\]/)[1]
        var url = k[1]
        var host = url.split("/").splice(0, 3).join("/")
        var title = k.slice(2).join("").replaceAll('"', "").replaceAll('\\', '')
        res.push({
          i,
          url,
          host,
          title
        })
      })
      return res
    }
  }
})
