package handlers

import (
	"log"
	"strings"

	"github.com/bujnlc8/wechatbot/gpt"
	"github.com/eatmoreapple/openwechat"
)

var _ MessageHandlerInterface = (*UserMessageHandler)(nil)

// UserMessageHandler 私聊消息处理
type UserMessageHandler struct {
}

// handle 处理消息
func (g *UserMessageHandler) handle(msg *openwechat.Message) error {
	if msg.IsText() {
		return g.ReplyText(msg)
	}
	if msg.IsSendByFriend() {
		msg.ReplyText("目前我只支持文字哦~")
	}
	if msg.IsPaiYiPai() {
		msg.ReplyText("我是机器人🤖️，会拍坏的哦~")
	}
	return nil
}

// NewUserMessageHandler 创建私聊处理器
func NewUserMessageHandler() MessageHandlerInterface {
	return &UserMessageHandler{}
}

// ReplyText 发送文本消息到群
func (g *UserMessageHandler) ReplyText(msg *openwechat.Message) error {
	// 接收私聊消息
	sender, err := msg.Sender()
	log.Printf("Received User %v Text Msg : %v", sender.UserName, msg.Content)

	requestText := strings.TrimSpace(msg.Content)
	requestText = strings.Trim(msg.Content, "\n")

	var reply = ""
	if strings.Contains(msg.Content, "@bing") {
		requestText = strings.TrimSpace(strings.ReplaceAll(msg.Content, "@bing", ""))
		reply, err = gpt.BingSearch(requestText, sender.UserName)
	} else {
		reply, err = gpt.Completions(requestText, sender.UserName)
	}
	if err != nil {
		log.Printf("gpt request error: %v \n", err)
		msg.ReplyText("机器人神了，我一会发现了就去修。")
		return err
	}
	if reply == "" {
		msg.ReplyText("机器人响应为空")
		return nil
	}

	// 回复用户
	reply = strings.TrimSpace(reply)
	reply = strings.Trim(reply, "\n")
	_, err = msg.ReplyText(reply)
	if err != nil {
		log.Printf("response user error: %v \n", err)
	}
	return err
}
