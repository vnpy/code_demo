import time
import hmac
import hashlib
import base64
import urllib.parse
import requests


url = "https://oapi.dingtalk.com/robot/send?access_token=a521d6c8d27cc04a06c8e6fcc47e3bed89ce34c1c62d4367d25115f0856feab2"
secret = "SECc273f6574c4bc8abe8639d73cbdc86492158a677a178289b91f6308af8ac9379"


def send_ding_msg(msg: str) -> dict:
    """发送钉钉消息"""
    # 结合当前时间戳，生成签名
    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, secret)

    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

    # 请求地址
    msg_url = f"{url}&timestamp={timestamp}&sign={sign}"

    # 请求头部
    header = {
        "Content-Type": "application/json",
        "Charset": "UTF-8"
    }

    # 请求数据
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": "信息",
            "text": msg
        },
        "at": {
            "isAtAll": False
        }
    }

    # 发送请求
    r = requests.post(msg_url, json=data, headers=header)

    return r.json()


if __name__ == "__main__":
    send_ding_msg("test")
