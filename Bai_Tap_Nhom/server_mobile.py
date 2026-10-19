import http.server
import socketserver
import socket
import os
import urllib.parse
import webbrowser

PORT = 8000

def get_ip():
    """Lấy địa chỉ IP mạng LAN / Wi-Fi hiện tại của máy tính"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Làm sạch URL bỏ qua query params
        clean_path = self.path.split('?')[0].rstrip('/')
        
        # Nếu truy cập trang chủ hoặc thư mục web -> chuyển hướng ngay tới Index.html
        if clean_path in ['', '/web', '/Web']:
            self.send_response(302)
            self.send_header('Location', '/Web/Index.html')
            self.end_headers()
            return
            
        # Trang hướng dẫn & quét mã QR tiện lợi
        if clean_path in ['/qr', '/qrcode', '/mobile']:
            ip = get_ip()
            app_url = f"http://{ip}:{PORT}/Web/Index.html"
            qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(app_url)}"
            html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mở WebGIS NTU Trên Điện Thoại</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #e3f2fd 0%, #f0f4f8 100%);
            margin: 0; padding: 25px 15px;
            display: flex; justify-content: center; align-items: center; min-height: 90vh;
        }}
        .card {{
            background: #ffffff;
            max-width: 460px; width: 100%;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            padding: 28px 22px;
            text-align: center;
            box-sizing: border-box;
        }}
        h2 {{ color: #0066cc; margin: 0 0 8px 0; font-size: 22px; }}
        .badge {{
            display: inline-block; background: #e8f4fd; color: #0066cc;
            font-size: 13px; font-weight: 600; padding: 4px 12px; border-radius: 20px; margin-bottom: 15px;
        }}
        .step {{ text-align: left; font-size: 14px; color: #333; line-height: 1.5; margin-bottom: 12px; }}
        .qr-wrapper {{
            background: #fff;
            padding: 10px;
            display: inline-block;
            border-radius: 12px;
            border: 2px dashed #0066cc;
            margin: 10px 0;
        }}
        .qr-wrapper img {{ display: block; border-radius: 6px; }}
        .link-box {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 10px;
            margin: 12px 0;
            font-family: monospace;
            font-size: 16px;
            color: #d63384;
            font-weight: bold;
            word-break: break-all;
        }}
        .tip {{
            background: #fff3cd; color: #856404; font-size: 12px;
            border-radius: 8px; padding: 10px 12px; text-align: left; line-height: 1.4; margin-top: 15px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h2>WebGIS Tìm Đường NTU</h2>
        <div class="badge">Dành cho Điện thoại di động</div>
        
        <div class="step">
            <b>Bước 1:</b> Kết nối điện thoại vào <b>cùng mạng Wi-Fi</b> với máy tính.
        </div>
        <div class="step">
            <b>Bước 2:</b> Dùng Camera điện thoại quét mã QR này:
        </div>
        
        <div class="qr-wrapper">
            <img src="{qr_api}" alt="Mã QR" width="240" height="240">
        </div>
        
        <div class="step" style="text-align: center;">
            Hoặc gõ đường link này vào trình duyệt trên điện thoại:
        </div>
        <div class="link-box">{app_url}</div>
        
        <div class="tip">
            📌 <b>Lưu ý:</b> Trên điện thoại, bạn có thể chạm ngón tay trực tiếp vào bất kỳ tòa nhà hoặc con đường nào trên bản đồ để chọn làm <i>Vị trí hiện tại / Điểm xuất phát</i> rất tiện lợi!
        </div>
    </div>
</body>
</html>"""
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
            return
            
        return super().do_GET()

def run_server():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    
    ip = get_ip()
    mobile_link = f"http://{ip}:{PORT}"
    qr_link = f"http://localhost:{PORT}/qr"
    
    print("=" * 60)
    print("       ĐÃ KHỞI CHẠY MÁY CHỦ CHO ĐIỆN THOẠI THÀNH CÔNG!")
    print("=" * 60)
    print(f" 1. Đảm bảo điện thoại và máy tính BẮT CHUNG MẠNG WI-FI.")
    print(f" 2. Mở trình duyệt trên điện thoại (Safari/Chrome), nhập:")
    print(f"    👉  {mobile_link}")
    print(f"    (Trang web sẽ tự chuyển hướng vào bản đồ WebGIS)")
    print(f"")
    print(f" 3. Hoặc quét mã QR trên màn hình vừa tự động bật trên máy tính:")
    print(f"    👉  {qr_link}")
    print("=" * 60)
    print(" (*) Để dừng máy chủ: Nhấn tổ hợp phím [Ctrl + C] tại cửa sổ này.")
    print("=" * 60)
    
    try:
        webbrowser.open(qr_link)
    except Exception:
        pass

    with socketserver.TCPServer(("0.0.0.0", PORT), CustomHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nĐã tắt máy chủ.")

if __name__ == '__main__':
    run_server()
