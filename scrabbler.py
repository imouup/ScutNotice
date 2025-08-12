import os
import requests
import json
from flask import Flask, jsonify, request


os.makedirs("./data", exist_ok=True)


class Scrabbler:
    '''
    定义所有抓取和数据处理方法的类
    '''
    def __init__(self):
        self.headers = None
        self.proxy = None
        self.namelist = ['jw', 'xy'] # 所有数据的存储名称, 用于数据存储
        self.qdata = {} # quick storage 内存
        self._set()
        self._load_quick_storage()  # 加载 quick storage 中的内容到内存

    def _load_headers(self):
        # 读取headers配置信息
        if os.path.exists('headers.json'):
            with open('headers.json', 'r', encoding='utf-8') as json_file:
                headers = json.load(json_file)

        else:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0',
                'Cookie': 'JSESSIONID=4E5BE59DFABCFC3D311A27803FC76F3E; my_client_ticket=Guih0P5iamKYp3wu',
                'sec-ch-ua-platform': "Windows"
            }
        return headers

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


    # 设置headers和代理
    def _set(self):
        self.headers = self._load_headers()
        self.proxy = self._load_proxy()


    # 公有方法

    def edit_headers(self, request):
        '''
        修改headers
        :param request: flask request对象（POST方法）
        :return: json格式的message和新headers
        '''

        new_headers = request.json
        self.headers.update(new_headers)
        with open('headers.json', 'w', encoding='utf-8') as json_file:
            json.dump(self.headers, json_file, ensure_ascii=False, indent=4)
        return {"message": "Headers updated successfully", "new_headers": self.headers}



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
        try:
            re = requests.post('https://jw.scut.edu.cn/zhinan/cms/article/v2/findInformNotice.do', headers=self.headers,
                               params=pa, proxies=self.proxy)
            tx = re.text
            js = json.loads(tx)  # 解析为json格式

            # 按照id解析为字典
            data_dict = {}
            datalist = js['list']
            for data in datalist:
                data_dict[str(data['id'])] = data

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
