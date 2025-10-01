import os
from datetime import datetime
import requests
import json
from flask import Flask, jsonify, request
import ssl
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib3.util import create_urllib3_context

os.makedirs("./data", exist_ok=True)
os.makedirs("./headers", exist_ok=True)

# 定义一个低 SSL 安全性的自定义 Adapter, 用于抓取统一门户通知
class Low_secure_HttpAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        # 创建一个自定义的 SSL 上下文
        # 'ALL' 表示接受所有服务端支持的加密算法
        # @SECLEVEL=1 降低了安全等级（默认为2），允许一些老旧但仍被部分服务器使用的算法
        ctx = ssl.create_default_context()
        ctx.set_ciphers('ALL:@SECLEVEL=1')

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_context=ctx
        )

class Scrabbler:
    '''
    定义所有抓取和数据处理方法的类
    '''
    def __init__(self):
        self.headers = None
        self.proxy = None
        self.namelist = ['jw', 'xy', 'myscut_gw', 'myscut_sw', 'myscut_xz', 'myscut_dw', 'myscut_xs', 'myscut_news'] # 所有数据的存储名称, 用于数据存储
        self.platform_list = ['jw', 'myscut'] # 支持的平台
        self.qdata = {} # quick storage 内存
        self.headers = {}
        self._set()
        self._load_quick_storage()  # 加载 quick storage 中的内容到内存


    def _load_headers(self):

        for platform in self.platform_list:
            path = f'headers/{platform}_headers.json'
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as json_file:
                    self.headers[platform] = json.load(json_file)
            else:
                return {"error": f"Headers file {path} not found"}, 500


    def _load_proxy(self):
        # 设置代理
        proxy = {
            'http': 'socks5://10.195.134.11:1080',
            'https': 'socks5://10.195.134.11:1080',
        }
        return proxy

    # 加载文件系统中 quick storage 中的内容到内存
    def _load_quick_storage(self):
        '''
        加载 quick storage 中的内容到内存
        :return: 完成情况
        '''
        for name in self.namelist:
            if os.path.exists(f'data/{name}_q.json'):
                with open(f'data/{name}_q.json', 'r', encoding='utf-8') as json_file:
                    self.qdata[name] = json.load(json_file)
            else:
                self.qdata[name] = {}

        return "Successfully loaded quick storage into memory."

    # 比对 qucik storage 中的差异
    def _compare(self, json_data, name):
        '''
        比对 quick storage 与新数据的差异
        :param json_data: 新获取到的json数据，已经过id字典化处理
        :param name: 数据在namelist中的名称
        :return: [ 代号（0表示无差异，1表示有差异）, 差异 ]
        '''
        qstorage_id = set(self.qdata[name].keys())
        new_id = set(json_data.keys())
        all_id = qstorage_id | new_id
        # 剔除all_id中的旧id

        diff_id = []
        for id in all_id:
            if id not in qstorage_id:
                diff_id.append(id)

        new_data = {}
        for id in diff_id:
            new_data[id] = json_data[id]

        return [1 if new_data else 0, new_data]


    # 初始化代理和 headers
    def _set(self):
        self._load_headers()
        self.proxy = self._load_proxy()


    # 公有方法

    def edit_headers(self, request):
        '''
        修改headers
        :param request: flask request对象（POST方法）, 包含 headers data和 platform name
        :return: json格式的message和新headers
        '''

        data = request.json
        new_headers = data['headers']
        platform = data['platform']
        if not platform in self.platform_list:
            return jsonify({"error": "Invalid platform name, which must be in [jw, myscut]"}), 400
        self.headers[platform].update(new_headers)
        with open(f'{platform}_headers.json', 'w', encoding='utf-8') as json_file:
            json.dump(self.headers[platform], json_file, ensure_ascii=False, indent=4)
        return jsonify({"message": f"Headers file {platform}_headers.json updated successfully", "new_headers": new_headers})



    # 以下为所有抓取方法的抽象方法
    def scrabble_template(self, request):
        '''
        抓取函数模板
        :param request: flask request对象, 包含输入参数
        :return: 字典格式数据
        '''

        pa = {
            'test': request.args.get('test')
        }
        try:
            re = requests.get('https://example.com/api', headers=self.headers, params=pa, proxies=self.proxy)
            tx = re.text
            js = json.loads(tx) # 解析为json格式

            # 按照id解析为字典
            data_dict = {}
            datalist = js['data']
            for data in datalist:
                data_dict[str(data['id'])] = data

            # 与 quick storage 进行比对，获取新内容
            compare_result = self._compare(data_dict, request.args.get('name'))
            whether_new, new_data = compare_result

            # 覆盖 quick storage
            with open(f'./data/{request.args.get("name")}_q.json', 'w', encoding='utf-8') as quick_storage_file:
                json.dump(data_dict, quick_storage_file, ensure_ascii=False, indent=4)

            # update longtime storage
            with open(f'./data/{request.args.get("name")}_long.json', 'w+', encoding='utf-8') as long_storage_file:
                long_data = json.load(long_storage_file)
                long_data.update(new_data)
                json.dump(long_data, long_storage_file, ensure_ascii=False, indent=4)

            return {"message": "Scrabble successful", "NewData": new_data, "WhetherNew": whether_new}, 200

        # 错误处理
        except requests.exceptions.ConnectionError:
            return {"error": "socks5代理服务器错误，请检查410wifi上的代理服务"}, 500
        except Exception as e:
            return {"error": f"发生未知错误: {e}"}, 500


    def jwnotice(self, request):
        '''
        抓取教务处通知，tag为0为教务处通知，tag为1为学院通知
        :param request: flask request对象, 包含输入参数
        :return: json格式数据
        '''
        # 根据name判断category
        if not request.args.get('name'):
            return {"error": "name parameter is required"}, 400
        name = request.args.get('name')
        if name == 'jw':
            category = 0
        elif name == 'xy':
            category = 1
        else:
            return {"error": "name parameter must be 'jw' or 'xy'"}, 400


        pa = {
            'category': category,
            'tag': request.args.get('tag', default=0, type=int),
            'pageNum': request.args.get('pageNum', default=1, type=int),
            'pageSize': request.args.get('pageSize', default=15, type=int),
            'keyword': '',
        }
        headers = self.headers['jw']

        try:
            re = requests.post('https://jw.scut.edu.cn/zhinan/cms/article/v2/findInformNotice.do', headers=headers,
                               params=pa, proxies=self.proxy)
            tx = re.text
            js = json.loads(tx)  # 解析为json格式

            # 按照id解析为字典
            data_dict = {}
            datalist = js['list']
            for data in datalist:
                normalized_item = {
                    'id': str(data['id']),
                    'title': data['title'],
                    'createTime': data['createTime'],
                    'tag': data['tag']
                }
                normalized_item.update(data)

                data_dict[normalized_item['id']] = normalized_item

            # 与 quick storage 进行比对，获取新内容
            compare_result = self._compare(data_dict, request.args.get('name'))
            whether_new, new_data = compare_result

            # 覆盖 quick storage
            with open(f'./data/{request.args.get("name")}_q.json', 'w', encoding='utf-8') as quick_storage_file:
                json.dump(data_dict, quick_storage_file, ensure_ascii=False, indent=4)
            self.qdata[name] = data_dict  # 更新内存中的 quick storage

            # update longtime storage
            if os.path.exists(f'./data/{request.args.get("name")}_long.json'):
                with open(f'./data/{request.args.get("name")}_long.json', 'r', encoding='utf-8') as long_storage_file:
                    if os.fstat(long_storage_file.fileno()).st_size != 0:
                        long_data = json.load(long_storage_file)
                    else:
                        long_data = {}
            else:
                long_data = {}

            if new_data:
                with open(f'./data/{request.args.get("name")}_long.json', 'w+',
                          encoding='utf-8') as long_storage_file:
                    long_data.update(new_data)
                    json.dump(long_data, long_storage_file, ensure_ascii=False, indent=4)


            return {"message": "Scrabble successful", "NewData": new_data, "WhetherNew": whether_new},200

        # 错误处理
        except requests.exceptions.ConnectionError:
            return {"error": "socks5代理服务器错误，请检查410wifi上的代理服务"}, 500
        except Exception as e:
            return {"error": f"发生未知错误: {e}"}, 500

    def myscut_notice(self, request):
        '''
        抓取统一门户的事务通知
        :param request: flask request对象, 包含输入参数
        :return: json格式数据
        '''
        # 根据name判断category
        if not request.args.get('name'):
            return {"error": "name parameter is required"}, 400
        name = request.args.get('name')

        name_type_dict = {
            'myscut_gw': '公务通知',
            'myscut_sw': '事务通知',
            'myscut_xz': '行政公文',
            'myscut_dw': '党务公文',
            'myscut_xs': '学术通知',
            'myscut_news': '校园新闻',
        }

        type = name_type_dict.get(name)
        if not type:
            return {"error": "name parameter must be one of 'myscut_gw', 'myscut_sw', 'myscut_xz', 'myscut_dw', 'myscut_xs', 'myscut_news'"}, 400

        # 构造请求的 payload
        payload = {
            "mapping": "getAllPimList",
            "pageNum": request.args.get('pageNum', default=1, type=int),
            "pageSize": request.args.get('pageSize', default=15, type=int),
            "PIM_TITLE": "",
            "TYPE_NAME": type,
            "BELONG_UNIT_NAME": "",
            "START_TIME": "",
            "END_TIME": ""
        }
        # 加载专用的headers，如果不存在则使用默认
        headers = self.headers['myscut']
        url = 'https://my.scut.edu.cn/up/up/pim/allpim/getAllPimList'

        # --- 使用自定义 Adapter 以兼容旧版SSL ---
        session = requests.Session()
        # 将类中预定义的低安全性Adapter挂载到https协议上
        session.mount('https://', Low_secure_HttpAdapter())

        try:
            # 使用 session 对象发送请求
            re = session.post(url, headers=headers, json=payload, proxies=self.proxy) #TODO:解决打开proxy后出现SSL错误的问题
            re.raise_for_status()  # 检查请求是否成功 (e.g., 4xx or 5xx errors)
            js = re.json()

            # 按照 RESOURCE_ID 解析为字典
            data_dict = {}
            datalist = js.get('list', [])  # 使用 .get() 避免因缺少'list'键而报错
            for data in datalist:
                ## --- 数据标准化处理 ---
                # 将毫秒时间戳转换为 YYYY.MM.DD 格式字符串
                ts_ms = data['CREATE_TIME']
                dt_object = datetime.fromtimestamp(ts_ms / 1000)
                formatted_time = dt_object.strftime('%Y.%m.%d')

                # 创建标准格式的字典
                normalized_item = {
                    'id': str(data['RESOURCE_ID']),
                    'title': data['PIM_TITLE'],
                    'createTime': formatted_time
                    # myscut 数据没有 tag，所以不添加
                }

                # 将原始数据也并入，以防未来需要
                normalized_item.update(data)

                # 使用标准化的id和数据
                data_dict[normalized_item['id']] = normalized_item

            # 与 quick storage 进行比对，获取新内容
            compare_result = self._compare(data_dict, name)
            whether_new, new_data = compare_result

            # 覆盖 quick storage
            with open(f'./data/{name}_q.json', 'w', encoding='utf-8') as quick_storage_file:
                json.dump(data_dict, quick_storage_file, ensure_ascii=False, indent=4)
            self.qdata[name] = data_dict  # 更新内存中的 quick storage

            # update longtime storage
            long_data = {}
            long_storage_path = f'./data/{name}_long.json'
            if os.path.exists(long_storage_path):
                with open(long_storage_path, 'r', encoding='utf-8') as long_storage_file:
                    # 检查文件是否为空
                    if os.fstat(long_storage_file.fileno()).st_size != 0:
                        long_data = json.load(long_storage_file)

            if new_data:
                long_data.update(new_data)
                with open(long_storage_path, 'w', encoding='utf-8') as long_storage_file:
                    json.dump(long_data, long_storage_file, ensure_ascii=False, indent=4)

            return {"message": "Scrabble successful for my.scut.edu.cn", "NewData": new_data,
                    "WhetherNew": whether_new}, 200

        # 更具体的错误处理
        except requests.exceptions.SSLError as e:
            return {"error": f"SSL 错误，无法连接到目标服务器: {e}"}, 500
        except requests.exceptions.ConnectionError:
            return {"error": "代理服务器或网络连接错误，请检查代理设置和网络状态"}, 500
        except requests.exceptions.HTTPError as e:
            return {"error": f"HTTP 请求错误: {e.response.status_code} {e.response.reason}"}, 500
        except Exception as e:
            return {"error": f"发生未知错误: {e}"}, 500
