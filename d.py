import base64

# Thay 'assets/app_icon.ico' bằng đường dẫn đến file icon hiện tại của bạn
with open('assets/app_icon.ico', 'rb') as icon_file:
    encoded_string = base64.b64encode(icon_file.read()).decode('utf-8')
    print("Sao chép chuỗi này:")
    print(encoded_string)
