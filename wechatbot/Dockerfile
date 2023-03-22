FROM golang:1.16 as builder
ENV GOPROXY=https://goproxy.cn,direct
WORKDIR /app
COPY  . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o chatgpt
FROM alpine:3.17.2
WORKDIR /app
COPY --from=builder /app/chatgpt .
ENTRYPOINT ["./chatgpt", ">>", "chatgpt.log", "2>&1"]
