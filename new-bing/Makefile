build:
	docker build -t yy194131/new-bing:$(version) .
	docker push yy194131/new-bing:$(version)

release:build
	# scp ./{cookie,cookie1,cookie2,cookie3}.json roselle:/home/linghaihui/bingchat/cookies
	ssh roselle 'bash /home/linghaihui/bingchat/start.sh $(version)'
