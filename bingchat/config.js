const SERVER_HOST = "https://example.com";

function doRequest(url, method = "GET", data = {}) {
  return new Promise((resolve, reject) => {
    data['t'] = new Date().getTime()
    wx.request({
      url: SERVER_HOST + url,
      method,
      data,
      dataType: "json",
      enableHttp2: true,
      success(res) {
        resolve(res)
      },
      fail(err) {
        reject(err)
      },
    })
  })
}
export {
  doRequest,
  SERVER_HOST
}
