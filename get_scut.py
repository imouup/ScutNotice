# 已弃用

import os
import requests
import json
from flask import Flask, jsonify, request
os.makedirs("./data", exist_ok=True)

app = Flask(__name__)

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

# 设置代理
# proxy = {
#     'http': 'socks5://10.195.134.11:1080',
#     'https': 'socks5://10.195.134.11:1080',
# }


# 获取教务处通知
@app.route('/scut/jwnotice', methods=['GET'])
def get_jw_notice():
    pa = {
        'category': request.args.get('category', default=0, type=int),
        'tag': request.args.get('tag', default=0, type=int),
        'pageNum': request.args.get('pageNum', default=1, type=int),
        'pageSize': request.args.get('pageSize', default=15, type=int),
        'keyword': '',
    }

    try:
        re = requests.post('https://jw.scut.edu.cn/zhinan/cms/article/v2/findInformNotice.do',headers=headers,params=pa)
        tx = re.text
        js = json.loads(tx)


        return jsonify(js)

    except requests.exceptions.ConnectionError:
        return jsonify({"error": "socks5代理服务器错误，请检查410wifi上的代理服务"}), 500
    except Exception as e:
        return jsonify({"error": f"发生未知错误:{e}"}), 500


# 修改headers
@app.route('/scut/edit_headers', methods=['POST'])
def edit_headers():
    global headers
    data = request.json
    new_headers = data['headers']
    name = data['name']
    if not name in ['jw', 'myscut']:
        return jsonify({"error": "Invalid name"}), 400
    headers.update(new_headers)
    with open(f'{name}_headers.json', 'w', encoding='utf-8') as json_file:
        json.dump(headers, json_file, ensure_ascii=False, indent=4)
    return jsonify({"message": f"Headers file {name}_headers.json updated successfully", "new_headers": headers})


@app.route('/scut/qstorage', methods=['POST'])
def qstorage():
    data = request.json
    name = request.args.get('name', default="notitleData", type=str)
    action = request.args.get('action', default=1, type=int)
    if action == 1:
        if not data:
            return jsonify({"error": "No data provided"}), 400

        with open(f'data/{name}_q.json', 'w+', encoding='utf-8') as json_file:
            json_origin = json.load(json_file) if os.path.exists(f'data/{name}_q.json') else {}

            json.dump(data, json_file, ensure_ascii=False, indent=4)
        return jsonify({"message": "Data stored successfully"})

    elif action == 0:
        if not os.path.exists(f'data/{name}_q.json'):
            return jsonify({"error": "File not found"}), 404

        with open(f'data/{name}_q.json', 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
        return jsonify(data)
    else:
        return jsonify({"error": "Invalid action"}), 400



def lstorage():
    pass


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
