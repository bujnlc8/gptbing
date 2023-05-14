build:
	docker build -t registry.cn-beijing.aliyuncs.com/roselle-1/chat:$(version) .
	docker push registry.cn-beijing.aliyuncs.com/roselle-1/chat:$(version)

release:build
	# scp ./{cookie,cookie1,cookie2,cookie3}.json roselle:/home/linghaihui/bingchat/cookies
	ssh roselle 'bash /home/linghaihui/bingchat/start.sh $(version)'
