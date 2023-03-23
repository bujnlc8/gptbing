package gpt

import (
	"bytes"
	"encoding/json"
	"io/ioutil"
	"log"
	"net/http"
	"strings"

	"github.com/bujnlc8/wechatbot/config"
)

const Referer = "https://servicewechat.com/wxee7496be5b68b740"

type BingQueryParam struct {
	Q         string `json:"q"`
	SID       string `json:"sid"`
	AutoReset string `json:"auto_reset"`
}

type BingResponse struct {
	Data   BingResponseData `json:"data"`
	Cookie string           `json:"cookie"`
}

type BingResponseData struct {
	Suggests []string `json:"suggests"`
	Status   string   `json:"status"`
	Text     string   `json:"text"`
	Message  string   `json:"message"`
}

func BingSearch(msg string, nickName string) (string, error) {
	requestBody := BingQueryParam{
		Q:         msg,
		SID:       nickName,
		AutoReset: "1",
	}
	requestData, err := json.Marshal(requestBody)

	if err != nil {
		return "", err
	}
	log.Printf("request bing json string : %v", string(requestData))
	BingChatUrl := config.LoadConfig().BingChatUrl
	req, err := http.NewRequest("POST", BingChatUrl, bytes.NewBuffer(requestData))
	if err != nil {
		return "", err
	}
        req.Header.Set("Referer", Referer)
	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{}
	response, err := client.Do(req)
	if err != nil {
		return "非常抱歉😭，网络异常，请稍后重试", err
	}
	if response.StatusCode != 200 {
		return "非常抱歉😭，网络异常，请稍后重试 [" + string(rune(response.StatusCode)) + "]", nil
	}
	defer response.Body.Close()

	body, err := ioutil.ReadAll(response.Body)
	if err != nil {
		return "响应异常，请稍后再试", err
	}

	bingResponse := &BingResponse{}
	log.Println(string(body))
	err = json.Unmarshal(body, bingResponse)
	if err != nil {
		return "", err
	}
	if bingResponse.Data.Status == "Success" {
		if strings.Contains(bingResponse.Data.Text, "New topic") {
			return bingResponse.Data.Text + "\n请重新开始对话", nil
		}
		return bingResponse.Data.Text, nil

	} else {
		if bingResponse.Data.Status == "Throttled" {
			return "这真是愉快，但你已达到每日限制。是否明天再聊？", nil
		} else {
			if strings.Contains(bingResponse.Data.Message, "has expired") {
				return "本轮对话已过期，请重新开始。", nil
			} else {
				return "抱歉😭，发生错误：" + bingResponse.Data.Message + "，请重试", nil
			}
		}
	}
}
