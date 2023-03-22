build:
	docker build -t yy194131/new-bing:$(version) .
	docker push yy194131/new-bing:$(version)

release:build
	ssh roselle 'bash /home/linghaihui/bingchat/start.sh $(version)'
