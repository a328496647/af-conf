# af-conf
项目配置集中化管理工具，通过监听zookeeper节点的变化去调用预设的脚本实现配置的更新，每个项目可以根据自身所需去订阅不同的配置项。zookeeper项目地址：[http://zookeeper.apache.org/](http://zookeeper.apache.org/)

## 使用方法
本工具由python编写，除了zookeeper包，其它无特殊依赖库。zookeeper包使用的是：

	// zkpython 0.4.2
	https://pypi.python.org/pypi/zkpython/

### 设置要监听配置
配置文件使用`.ini`文件，示例如下：

	[sdkapi]
	command = php xxx.php
	chdir = ./
	path.db_master = /anfeng/dev/database/sdk/master
	path.db_slave = /anfeng/dev/database/sdk/slave
	path.db_56gamebbs_master = /anfeng/dev/database/sdk/56gamebbs_master
	path.db_56gamebbs_slave = /anfeng/dev/database/sdk/56gamebbs_slave
	path.mongodb_user_messages = /anfeng/dev/mongodb/sdk/user_messages
	path.mongodb_logs = /anfeng/dev/mongodb/sdk/logs
	path.redis_default = /anfeng/dev/redis/sdk/default

1. `command` 如果配置文件有更新，则调用该shell命令
2. `chdir` 调用命令之前先chdir到该目录
3. `path.[key]` 要订阅的配置文件（zookeeper节点）

当监听到配置文件有更改时，会将配置文件的内容保存为文件，并将文件路径和`path.[key]`中的`key`传递给`command`脚本，例如：

	php xxx.php mongodb_user_messages /tmp/af-conf/anfeng/dev/mongodb/sdk/user_messages/2.json

此时在`xxx.php`脚本中通过argv[1]能拿到`path.[key]`中的`key`，argv[2]能拿到配置文件的路径，脚本在调用成功之后必须输出`OK`并返回状态码`0`，否则将会每隔`60`秒重试

### 启动监听脚本

	Using: af-conf.py [OPTIONS] [conf...]

		-s, server     zookeeper server(host:port), use "," separated
		-o, output     config file output directory
		-h, help       show help

参数说明

1. `-s, server` 设置zookeeper服务的地址，多个服务器使用逗号分隔，例如：`192.168.1.100:2181,192.168.1.100:2182`
2. `-o, output` 当监听到配置文件发生变化时，将配置文件何存在何处
3. `-h, help` 显示帮助

示例（项目目录下有一个demo）：

	python ./../af-conf.py --s 127.0.0.1:2181 -o /tmp/af-conf ./af-conf.conf

## `af-conf`自身的配置
`af-conf`解决的问题就是集中管理多台服务器上的配置文件，那么`af-conf`本身的配置怎么去管理？`af-conf`自身的配置也是通过zookeeper节点来设置，它的zookeeper节点名称为：`/af-conf`，节点值为json格式。

	{
		"restart":true
	｝

`restart`，如果标记为true，则`af-conf`进程本身会被重启