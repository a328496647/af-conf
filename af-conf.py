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

G = {
    'output': '.',
    'server': '127.0.0.1:2181',
    'project': {},
    'curdir': os.path.dirname(os.path.abspath(__file__)),
    'queue': Queue.PriorityQueue(maxsize = 0),
    'nodever': {},
    'config': {},
    'zookeeper': None,
}

def help():
    print 'Using: %s [OPTIONS] [conf...]\n' % (sys.argv[0])
    print '  -s, server     zookeeper server(host:port), use "," separated'
    print '  -o, output     config file output directory'
    print '  -h, help       show help'
    sys.exit(0)

def log(keyword, data, level = 'DEBUG'):
    print "%s %s [%s] %s" % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), level, keyword, json.dumps(data))

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

def conf_command(cmd, args, chdir):
    result = command(cmd, args, chdir, 10)

    code = result[0]
    text = result[1]

    if text != 'OK' or code != 0:
        log('command:conf:fail', {'cmd': cmd, 'chdir': chdir, 'returncode': code, 'text': text}, 'ERROR')
        return False
    else:
        return True

def zookeeper_node_change(nodevalue, path):
    log('zookeeper:get', {'path': path, 'res': nodevalue[1]}, 'DEBUG')

    version = nodevalue[1]['version']
    file = os.path.abspath(G['output'] + path + os.sep + str(version) + '.json')
    open(file, 'w').write(nodevalue[0]);
    
    G['nodever'][path] = version

    log('write:file', {'file': file}, 'DEBUG')

    for project in G['project'][path]:
        qdata = {
            'type': 'conf_command', 
            'cmd': project['command'], 
            'args': [project['key'], file], 
            'path': path, 
            'version': version
        }

        if project.has_key('chdir'):
            qdata['chdir'] = project['chdir'];

        G['queue'].put((0, qdata))

"""
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
def watcher(zk, type, state, path):
    log('watcher', {'type': type, 'state': state, 'path': path}, 'DEBUG')
    
    if type == zookeeper.SESSION_EVENT:
        zookeeper.set_watcher(zk, watcher)
        if state == zookeeper.CONNECTED_STATE:
            for k in G['project']:
                if zookeeper.exists(zk, k, watcher):
                    zookeeper_node_change(zookeeper.get(zk, k), k) # 启动时马上就通知一次，防止在断线过程中出现了数据更改，而服务又不知道
                    
            if zookeeper.exists(zk, '/af-conf', watcher):
                try:
                    G['config'] = json.loads(zookeeper.get(zk, '/af-conf')[0])
                    if not isinstance(G['config'], dict):
                        raise Exception()
                except Exception as e:
                    log('config:error', '"/af-conf" is invalid format', 'ERROR')
                    return

                log('config', G['config'], 'DEBUG')
    elif type == zookeeper.CREATED_EVENT or type == zookeeper.CHANGED_EVENT:
        nodevalue = zookeeper.get(zk, path, watcher)
        if path == '/af-conf':
            try:
                G['config'] = json.loads(nodevalue[0])
                if not isinstance(G['config'], dict):
                    raise Exception()
            except Exception as e:
                log('config:error', '"/af-conf" is invalid format', 'ERROR')
                return

            log('config', G['config'], 'DEBUG')

            # restart process
            if G['config'].has_key('restart') and G['config']['restart'] == True:
                G['queue'].put((0, {'type': 'restart'}))
        else:
            zookeeper_node_change(nodevalue, path)
    elif type == zookeeper.DELETED_EVENT:
        zookeeper.exists(zk, path, watcher) # 期待再次创建节点

try:
    # parse command line arguments
    try:
        options, files = getopt.getopt(sys.argv[1:], 'hs:o:', ['help', 'server=', 'output='])
    except Exception, e:
        help()

    for option in options:
        key = option[0]
        val = option[1]
        if key == '-s' or key == '--server':
            G['server'] = val
        elif key == '-o' or key == '--output':
            if val[-1:] == os.sep:
                G['output'] = os.path.abspath(val[:-1])
            else:
                G['output'] = os.path.abspath(val)

            if not os.path.exists(G['output']):
                raise Exception('Output directory "'+ G['output'] +'": No such directory')

            if not os.access(G['output'], os.W_OK):
                raise Exception('Output directory "'+ G['output'] +'": Permission denied')
        if key == '-h' or key == '--help':
            help()

    # read config file
    for file in files:
        config = ConfigParser.ConfigParser()
        config.read(file)
        for section in config.sections():
            paths = {}
            project = {'name': section}
            for item in config.items(section):
                if item[0][0:5] == 'path.':
                    paths[item[0][5:]] = item[1]
                else:
                    project[item[0]] = item[1]

            if not project.has_key('command'):
                raise Exception('The configuration file "'+file+'" is missing the "command" parameter in the "'+section+'" section')

            for key in paths:
                pro = project.copy()
                pro.update({'key':key})
                
                if not os.path.exists(G['output'] + paths[key]):
                    os.makedirs(G['output'] + paths[key])

                if not G['project'].has_key(paths[key]):
                    G['project'][paths[key]] = []

                G['project'][paths[key]].append(pro)

    # zookeeper connect
    G['zookeeper'] = zookeeper.init(G['server'], watcher)

    # queue handle
    while True:
        qitem = G['queue'].get()
        priority = qitem[0]
        data = qitem[1]
        timestamp = int(time.time())
        result = True

        if priority > 0 and priority > timestamp:
            time.sleep(1)
            G['queue'].put((priority, data))
            continue
            
        log('queue', qitem, 'DEBUG')

        # execute conf-command
        if data['type'] == 'conf_command':
            if data['version'] < G['nodever'][data['path']]:
                continue
            result = conf_command(data['cmd'], data['args'], data['chdir'])
        # restart process
        elif data['type'] == 'restart':
            python = sys.executable
            os.execl(python, python, * sys.argv)

        if not result:
            if data.has_key('num'):
                data['num'] = data['num'] + 1
            else:
                data['num'] = 1

            G['queue'].put((timestamp + 60, data))

except KeyboardInterrupt, e:
    pass
except Exception, e:
    raise e
finally:
    if G['zookeeper'] != None:
        zookeeper.close(G['zookeeper'])

log('quit', [], 'DEBUG')
sys.exit(0)