package gpt

import (
	"bytes"
	"encoding/json"
	"io/ioutil"
	"log"
	"net/http"

	"github.com/bujnlc8/wechatbot/config"
)

const BASEURL = "https://api.openai.com/v1/chat/"

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ChatGPTResponseBody 请求体
type ChatGPTResponseBody struct {
	ID      string                 `json:"id"`
	Object  string                 `json:"object"`
	Created int                    `json:"created"`
	Model   string                 `json:"model"`
	Choices []ChoiceItem           `json:"choices"`
	Usage   map[string]interface{} `json:"usage"`
}

type ChoiceItem struct {
	Message      Message `json:"message"`
	FinishReason string  `json:"finish_reason"`
}

// ChatGPTRequestBody 响应体
type ChatGPTRequestBody struct {
	Model       string    `json:"model"`
	MaxTokens   int       `json:"max_tokens"`
	Temperature float32   `json:"temperature"`
	Messages    []Message `json:"messages"`
}

var MessageCacheRegistry = make(map[string][]Message)

func Completions(msg string, nickName string) (string, error) {
	messageCache := MessageCacheRegistry[nickName]
	message := Message{Role: "user", Content: msg}
	if messageCache == nil || len(messageCache) == 0 {
		messageCache = []Message{message}
	} else {
		messageCache = append(messageCache, message)
		// 只保留20条
		if len(messageCache) > 20 {
			messageCache = messageCache[(len(messageCache) - 20):]
		}
	}
	MessageCacheRegistry[nickName] = messageCache
	requestBody := ChatGPTRequestBody{
		Model:       "gpt-3.5-turbo",
		MaxTokens:   2048,
		Temperature: 0.2,
		Messages:    messageCache,
	}
	requestData, err := json.Marshal(requestBody)

	if err != nil {
		return "", err
	}
	log.Printf("request gpt json string : %v", string(requestData))
	req, err := http.NewRequest("POST", BASEURL+"completions", bytes.NewBuffer(requestData))
	if err != nil {
		return "", err
	}

	apiKey := config.LoadConfig().ApiKey
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+apiKey)
	client := &http.Client{}
	response, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer response.Body.Close()

	body, err := ioutil.ReadAll(response.Body)
	if err != nil {
		return "", err
	}
	gptResponseBody := &ChatGPTResponseBody{}
	log.Println(string(body))
	err = json.Unmarshal(body, gptResponseBody)
	if err != nil {
		return "", err
	}
	var reply string
	if len(gptResponseBody.Choices) > 0 {
		for _, v := range gptResponseBody.Choices {
			messageCache = append(messageCache, v.Message)
			MessageCacheRegistry[nickName] = messageCache
			reply = v.Message.Content
			break
		}
	}
	log.Printf("gpt response text: %s \n", reply)
	return reply, nil
}
