package handlers

import (
	"log"
	"strings"

	"github.com/bujnlc8/wechatbot/gpt"
	"github.com/eatmoreapple/openwechat"
)

var _ MessageHandlerInterface = (*GroupMessageHandler)(nil)

// GroupMessageHandler 群消息处理
type GroupMessageHandler struct {
}

// handle 处理消息
func (g *GroupMessageHandler) handle(msg *openwechat.Message) error {
	if msg.IsText() {
		return g.ReplyText(msg)
	} else {
		if strings.Contains(msg.Content, "@GPTBot") || strings.Contains(msg.Content, "@bing") {
			msg.ReplyText("目前我只支持文字哦~")
		}
	}
	if msg.IsPaiYiPai() {
		msg.ReplyText("我是机器人🤖️，会拍坏的哦~")
	}
	return nil
}

// NewGroupMessageHandler 创建群消息处理器
func NewGroupMessageHandler() MessageHandlerInterface {
	return &GroupMessageHandler{}
}

// ReplyText 发送文本消息到群
func (g *GroupMessageHandler) ReplyText(msg *openwechat.Message) error {
	sender, err := msg.Sender()
	group := openwechat.Group{User: sender}
	log.Printf("Received Group %v Text Msg : %v", group.NickName, msg.Content)

	// @GPTBot 或者 @bing的消息才处理
	if !(strings.Contains(msg.Content, "@GPTBot") || strings.Contains(msg.Content, "@bing")) {
		return nil
	}

	requestText := strings.TrimSpace(strings.ReplaceAll(msg.Content, "@GPTBot", ""))
	var reply = ""
	if strings.Contains(msg.Content, "@bing") {
		requestText = strings.TrimSpace(strings.ReplaceAll(msg.Content, "@bing", ""))
		reply, err = gpt.BingSearch(requestText, group.UserName)
		if reply != "" && strings.HasPrefix(reply, "[") {
			reply = "\n" + reply
		}
	} else {
		reply, err = gpt.Completions(requestText, group.UserName)
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

	// 获取@我的用户
	groupSender, err := msg.SenderInGroup()
	if err != nil {
		log.Printf("get sender in group error :%v \n", err)
		return err
	}

	// 回复@我的用户
	reply = strings.TrimSpace(reply)
	reply = strings.Trim(reply, "\n")
	atText := "@" + groupSender.NickName
	replyText := atText + " " + reply
	_, err = msg.ReplyText(replyText)
	if err != nil {
		log.Printf("response group error: %v \n", err)
	}
	return err
}
