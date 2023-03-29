package utils

import (
	"log"
	"net/smtp"
	"os"
)

const (
	SMTP_SERVER = "smtp.qq.com"
	SMTP_PORT   = "587"
)

// 用qq邮箱发送邮件，从New Bing写的代码修改而来
func SendSimpleEmail(subject string, body string) {
	sender := os.Getenv("EMAIL_SENDER")
	passwd := os.Getenv("EMAIL_PASSWD")
	recipient := os.Getenv("EMAIL_RECIPIENT")
	if len(recipient) == 0 {
		recipient = sender
	}
	auth := smtp.PlainAuth("", sender, passwd, SMTP_SERVER)
	header := make(map[string]string)
	header["To"] = recipient
	header["From"] = sender
	header["Subject"] = subject
	headerStr := ""
	for k, v := range header {
		headerStr += k + ": " + v + "\r\n"
	}
	message := headerStr + "\r\n\r\n" + body
	err := smtp.SendMail(SMTP_SERVER+":"+SMTP_PORT, auth, sender, []string{recipient}, []byte(message))
	if err != nil {
		log.Fatal(err)
	}
	log.Println("Email sent successfully")
}
