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

G = {
    'name':'',
    'output': '.',
    'server': '',
    'project': {},
    'queue': Queue.PriorityQueue(maxsize = 0),
    'nodever': {},
    'config': {},
    'zookeeper': None,
}

AF_CONF_NODE = '/af-conf'

def help():
    print 'Using: %s [OPTIONS] [conf...]\n' % (sys.argv[0])
    print '  -s, server     zookeeper server(host:port), use "," separated'
    print '  -o, output     config file output directory'
    print '  -n, name       set process name(unique), do not use "/"'
    print '  -h, help       show help'
    sys.exit(0)

def log(keyword, data, level = 'DEBUG'):
    print datetime.now().strftime('%Y-%m-%d %H:%M:%S'), level, keyword, json.dumps(data)

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

def conf_command(data):
    cmd = data['cmd']
    args = data['args']
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
    
    node = AF_CONF_NODE + '/' + G['name'] + '/' + data['nodepath'][1:].replace('/', '|')

    if not zookeeper.exists(G['zookeeper'], node):
        zookeeper.create(G['zookeeper'], node, json.dumps(v), [{"perms":zookeeper.PERM_ALL, "scheme":"world", "id":"anyone"}], 0)
    else:
        zookeeper.set(G['zookeeper'], node, json.dumps(v))

    return result

def zookeeper_node_change(nodevalue, nodepath):
    log('zookeeper:get', {'nodepath': nodepath, 'nodeinfo': nodevalue[1]}, 'DEBUG')

    version = nodevalue[1]['version']
    file = os.path.abspath(G['output'] + nodepath + os.sep + str(version))
    open(file, 'w').write(nodevalue[0]);
    
    G['nodever'][nodepath] = version

    log('write:file', {'file': file}, 'DEBUG')

    for project in G['project'][nodepath]:
        qdata = {
            'type': 'conf_command', 
            'cmd': project['command'], 
            'args': [project['key'], file], 
            'nodepath': nodepath, 
            'nodeinfo': nodevalue[1]
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
def watcher(zk, type, state, nodepath):
    log('watcher', {'type': type, 'state': state, 'nodepath': nodepath}, 'DEBUG')
    
    if type == zookeeper.SESSION_EVENT:
        zookeeper.set_watcher(zk, watcher)
        if state == zookeeper.CONNECTED_STATE:
            for k in G['project']:
                if zookeeper.exists(zk, k, watcher):
                    zookeeper_node_change(zookeeper.get(zk, k), k) # 启动时马上就通知一次，防止在断线过程中出现了数据更改，而服务又不知道
                    
            if zookeeper.exists(zk, AF_CONF_NODE, watcher):
                try:
                    G['config'] = json.loads(zookeeper.get(zk, AF_CONF_NODE)[0])
                    if not isinstance(G['config'], dict):
                        raise TypeError()
                except BaseException, e:
                    log('config:error', '"' + AF_CONF_NODE + '" is invalid format', 'ERROR')
                    return

                log('config', G['config'], 'DEBUG')
    elif type == zookeeper.CREATED_EVENT or type == zookeeper.CHANGED_EVENT:
        nodevalue = zookeeper.get(zk, nodepath, watcher)
        if nodepath == AF_CONF_NODE:
            try:
                G['config'] = json.loads(nodevalue[0])
                if not isinstance(G['config'], dict):
                    raise TypeError()
            except BaseException, e:
                log('config:error', '"' + AF_CONF_NODE + '" is invalid format', 'ERROR')
                return

            log('config', G['config'], 'DEBUG')

            # restart process
            if G['config'].has_key('restart') and G['config']['restart'] == True:
                G['queue'].put((0, {'type': 'restart'}))
        else:
            zookeeper_node_change(nodevalue, nodepath)
    elif type == zookeeper.DELETED_EVENT:
        zookeeper.exists(zk, nodepath, watcher) # 期待再次创建节点

def set_process_status(status):
    if G['zookeeper'] != None:
        nodepath = AF_CONF_NODE + '/' + G['name']
        nodevalue = {'status': status, 'nodes': G['project']}
        if not zookeeper.exists(G['zookeeper'], nodepath):
            zookeeper.create(G['zookeeper'], nodepath, json.dumps(nodevalue), [{"perms": zookeeper.PERM_ALL, "scheme": "world", "id": "anyone"}], 0)
        else:
            zookeeper.set(G['zookeeper'], nodepath, json.dumps(nodevalue))

def quit(code):
    try:
        if G['zookeeper'] != None:
            set_process_status('closed')
            zookeeper.close(G['zookeeper'])
            G['zookeeper'] = None
    except BaseException:
        pass

    log('quit', [], 'DEBUG')
    sys.exit(code)

def signal_handler(s, f):
    quit(0)

# listen signal
signal.signal(signal.SIGTERM, signal_handler) # kill
signal.signal(signal.SIGINT, signal_handler)  # ctrl+c

# parse command line arguments
try:
    options, files = getopt.getopt(sys.argv[1:], 'hn:s:o:', ['help', 'name=', 'server=', 'output='])
except getopt.GetoptError:
    help()

try:
    for key, val in options:
        if key in ['-s', '-server']:
            G['server'] = val
        elif key in ['-o', '--output']:
            if val[-1:] == os.sep:
                G['output'] = os.path.abspath(val[:-1])
            else:
                G['output'] = os.path.abspath(val)

            if not os.path.exists(G['output']):
                raise IOError('Output directory "'+ G['output'] +'": No such directory')

            if not os.access(G['output'], os.W_OK):
                raise IOError('Output directory "'+ G['output'] +'": Permission denied')
        elif key in ['-n', '--name']:
            G['name'] = val
        elif key in ['-h', '--help']:
            help()

    # verify arguments
    if G['name'] == '' or G['name'].find('/') >= 0:
        help()
    elif G['output'] == '':
        help()
    elif G['server'] == '':
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
                raise StandardError('The configuration file "'+file+'" is missing the "command" parameter in the "'+section+'" section')

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
    set_process_status('running')

    # queue handle
    while True:
        try:
            qitem = G['queue'].get(block = False)
        except Queue.Empty:
            time.sleep(1)
            continue

        timestamp = int(time.time())
        priority = qitem[0]
        data = qitem[1]
        result = True

        if priority > 0 and priority > timestamp:
            time.sleep(1)
            G['queue'].put((priority, data))
            continue
            
        log('queue', qitem, 'DEBUG')

        # execute conf-command
        if data['type'] == 'conf_command':
            if data['nodeinfo']['version'] < G['nodever'][data['nodepath']]:
                continue
            result = conf_command(data)
        # restart process
        elif data['type'] == 'restart':
            python = sys.executable
            os.execl(python, python, * sys.argv)

        # failure, 60s retry!!!
        if not result:
            if data.has_key('num'):
                data['num'] = data['num'] + 1
            else:
                data['num'] = 1

            G['queue'].put((timestamp + 60, data))
except SystemExit:
    pass
except BaseException, e:
    traceback.print_exc()
    quit(0)