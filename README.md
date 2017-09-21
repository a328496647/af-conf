# af-conf
项目配置集中化管理工具，通过监听zookeeper节点的变化去调用预设的脚本文件实现能配置的更新。zookeeper项目地址：[http://zookeeper.apache.org/](http://zookeeper.apache.org/)

## 使用方法
本工具由python编写，无特殊依赖库，下载即用。

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
2. `chdir` 调用命令之前先cd到该目录
3. `path.[key]` 要监听的配置文件（zookeeper节点）

当监听到配置文件有更改时，会将配置文件的内容保存为文件，并将文件路径和`path.[key]`中的`key`传递给`command`脚本，例如：

	php xxx.php mongodb_user_messages /tmp/af-conf/anfeng/dev/mongodb/sdk/user_messages/2.json

此时在`xxx.php`脚本中通过argv[1]能拿到`path.[key]`中的`key`，argv[2]能拿到配置文件的路径，脚本在调用成功之后必须输出`SUCCESS`并返回状态码`0`，否则将会每隔`60`秒重试

### 启动监听脚本

	Using: af-conf.py [OPTIONS] [conf...]

		-s, server     zookeeper server(host:port), use "," separated
		-o, output     config file output directory
		-h, help       show help

参数说明

1. `-s, server` 设置zookeeper服务的地址，多个服务器使用逗号分隔，例如：`192.168.1.100:2181,192.168.1.100:2182`
2. `-o, output` 当监听到配置文件发生变化时，将配置文件何存在何处
3. `-h, help` 显示帮助

示例：

	python ./../af-conf.py --server=127.0.0.1:2181 -o /tmp/af-conf ./af-conf.conf



### 报警设置
当配置文件发生更改，调用通知脚本（`command`）时，脚本没有调用成功怎么办？只需在zookeeper中增加一个根节点为：`/af-conf`，其中增加`mail`配置（json格式），即可在发生错误时邮件通知。节点值示例如下：

	{
	    "mail":{
	        "enable":false,
	        "smtp_host":"smtp.exmail.qq.com",
	        "smtp_port":465,
	        "encrypt":"ssl",
	        "username":"xxx@anfan.com",
	        "password":"xxx",
	        "address":"xxx@anfan.com",
	        "name":"af-conf alarm",
	        "receiver":[
	            "sss60@qq.com"
	        ]
	    }
	}

1. `mail.enable` 是否启用邮件报警
2. `mail.smtp_host` smtp邮件服务器Host
3. `mail.smtp_port` smtp邮件服务器Port
4. `mail.encrypt` 网络加密类型，`ssl`或空
5. `mail.username` smtp邮件服务器登陆用户名
6. `mail.password` smtp邮件服务器登陆密码
7. `mail.address` 发件人邮件地址
8. `mail.name` 发件人名字
9. `mail.receiver` 收件人（警报接收人）列表