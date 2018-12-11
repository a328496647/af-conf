#!/usr/bin/env python
#coding:utf8
import os, sys
import zookeeper
import json
import time
from datetime import datetime
import ConfigParser
import getopt
import subprocess
import Queue
import signal
import traceback

"""
全局变量
"""
class G:
    name = ''
    tmp_dir = ''
    zookeeper_server = ''
    project = {}
    queue = Queue.PriorityQueue(maxsize = 0)
    nodever = {}
    config = {}
    zk = None

class FilePath(str):
    def split(self, s):
        return str.split(self, s)[1:]

    def __div__(self, p):
        p1 = str(p).strip('/')
        p2 = self.rstrip('/')

        if p1 == '':
            return FilePath(p2)
        elif p2 != '/':
            return FilePath(p2 + '/' + p1)
        else:
            return FilePath(p2 + p1)

ROOT_NODE = FilePath('/af-conf')
SERVIE_NODE = ROOT_NODE / 'server'
ONLINE_NODE = ROOT_NODE / 'online'
CONFIG_NODE = ROOT_NODE / 'config'

"""
输出日志
"""
def log(keyword, data, level = 'DEBUG'):
    print datetime.now().strftime('%Y-%m-%d %H:%M:%S'), level, keyword, json.dumps(data)

"""
设置zookeeper节点
option.nocreate     bool 如果不存在时是否创建
option.ephemeral    bool 创建临时节点
option.parent_perms int  parent perms
"""
def zookeeper_node_set(nodepath, nodevalue, perms, **option):
    ephemeral = 0
    if option.has_key('ephemeral') and option['ephemeral']:
        ephemeral = zookeeper.EPHEMERAL

    parent_perms = perms
    if option.has_key('parent_perms'):
        parent_perms = option['parent_perms']

    p = FilePath('/')

    for v in nodepath.split('/'):
        p = p / v

        if not zookeeper.exists(G.zookeeper, p):
            if not option.has_key('nocreate') or not option['nocreate']:
                if p == nodepath:
                    print zookeeper.create(G.zookeeper, p, nodevalue, [{"perms":perms, "scheme":"world", "id":"anyone"}], ephemeral)
                    return True
                else:
                    zookeeper.create(G.zookeeper, p, '', [{"perms":parent_perms, "scheme":"world", "id":"anyone"}], 0)
        elif p == nodepath:
            print zookeeper.set(G.zookeeper, p, nodevalue)
            return True

    return False

"""
执行系统命令
"""
def command(cmd, args = [], chdir = None, timeout = 10):
    if len(args):
        cmd = cmd + ' ' + ' '.join(args)

    childprocess = subprocess.Popen(cmd, cwd = chdir, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True)
    
    timestamp = int(time.time())
    while childprocess.poll() == None:
        time.sleep(0.1)
        if timestamp + timeout <= int(time.time()):
            childprocess.terminate()
            log('command:timeout', {'cmd': cmd, 'chdir': chdir, 'timeout': timeout}, 'ERROR')
            return False

    childprocess.wait()

    code = childprocess.returncode
    text = childprocess.stdout.read()

    log('command', {'cmd': cmd, 'chdir': chdir, 'returncode': code, 'text': text}, 'DEBUG')

    return (code, text)

"""
通过执行命令通知应用程序配置文件有更新
"""
def conf_command(data):
    cmd = data['cmd']
    args = [data['key'], data['file']]
    chdir = data['chdir']

    res = command(cmd, args, chdir, 10)

    code = res[0]
    text = res[1]

    v = {
        'returncode': code,
        'text': text,
        'nodeinfo': data['nodeinfo'],
        'nodepath': data['nodepath'],
    }

    result = (text == 'OK' and code == 0)

    if not result:
        log('command:conf:fail', {'cmd': cmd, 'chdir': chdir, 'returncode': code, 'text': text}, 'ERROR')
        v['result'] = False
    else:
        v['result'] = True

    zookeeper_node_set(SERVIE_NODE / G.name / 'project' / data['name'] / data['key'], json.dumps(v), zookeeper.PERM_ALL)

    return result

"""
当zookeeper节点（配置文件）有变化时调用
"""
def on_zookeeper_node_change(nodevalue, nodepath):
    log('zookeeper:get', {'nodepath': nodepath, 'nodeinfo': nodevalue[1]}, 'DEBUG')

    version = nodevalue[1]['version']
    file = os.path.abspath(G.tmp_dir + nodepath + os.sep + str(version))
    open(file, 'w').write(nodevalue[0]);
    
    G.nodever[nodepath] = version

    log('write:file', {'file': file}, 'DEBUG')

    for project in G.project[nodepath]:
        qdata = {
            'type': 'conf_command', 
            'cmd': project['command'],
            'name': project['name'],
            'key': project['key'],
            'file': file,
            'nodepath': nodepath, 
            'nodeinfo': nodevalue[1]
        }

        if project.has_key('chdir'):
            qdata['chdir'] = project['chdir'];

        G.queue.put((0, qdata))

"""
zookeeper 事件回调方法

state=-112  zookeeper.EXPIRED_SESSION_STATE 会话超时状态
state=-113  zookeeper.AUTH_FAILED_STATE     认证失败状态
state=1     zookeeper.CONNECTING_STATE      连接建立中
state=2     zookeeper.ASSOCIATING_STATE
state=3     zookeeper.CONNECTED_STATE       连接已建立状态
state=999                                   无连接状态

type=1      zookeeper.CREATED_EVENT         创建节点事件
type=2      zookeeper.DELETED_EVENT         删除节点事件
type=3      zookeeper.CHANGED_EVENT         更改节点事件
type=4      zookeeper.CHILD_EVENT           子节点列表变化事件
type=-1     zookeeper.SESSION_EVENT         会话session事件
type=-2     zookeeper.NOTWATCHING_EVENT     监控被移除事件
"""
def watcher(zk, type, state, nodepath):
    log('watcher', {'type': type, 'state': state, 'nodepath': nodepath}, 'DEBUG')
    
    if type == zookeeper.SESSION_EVENT:
        zookeeper.set_watcher(zk, watcher)
        if state == zookeeper.CONNECTED_STATE:
            for k in G.project:
                if zookeeper.exists(zk, k, watcher):
                    # 启动时马上就通知一次，防止在断线过程中出现了数据更改，而服务又不知道
                    on_zookeeper_node_change(zookeeper.get(zk, k), k)
                    
            if zookeeper.exists(zk, ROOT_NODE, watcher):
                config = zookeeper.get(zk, ROOT_NODE)[0]
                if config != '':
                    G.config = json.loads(config)
                    if not isinstance(G.config, dict):
                        raise TypeError()
                else:
                    G.config = {}

                log('config', G.config, 'DEBUG')
    elif type == zookeeper.CREATED_EVENT or type == zookeeper.CHANGED_EVENT:
        nodevalue = zookeeper.get(zk, nodepath, watcher)
        if nodepath == ROOT_NODE:
            if nodevalue[0] != '':
                G.config = json.loads(nodevalue[0])
                if not isinstance(G.config, dict):
                    raise TypeError()
            else:
                G.config = {}

            log('config', G.config, 'DEBUG')

            # restart process
            if G.config.has_key('restart') and G.config['restart'] in [True, G.name]:
                G.queue.put((0, {'type': 'restart'}))
        else:
            on_zookeeper_node_change(nodevalue, nodepath)
    elif type == zookeeper.DELETED_EVENT:
        zookeeper.exists(zk, nodepath, watcher) # 期待再次创建节点

"""
程序退出方法
"""
def quit(code):
    if G.zookeeper != None:
        zookeeper.close(G.zookeeper)
        G.zookeeper = None

    log('quit', [], 'DEBUG')
    sys.exit(code)

"""
进程信号回调方法
"""
def signal_handler(s, f):
    quit(0)

try:
    if len(sys.argv) == 1:
        raise BaseException('Using: %s <file>\n' % (sys.argv[0]))

    if not os.path.exists(sys.argv[1]):
        raise BaseException('cannot open "%s": No such file or directory' % (sys.argv[1]))

    # 注册进程信号监听函数
    signal.signal(signal.SIGTERM, signal_handler) # kill
    signal.signal(signal.SIGINT, signal_handler)  # ctrl+c)

    # 读取配置文件
    config = ConfigParser.ConfigParser()
    config.read(sys.argv[1])

    # 解析common段配置
    # common.name: 进程名称，这必须唯一
    # common.zookeeper_server zookeeper服务的host
    # common.tmp_dir 创建临时文件的目录
    for item in config.items('common'):
        if item[0] == 'name':
            G.name = item[1]
        elif item[0] == 'zookeeper_server':
            G.zookeeper_server = item[1]
        elif item[0] == 'tmp_dir':
            G.tmp_dir = item[1]

    # 判断临时目录是否可用
    if G.tmp_dir == '':
        raise BaseException('"tmp_dir" is not set, on "common" section')

    if not os.path.exists(G.tmp_dir):
        os.makedirs(G.tmp_dir)
    elif not os.access(G.tmp_dir, os.W_OK):
        raise BaseException('cannot open "%s": Permission denied' % (G.tmp_dir))

    # 读取配置文件其它段
    for section in config.sections():
        if section == 'common': continue

        path = {}
        project = {'name': section}
        for item in config.items(section):
            if item[0][0:5] == 'path.':
                path[item[0][5:]] = CONFIG_NODE / item[1]
            else:
                project[item[0]] = item[1]

        if not project.has_key('command'):
            raise BaseException('The configuration file "%s" is missing the "command" parameter in the "%s" section' % (file, section))

        for k in path:
            p = path[k]

            _project = project.copy()
            _project.update({'key':k})
            
            if not os.path.exists(G.tmp_dir + p):
                os.makedirs(G.tmp_dir + p)

            if not G.project.has_key(p):
                G.project[p] = []

            G.project[p].append(_project)

    # zookeeper 连接
    G.zookeeper = zookeeper.init(G.zookeeper_server, watcher)

    # /service/<name>
    zookeeper_node_set(SERVIE_NODE / G.name, json.dumps(G.project), zookeeper.PERM_ALL)
    # /online/<name>
    nodepath = ONLINE_NODE / G.name
    if zookeeper.exists(G.zookeeper, nodepath):
        raise BaseException('The same service has been run in other places')
    zookeeper_node_set(nodepath, '', zookeeper.PERM_READ, ephemeral = True, parent_perms = zookeeper.PERM_ALL)
except BaseException, e:
    print e.message
    sys.exit(0)

try:
    # 队列消费程序
    while True:
        try:
            qitem = G.queue.get(block = False)
        except Queue.Empty:
            time.sleep(1)
            continue

        timestamp = int(time.time())
        priority = qitem[0]
        data = qitem[1]
        result = True

        if priority > 0 and priority > timestamp:
            time.sleep(1)
            G.queue.put((priority, data))
            continue
            
        log('queue', qitem, 'DEBUG')

        # execute conf-command
        if data['type'] == 'conf_command':
            if data['nodeinfo']['version'] < G.nodever[data['nodepath']]:
                continue
            result = conf_command(data)
        # restart process
        elif data['type'] == 'restart':
            zookeeper.close(G.zookeeper)
            python = sys.executable
            os.execl(python, python, * sys.argv)

        # failure, 60s retry!!!
        if not result:
            if data.has_key('num'):
                data['num'] = data['num'] + 1
            else:
                data['num'] = 1

            G.queue.put((timestamp + 60, data))
except SystemExit:
    pass
except BaseException, e:
    traceback.print_exc()
    quit(0)