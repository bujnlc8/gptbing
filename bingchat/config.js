const SERVER_HOST = "https://example.com";
const SERVER_WSS_HOST = "wss://example.com";

function doRequest(url, method = "GET", data = {}) {
  return new Promise((resolve, reject) => {
    data["t"] = new Date().getTime();
    wx.request({
      url: SERVER_HOST + url,
      method,
      data,
      dataType: "json",
      enableHttp2: true,
      success(res) {
        resolve(res);
      },
      fail(err) {
        reject(err);
      },
    });
  });
}
const systemInfo = wx.getSystemInfoSync();

const sidPrefix =
  systemInfo.platform == "ios" || systemInfo.platform == "android"
    ? ""
    : systemInfo.platform;

// 缓存的对话数量
const cacheChatNum = 300;

export {
  doRequest,
  SERVER_HOST,
  SERVER_WSS_HOST,
  systemInfo,
  sidPrefix,
  cacheChatNum,
};
