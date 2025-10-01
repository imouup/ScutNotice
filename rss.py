from flask import Flask, request, jsonify
from datetime import datetime, timezone
import scrabbler
import requests
import json
import os
from feedgen.feed import FeedGenerator
import pytz

app = Flask(__name__)
scrabbler = scrabbler.Scrabbler()
namelist = scrabbler.namelist  # 获取所有数据的存储名称
lastUpdated = None

# 设置namedict，包含每个name的信息
namedict = {
    'jw':{
        'link_prefix':'https://jw.scut.edu.cn/zhinan/cms/article/view.do?type=posts&id=',
        'title':'华南理工大学教务处教务通知',
        'href':'https://jw.scut.edu.cn/zhinan/cms/toPosts.do?category=0&tag=6',
        'description':'华南理工大学教务处官网发布的教务通知, 包含考试、选课、交流等信息',
    },
    'xy':{
        'link_prefix':'https://jw.scut.edu.cn/zhinan/cms/article/view.do?type=posts&id=',
        'title':'华南理工大学教务处学院通知',
        'href':'https://my.scut.edu.cn/up/up/pim/allpim/getAllPimList',
        'description':'华南理工大学教务处官网发布的学院通知， 包含各学院向全校公开的考试、选课等通知信息',
    },
    'myscut_gw':{
        'link_prefix':'https://my.scut.edu.cn/up/view?m=up#act=up/pim/showpim&id=',
        'title':'华南理工大学统一门户公务通知',
        'href':'https://my.scut.edu.cn/up/up/pim/allpim/getAllPimList',
        'description':'华华南理工大学统一门户公务通知',
    },
    'myscut_sw':{
        'link_prefix':'https://my.scut.edu.cn/up/view?m=up#act=up/pim/showpim&id=',
        'title':'华南理工大学统一门户事务通知',
        'href':'https://my.scut.edu.cn/up/up/pim/allpim/getAllPimList',
        'description':'华华南理工大学统一门户事务通知',
    },
    'myscut_xz': {
        'link_prefix': 'https://my.scut.edu.cn/up/view?m=up#act=up/pim/showpim&id=',
        'title': '华南理工大学统一门户行政公文',
        'href': 'https://my.scut.edu.cn/up/up/pim/allpim/getAllPimList',
        'description': '华华南理工大学统一门户行政公文',
    },
    'myscut_dw': {
        'link_prefix': 'https://my.scut.edu.cn/up/view?m=up#act=up/pim/showpim&id=',
        'title': '华南理工大学统一门户党务公文',
        'href': 'https://my.scut.edu.cn/up/up/pim/allpim/getAllPimList',
        'description': '华华南理工大学统一门户党务公文',
    },
    'myscut_xs': {
        'link_prefix': 'https://my.scut.edu.cn/up/view?m=up#act=up/pim/showpim&id=',
        'title': '华南理工大学统一门户学术通知',
        'href': 'https://my.scut.edu.cn/up/up/pim/allpim/getAllPimList',
        'description': '华华南理工大学统一门户学术通知',
    },
    'myscut_news': {
        'link_prefix': 'https://my.scut.edu.cn/up/view?m=up#act=up/pim/showpim&id=',
        'title': '华南理工大学统一门户校园新闻',
        'href': 'https://my.scut.edu.cn/up/up/pim/allpim/getAllPimList',
        'description': '华华南理工大学统一门户校园新闻',
    }
}

# 读取上一次更新时间
def init_last_updated():
    if os.path.exists('data/lastUpdated.txt'):
        with open('data/lastUpdated.txt', 'r', encoding='utf-8') as f:
            return f.read().strip()
    else:
        return None

# 写入上一次更新时间
def write_last_updated(lastUpdated):
    with open('data/lastUpdated.txt', 'w', encoding='utf-8') as f:
        f.write(lastUpdated)


# 建立public文件夹
os.makedirs('rsspublic', exist_ok=True)
for name in namelist:
    os.makedirs('rsspublic/'+name, exist_ok=True)


# 接收更新指令
@app.route('/update', methods=['POST'])
def update():
    name = request.json.get('name')
    multi = request.json.get('multi') # 是否有多个tags 0/1
    tag_num = request.json.get('tag_num') # tag数量

    # 记录result
    result = {}
    result[0] = feed(name) # 更新完整rss
    if multi == 1:
        for tag in range(1,tag_num+1):
            result[tag] = feed_tag(name, tag)

    # 记录最后更新时间
    global lastUpdated
    lastUpdated = datetime.now(timezone.utc).isoformat()
    write_last_updated(lastUpdated)

    return jsonify({"message":"RSS更新完成", "result":result}), 200

# 获取lastupdated
@app.route('/lastUpdated', methods=['GET'])
def last_updated():
    global lastUpdated
    if lastUpdated is None:
        lastUpdated = init_last_updated() # 若内存中无lastUpdated则从文件中读取

    data = {
        "lastUpdated": lastUpdated
    }
    return jsonify(data), 200



# RSS文件生成(不筛选)
def feed(name):
    '''
    RSS feed 生成
    :param name: 数据在namelist中的名称
    :return:
    '''
    filepath = f'rsspublic/{name}/{name}_0.rss'

    # 读取json文件
    try:
        with open(f'data/{name}_long.json', 'r', encoding='utf-8') as json_file:
            jsondata = json.load(json_file)
    except FileNotFoundError:
        return 'long storage文件不存在'
    except json.JSONDecodeError:
        return 'long storage文件json解析错误'
    except Exception as e:
        return f'发生未知错误: {e}'

    # 获取基本信息
    infos = namedict[name]

    # 获取article link的前缀
    link_prefix = infos['link_prefix']

    # 按时间对数据进行排序
    notifications_list = list(jsondata.values())

    sorted_data = sorted(
        notifications_list,
        key=lambda item: datetime.strptime(item['createTime'], '%Y.%m.%d'),
        reverse=True
    )


    # 设置时区
    cst_tz = pytz.timezone('Asia/Shanghai')

    # 初始化 FeedGenerator
    fg = FeedGenerator()
    fg.title(infos['title'])
    fg.link(href=infos['href'], rel='alternate')
    fg.description(infos['description'])
    fg.language('zh-CN')


    # 构建RSS feed
    for notice in sorted_data:
        fe = fg.add_entry()

        # 构建文章链接
        notice_url = f'{infos["link_prefix"]}{notice["id"]}'

        fe.id(notice_url)
        fe.title(notice['title'])
        fe.link(href=notice_url)
        fe.description(notice['title'])

        # 处理日期
        try:
            create_time = datetime.strptime(notice['createTime'], '%Y.%m.%d')
            create_time = cst_tz.localize(create_time)
            fe.pubDate(create_time)
        except (ValueError, KeyError):
            # 如果日期格式错误或不存在，则跳过日期的设置
            pass

    # 生成RSS文件
    fg.rss_file(filepath, pretty=True) # pretty=True 使XML文件格式化，易于阅读

    return {"message": "RSS文件成功生成", "tag": 0, "filepath": filepath, "status_code": 200}


def feed_tag(name, tag):
    '''
    RSS feed 生成
    :param name: 数据在namelist中的名称
    :return:
    '''
    filepath = f'rsspublic/{name}/{name}_{tag}.rss'

    # 读取json文件
    try:
        with open(f'data/{name}_long.json', 'r', encoding='utf-8') as json_file:
            jsondata = json.load(json_file)
    except FileNotFoundError:
        return 'long storage文件不存在'
    except json.JSONDecodeError:
        return 'long storage文件json解析错误'
    except Exception as e:
        return f'发生未知错误: {e}'

    # 获取基本信息
    infos = namedict[name]

    # 获取article link的前缀
    link_prefix = infos['link_prefix']

    # 按时间对数据进行排序
    notifications_list = list(jsondata.values())
    sorted_data = sorted(
        notifications_list,
        key=lambda item: datetime.strptime(item['createTime'], '%Y.%m.%d'),
        reverse=True
    )


    # 设置时区
    cst_tz = pytz.timezone('Asia/Shanghai')

    # 初始化 FeedGenerator
    fg = FeedGenerator()
    fg.title(infos['title'])
    fg.link(href=infos['href'], rel='alternate')
    fg.description(infos['description'])
    fg.language('zh-CN')


    # 构建RSS feed
    for notice in sorted_data:
        if notice['tag'] == tag:
            fe = fg.add_entry()

            # 构建文章链接
            notice_url = f'{infos["link_prefix"]}{notice["id"]}'

            fe.id(notice_url)
            fe.title(notice['title'])
            fe.link(href=notice_url)
            fe.description(notice['title'])

            # 处理日期
            try:
                create_time = datetime.strptime(notice['createTime'], '%Y.%m.%d')
                create_time = cst_tz.localize(create_time)
                fe.pubDate(create_time)
            except (ValueError, KeyError):
                # 如果日期格式错误或不存在，则跳过日期的设置
                pass
        else:
            continue

    # 生成RSS文件
    if fg.entry():
        fg.rss_file(filepath, pretty=True) # pretty=True 使XML文件格式化，易于阅读
        return {"message": "RSS文件成功生成", "tag": tag,"filepath": filepath, "status_code": 200}
    else:
        return {"message": "tag不存在", "tag": tag, "status_code": 404}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)