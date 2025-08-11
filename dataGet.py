import requests
from flask import Flask, request, jsonify
from scrabbler import Scrabbler

app = Flask(__name__)
scrabbler = Scrabbler()

def update_rss(name):
    '''
    向rss服务器发送数据更新请求
    :return: 更新结果
    '''
    jsdata = {
        'name': name,
    }
    re = requests.post('http://127.0.0.1:5001/update', json=jsdata)
    return re.json()

# 教务处通知栏（含教务学院通知和）
@app.route('/scut/jwnotice', methods=['GET'])
def jwnotice():
    reData = scrabbler.jwnotice(request) # 传入request对象
    update_re = None
    # 仅当成功抓取数据后更新long storage
    if reData[1] == 200:
        whethernew = reData[0].get('WhetherNew') # 判断是否需要更新RSS
        if whethernew == 1:
            name = request.args.get('name')
            update_re = update_rss(name)
    return jsonify({'getre':reData, 'update_re': update_re if update_re else 'No need to update rss'}) # 返回抓取结果和更新结果


# 后端api
## 修改headers接口
@app.route('/scut/edit_headers', methods=['POST'])
def edit_headers():
    return scrabbler.edit_headers(request)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)