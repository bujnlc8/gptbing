const app = getApp();

import {
	doRequest,
	sidPrefix,
	systemInfo,
	cacheChatNum
} from "../../config";

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
			}
		},
	},
	lifetimes: {
		attached() {
			//this.initMessageHistory()
		},
		detached() {
			try {} catch (error) {}
		},
	},
	data: {
		chatList: [],
		receiveData: false,
		autoIncrConversation: 1,
		closeShareOnCopy: closeShareOnCopy,
		showShare: false,
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
						"GET", {
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
						that.setData({
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
				content: "是否删除该条聊天？",
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
		copyContentToClipBoard: function (content, index) {
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
						setTimeout(() => {
							that.setData({
								showShare: true,
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
			wx.showActionSheet({
				itemList: ["复制内容", "发送至Memos"],
				success: function (res) {
					if (res.tapIndex == 0) {
						that.copyContentToClipBoard(content, index);
					} else if (res.tapIndex == 1) {
						wx.getStorage({
							key: "memos_openapi",
							success: function (res) {
								app.getSid((sid) => {
									doRequest("/share", "POST", {
											url: res.data,
											content: content,
											sid: sid,
										})
										.then((res) => {
											console.log(res);
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
									title: "请先设置Memos的OpenAPI地址",
									icon: "none",
								});
							},
						});
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
				"suggestSubmit", {
					suggest,
				}, {}
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