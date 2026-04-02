import sys
import json
import os
import logging

# 禁用所有日志输出（包括第三方库）
logging.disable(logging.CRITICAL)

# 如果 hiksdk_camera 会 print()，也要重定向 stdout（可选）
# 但最好让 SDK 本身不 print

"""
该文件用于单个摄像头抓拍一张图片，目前只支持海康威视的摄像头，其他摄像头需要适配。
用法 python3 capture_single.py 192.168.1.100 admin 123456 80 1 /tmp/test.jpg
"""

def main():
    if len(sys.argv) != 7:
        print(json.dumps({"success": False, "error": "Invalid arguments"}))
        return

    ip, username, password, port, channel, img_path = sys.argv[1:7]
    
    try:
        port = int(port)
        channel = int(channel)
    except ValueError:
        print(json.dumps({"success": False, "error": "port or channel not integer"}))
        return

    os.makedirs(os.path.dirname(img_path), exist_ok=True)

    try:
        # 关键：确保 hiksdk_camera 不输出任何 print 或日志！
        from hiksdk_camera import HikvisionCamera
        cam = HikvisionCamera()
        user_id = cam.login_camera(ip, username, password, port)
        if user_id < 0:
            print(json.dumps({"success": False, "error": f"Login failed, code={user_id}"}))
            return

        try:
            result = cam.capture_image(user_id, img_path)
            success = result is not None
            error = None if success else "Capture returned empty result"
        finally:
            cam.logout_camera(user_id)

        print(json.dumps({"success": success, "error": error}))
    except Exception as e:
        # 捕获所有异常，只输出 JSON
        print(json.dumps({"success": False, "error": str(e)}))

if __name__ == "__main__":
    main()