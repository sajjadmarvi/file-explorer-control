# server_ubuntu.py
import socket
import os
import json
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QVBoxLayout, 
                             QWidget, QPushButton, QLabel, QLineEdit, QMessageBox)

class FileServer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.server_running = False
        self.clients = {}
        
    def initUI(self):
        self.setWindowTitle('سرور مدیریت فایل اوبونتو')
        self.setGeometry(100, 100, 600, 400)
        
        # ویجت‌ها
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        
        self.status_label = QLabel('وضعیت سرور: غیرفعال')
        self.ip_label = QLabel('آی‌پی سرور:')
        self.ip_input = QLineEdit(self.get_local_ip())
        self.port_label = QLabel('پورت:')
        self.port_input = QLineEdit('5000')
        
        self.start_btn = QPushButton('شروع سرور')
        self.start_btn.clicked.connect(self.toggle_server)
        self.stop_btn = QPushButton('توقف سرور')
        self.stop_btn.clicked.connect(self.toggle_server)
        self.stop_btn.setEnabled(False)
        
        # لیآوت
        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.ip_label)
        layout.addWidget(self.ip_input)
        layout.addWidget(self.port_label)
        layout.addWidget(self.port_input)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.log)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return '127.0.0.1'
            
    def log_message(self, message):
        self.log.append(message)
        
    def toggle_server(self):
        if not self.server_running:
            self.start_server()
        else:
            self.stop_server()
            
    def start_server(self):
        self.ip = self.ip_input.text()
        self.port = int(self.port_input.text())
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((self.ip, self.port))
            self.server_socket.listen(5)
            
            self.server_running = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_label.setText('وضعیت سرور: فعال - در حال گوش دادن...')
            self.log_message(f'سرور شروع به کار کرد روی {self.ip}:{self.port}')
            
            # شروع thread برای پذیرش اتصالات
            self.server_thread = threading.Thread(target=self.accept_connections, daemon=True)
            self.server_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, 'خطا', f'خطا در شروع سرور:\n{str(e)}')
            
    def stop_server(self):
        self.server_running = False
        try:
            self.server_socket.close()
            for client in self.clients.values():
                client['socket'].close()
            self.clients = {}
            
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_label.setText('وضعیت سرور: غیرفعال')
            self.log_message('سرور متوقف شد')
            
        except Exception as e:
            QMessageBox.warning(self, 'هشدار', f'خطا در توقف سرور:\n{str(e)}')
            
    def accept_connections(self):
        while self.server_running:
            try:
                client_socket, addr = self.server_socket.accept()
                self.log_message(f'اتصال جدید از {addr[0]}:{addr[1]}')
                
                client_id = f'{addr[0]}:{addr[1]}'
                self.clients[client_id] = {
                    'socket': client_socket,
                    'address': addr
                }
                
                # شروع thread برای مدیریت کلاینت
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, addr),
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                if self.server_running:
                    self.log_message(f'خطا در پذیرش اتصال: {str(e)}')
                    
    def handle_client(self, client_socket, addr):
        client_id = f'{addr[0]}:{addr[1]}'
        try:
            while self.server_running:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                    
                self.log_message(f'پیام از {client_id}: {data}')
                
                try:
                    command = json.loads(data)
                    response = self.process_command(command)
                    client_socket.send(json.dumps(response).encode('utf-8'))
                    
                except json.JSONDecodeError:
                    response = {'status': 'error', 'message': 'دستور نامعتبر'}
                    client_socket.send(json.dumps(response).encode('utf-8'))
                    
        except Exception as e:
            self.log_message(f'خطا در ارتباط با {client_id}: {str(e)}')
        finally:
            client_socket.close()
            if client_id in self.clients:
                del self.clients[client_id]
            self.log_message(f'اتصال با {client_id} بسته شد')
            
    def process_command(self, command):
        try:
            cmd = command.get('command', '')
            
            if cmd == 'list_dir':
                path = command.get('path', '/')
                if not os.path.exists(path):
                    return {'status': 'error', 'message': 'مسیر وجود ندارد'}
                
                items = os.listdir(path)
                dirs = []
                files = []
                
                for item in items:
                    full_path = os.path.join(path, item)
                    if os.path.isdir(full_path):
                        dirs.append({'name': item, 'type': 'directory'})
                    else:
                        files.append({'name': item, 'type': 'file', 'size': os.path.getsize(full_path)})
                
                return {
                    'status': 'success',
                    'path': path,
                    'directories': dirs,
                    'files': files
                }
                
            elif cmd == 'get_file':
                file_path = command.get('path', '')
                if not os.path.exists(file_path):
                    return {'status': 'error', 'message': 'فایل وجود ندارد'}
                
                if os.path.isdir(file_path):
                    return {'status': 'error', 'message': 'مسیر یک دایرکتوری است'}
                
                with open(file_path, 'rb') as f:
                    content = f.read().decode('utf-8', errors='ignore')
                
                return {
                    'status': 'success',
                    'content': content
                }
                
            else:
                return {'status': 'error', 'message': 'دستور نامشخص'}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def closeEvent(self, event):
        if self.server_running:
            self.stop_server()
        event.accept()

if __name__ == '__main__':
    app = QApplication([])
    server = FileServer()
    server.show()
    app.exec_()