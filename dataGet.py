
from flask import Flask, request
from scrabbler import Scrabbler

app = Flask(__name__)
scrabbler = Scrabbler()

# 教务处通知栏（含教务学院通知和）
@app.route('/scut/jwnotice', methods=['GET'])
def jwnotice():
    return scrabbler.jwnotice(request)

# 修改headers接口
@app.route('/scut/edit_headers', methods=['POST'])
def edit_headers():
    return scrabbler.edit_headers(request)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)