#coding:utf8
import config
from flask import Flask,session,flash,request,render_template,url_for,redirect
import zookeeper
import json
import time
import urllib

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

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


######################################################################
#                               普通函数定义                         #
######################################################################

"""
解析模板，从“templates”目录
"""
def render_file(file, **data):
    data['__path__'] = request.path
    data['__config__'] = config
    return render_template(file, **data)

"""
返回JSON格式，凡是输出JSON格式的地方都应该使用该方法来生成JSON格式
"""
def render_json(data = None, code = 0, msg = None):
    return json.dumps({'code': code, 'msg': msg, 'data': data})

"""
删除zookeeper节点
"""
def zookeeper_delete_node(zk, path):
    children = zookeeper.get_children(zk, path)

    for child in children:
        zookeeper_delete_node(zk, path / child)

    zookeeper.delete(zk, path)

"""
获取zookeeper路径信息
"""
def config_node(zk, path):
    nodevalue = zookeeper.get(zk, CONFIG_NODE / path)

    if path != '/':
        name = path.split('/')[-1]
    else:
        name = 'root'

    return {
        'path': path,
        'name': name,
        'value': nodevalue[0],
        'info': nodevalue[1],
        'acl': zookeeper.get_acl(zk, CONFIG_NODE / path)
    }

"""
获取zookeeper某节点和其所有子节点，并生成树
"""
def config_treenode(zk, path = None):
    if not path:
        path = FilePath('/')

    data = config_node(zk, path)
    data['children'] = []

    if data['info']['numChildren'] == 0:
        return data

    for v in zookeeper.get_children(zk, CONFIG_NODE / path):
        data['children'].append(config_treenode(zk, path / v))

    return data

"""
zookeeper 事件回调函数
"""
def watcher(zk, type, state, nodepath):
    if type == zookeeper.SESSION_EVENT:
        zookeeper.set_watcher(zk, watcher)

######################################################################
#                              模板方法定义                          #
######################################################################

"""
将时间戳转换成可读的日期时间格式
"""
def filter_datetime(timestamp, format = '%Y-%m-%d %H:%M:%S'):
    return time.strftime(format, time.localtime(int(timestamp / 1000)));

"""
将dict格式的参数进行url编码
"""
def filter_url_encode(data):
    return urllib.urlencode(data)

"""
将字符串url编码
"""
def filter_url_quote(str):
    return urllib.quote_plus(str)

"""
将数据转换成JSON格式
"""
def filter_json_dumps(data):
    return json.dumps(data)

"""
将`config_treenode`返回值显示成HTML树
"""
def filter_node_treegrid(data, depth = 0, pos = 1, sep = ''):
    if depth == 0:
        data['__sep__'] = ''

    html = render_template('node/treegrid.html', node = data)

    if depth > 0:
        if pos == 1:
            sep = sep + '&nbsp;&nbsp;'
        elif pos == 0:
            sep = sep + '│&nbsp;'
        else:
            sep = sep + '│&nbsp;'

    last = len(data['children']) - 1
    for item in enumerate(data['children']):
        if item[0] == last:
            item[1]['__sep__'] = sep + '└─'
            _pos = 1
        elif item[0] == 0:
            item[1]['__sep__'] = sep + '├─'
            _pos = -1
        else:
            item[1]['__sep__'] = sep + '├─'
            _pos = 0

        html = html + filter_node_treegrid(item[1], depth + 1, _pos, sep)

    return html

######################################################################
#                              开始代码执行                          #
######################################################################

# zookeeper连接
zk = zookeeper.init(config.zookeeper['server'], watcher)

# 初始化、配置app
app = Flask(__name__)
app.config.from_mapping(config.site)

# 注册模板函数到jinja2
app.jinja_env.filters['datetime'] = filter_datetime
app.jinja_env.filters['json_dumps'] = filter_json_dumps
app.jinja_env.filters['url_encode'] = filter_url_encode
app.jinja_env.filters['url_quote'] = filter_url_quote
app.jinja_env.filters['node_treegrid'] = filter_node_treegrid

# 在所有的页面请求前执行
@app.before_request
def before_request():
    if not zookeeper.exists(zk, ROOT_NODE):
        zookeeper.create(zk, ROOT_NODE, '', [{"perms": zookeeper.PERM_ALL, "scheme": "world", "id": "anyone"}], 0)
    elif not zookeeper.exists(zk, CONFIG_NODE):
        zookeeper.create(zk, CONFIG_NODE, '', [{"perms": zookeeper.PERM_ALL, "scheme": "world", "id": "anyone"}], 0)

######################################################################
#                              路由定义                              #
######################################################################

@app.route('/')
def server():
    searchdata = {
        'name': request.args.get('name', ''),
        'state': request.args.get('state', ''),
        'online': request.args.get('online', ''),
        'path': request.args.get('path', ''),
    }

    data = {}

    if not zookeeper.exists(zk, SERVIE_NODE):
        return render_file('index.html', data = data, searchdata = searchdata)

    for child in zookeeper.get_children(zk, SERVIE_NODE):
        server = {
            'name': child,
            'online': zookeeper.exists(zk, ONLINE_NODE / child),
            'state': 'Normal'
        }

        nodevalue = zookeeper.get(zk, SERVIE_NODE / child)
        info = json.loads(nodevalue[0])

        # filters
        print CONFIG_NODE / searchdata['path']
        if searchdata['name'] != '' and child.find(searchdata['name']) < 0:
            continue
        if searchdata['path'] != '' and not info.has_key(CONFIG_NODE / searchdata['path']):
            continue

        for key in info:
            if not zookeeper.exists(zk, key):
                server['state'] = 'Abnormal'
                break

            pathinfo = zookeeper.get(zk, key)[1]

            for item in info[key]:
                nodepath = SERVIE_NODE / child / 'project' / item['name'] / item['key']
                if not zookeeper.exists(zk, nodepath):
                    server['state'] = 'Abnormal'
                    break

                nodevalue = json.loads(zookeeper.get(zk, nodepath)[0])
                if pathinfo['version'] != nodevalue['nodeinfo']['version']:
                    server['state'] = 'Abnormal'
                elif not nodevalue['result']:
                    server['state'] = 'Abnormal'

            if server['state'] != 'Normal':
                break

        # filters

        if searchdata['state'] != '' and server['state'] != searchdata['state']:
            continue

        if searchdata['online'] == 'Yes' and not server['online']:
            continue

        if searchdata['online'] == 'No' and server['online']:
            continue

        data[child] = server

    return render_file('index.html', data = data, searchdata = searchdata)

@app.route('/server/info')
def server_info():
    name = request.args.get('name', '')
    if name == '':
        return '', 500

    if not zookeeper.exists(zk, SERVIE_NODE):
        flash('"%s" not exists' % (SERVIE_NODE))
        return redirect(request.referrer)

    nodepath = SERVIE_NODE / name
    if not zookeeper.exists(zk, nodepath):
        flash('"%s" not exists' % (nodepath))
        return redirect(request.referrer)
    
    server = {
        'name': name,
        'info': json.loads(zookeeper.get(zk, nodepath)[0]),
        'online': zookeeper.exists(zk, ONLINE_NODE / name),
    }

    for key in server['info']:
        nodevalue = None
        if zookeeper.exists(zk, key):
            nodevalue = zookeeper.get(zk, key)

        for item in server['info'][key]:
            item['path'] = key[len(CONFIG_NODE):];

            if nodevalue == None:
                item['state'] = 'NodeNotExists'
                continue

            nodepath = SERVIE_NODE / name / 'project' / item['name'] / item['key']
            if not zookeeper.exists(zk, nodepath):
                item['state'] = 'NotNotified'
                continue

            _nodevalue = json.loads(zookeeper.get(zk, nodepath)[0])
            if nodevalue[1]['version'] != _nodevalue['nodeinfo']['version']:
                item['state'] = 'VersionNotMatch'
                item['version'] = _nodevalue['nodeinfo']['version']
                item['sversion'] = nodevalue[1]['version']
            elif not _nodevalue['result']:
                item['state'] = 'NotifyFail'
                item['text'] = _nodevalue['text']
                item['returncode'] = _nodevalue['returncode']
            else:
                item['state'] = 'Normal'

    server_info = {}
    for path in server['info']:
        for item in server['info'][path]:
            if not server_info.has_key(item['name']):
                server_info[item['name']] = []

            server_info[item['name']].append(item)

    server['info'] = server_info

    return render_file('server/info.html', server = server)

@app.route('/server/delete')
def server_delete():
    name = request.args.get('name', '')
    if name == '':
        return redirect(request.referrer)

    if zookeeper.exists(zk, ONLINE_NODE / name):
        flash('"%s" is already online and can not be deleted' % (name))
        return redirect(request.referrer);

    nodepath = SERVIE_NODE / name
    if zookeeper.exists(zk, nodepath):
        zookeeper_delete_node(zk, nodepath)

    return redirect(request.referrer)

@app.route('/server/restart')
def server_restart():
    name = request.args.get('name', '')
    if name == '':
        return redirect(request.referrer)

    if not zookeeper.exists(zk, ONLINE_NODE / name):
        flash('"%s" is not online and can not be restart' % (name))
        return redirect(request.referrer);

    nodevalue = zookeeper.get(zk, ROOT_NODE)
    if nodevalue[0] != '':
        config = json.loads(nodevalue[0])
        config['restart'] = name
    else:
        config = {'restart': name}

    zookeeper.set(zk, ROOT_NODE, json.dumps(config))

    flash('Success')

    return redirect(request.referrer)


@app.route('/node')
def node():
    search = {
        'path': request.args.get('path', '')
    }

    data = config_treenode(zk)

    return render_file('node.html', data = data, search = search)

@app.route('/node/add', methods = ['GET', 'POST'])
def node_add():
    basepath = request.args.get('path', '')

    if request.method == 'POST':
        path = request.form.get('path')
        data = request.form.get('data')
        print request.form
        print request.values
        verify = True

        if len(path) == 0:
            verify = False
            flash('"Node Path" not allow empty')
        elif path[0] == '/':
            verify = False
            flash('"Node Path" can not start with "/"')
        else:
            path = CONFIG_NODE / basepath / path
            if zookeeper.exists(zk, path):
                verify = False
                flash('Path already exists:"%s"' % (path))

        if verify:
            nodepath = FilePath('/')
            try:
                for node in path.split('/'):
                    nodepath = nodepath / node

                    if not zookeeper.exists(zk, nodepath):
                        if nodepath != path:
                            zookeeper.create(zk, nodepath, '', [{"perms": zookeeper.PERM_ALL, "scheme": 'world', "id": 'anyone'}], 0)
                        else:
                            zookeeper.create(zk, nodepath, data, [{"perms": zookeeper.PERM_ALL, "scheme": 'world', "id": 'anyone'}], 0)

                return redirect('/node')
            except BaseException, e:
                flash(e.message)

        formdata = {
            'path': request.form.get('path') if path != '' else '',
            'data': data
        }
    else:
        formdata = {}

    return render_file('node/add.html', formdata = formdata, basepath = basepath)

@app.route('/node/delete')
def node_delete():
    path = request.args.get('path')

    if not path or path == '' or path == '/':
        return redirect('/node')

    zookeeper_delete_node(zk, CONFIG_NODE / path)

    return redirect('/node')

@app.route('/node/modify', methods = ['GET', 'POST'])
def node_modify():
    path = request.args.get('path', '')

    if request.method == 'POST':
        data = request.form.get('data')

        verify = True

        if not zookeeper.exists(zk, CONFIG_NODE / path):
            flash('Path already exists:"%s"' % (CONFIG_NODE / path))
            verify = False

        if verify:
            try:
                zookeeper.set(zk, CONFIG_NODE / path, data)
                return redirect('/node')
            except BaseException, e:
                flash(e.message)

    data = config_node(zk, path)

    return render_file('node/modify.html', data = data, path = path)

@app.route('/control', methods = ['GET', 'POST'])
def control():
    if request.form.get('restart', default = False):
        nodevalue = zookeeper.get(zk, ROOT_NODE)
        if nodevalue[0] != '':
            config = json.loads(nodevalue[0])
            config['restart'] = True
        else:
            config = {'restart': True}

        zookeeper.set(zk, ROOT_NODE, json.dumps(config))

        flash('Success')

    return render_file('control.html')

@app.route('/heartbeat')
def heartbeat():
    return render_json()

# run
if __name__ == '__main__':
    app.run()