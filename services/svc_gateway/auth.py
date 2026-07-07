import jwt
from functools import wraps
from flask import request, jsonify

SECRET_KEY = "fams_secret_key_2024"

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"code": 401, "msg": "未登录"}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user = payload
        except jwt.ExpiredSignatureError:
            return jsonify({"code": 401, "msg": "Token已过期"}), 401
        except Exception:
            return jsonify({"code": 401, "msg": "Token无效"}), 401
        return f(*args, **kwargs)
    return wrapper