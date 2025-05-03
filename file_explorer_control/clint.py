# client_windows.py
import socket
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTreeView, QFileSystemModel,
                             QSplitter, QListView, QVBoxLayout, QWidget, QToolBar,
                             QAction, QMessageBox, QInputDialog, QLineEdit, QLabel,
                             QHBoxLayout, QFileDialog)
from PyQt5.QtCore import Qt, QModelIndex

class RemoteFileExplorer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.connected = False
        self.current_path = '/'
        
    def initUI(self):
        self.setWindowTitle('مدیریت فایل سرور اوبونتو - کلاینت ویندوز')
        self.setGeometry(100, 100, 800, 600)
        
        # ویجت‌ها
        self.tree_view = QTreeView()
        self.list_view = QListView()
        
        # مدل محلی برای نمایش ساختار درختی
        self.local_model = QFileSystemModel()
        self.local_model.setRootPath("")
        self.tree_view.setModel(self.local_model)
        
        # لیبل وضعیت
        self.status_label = QLabel('وضعیت: قطع ارتباط')
        
        # فیلدهای اتصال
        self.server_ip_label = QLabel('آی‌پی سرور:')
        self.server_ip_input = QLineEdit('51.77.109.238')
        self.server_port_label = QLabel('پورت:')
        self.server_port_input = QLineEdit('5000')
        
        # دکمه اتصال
        self.connect_btn = QPushButton('اتصال به سرور')
        self.connect_btn.clicked.connect(self.toggle_connection)
        
        # لیآوت اتصال
        connection_layout = QHBoxLayout()
        connection_layout.addWidget(self.server_ip_label)
        connection_layout.addWidget(self.server_ip_input)
        connection_layout.addWidget(self.server_port_label)
        connection_layout.addWidget(self.server_port_input)
        connection_layout.addWidget(self.connect_btn)
        connection_layout.addWidget(self.status_label)
        
        # لیآوت اصلی
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.tree_view)
        splitter.addWidget(self.list_view)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(connection_layout)
        main_layout.addWidget(splitter)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        # نوار ابزار
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # اقدامات نوار ابزار
        refresh_action = QAction('تازه‌سازی', self)
        refresh_action.triggered.connect(self.refresh)
        toolbar.addAction(refresh_action)
        
        download_action = QAction('دانلود فایل', self)
        download_action.triggered.connect(self.download_file)
        toolbar.addAction(download_action)
        
        # سیگنال‌ها
        self.tree_view.doubleClicked.connect(self.on_tree_double_click)
        
    def toggle_connection(self):
        if not self.connected:
            self.connect_to_server()
        else:
            self.disconnect_from_server()
            
    def connect_to_server(self):
        self.server_ip = self.server_ip_input.text()
        self.server_port = int(self.server_port_input.text())
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_ip, self.server_port))
            
            self.connected = True
            self.connect_btn.setText('قطع ارتباط')
            self.status_label.setText('وضعیت: متصل')
            
            # دریافت محتوای ریشه
            self.refresh()
            
            QMessageBox.information(self, 'اتصال موفق', 'اتصال به سرور با موفقیت برقرار شد.')
            
        except Exception as e:
            QMessageBox.critical(self, 'خطای اتصال', f'خطا در اتصال به سرور:\n{str(e)}')
            
    def disconnect_from_server(self):
        try:
            self.socket.close()
            self.connected = False
            self.connect_btn.setText('اتصال به سرور')
            self.status_label.setText('وضعیت: قطع ارتباط')
            
        except Exception as e:
            QMessageBox.warning(self, 'هشدار', f'خطا در قطع ارتباط:\n{str(e)}')
            
    def send_command(self, command):
        try:
            self.socket.send(json.dumps(command).encode('utf-8'))
            response = self.socket.recv(8192).decode('utf-8')
            return json.loads(response)
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def refresh(self, path=None):
        if not self.connected:
            QMessageBox.warning(self, 'هشدار', 'لطفاً ابتدا به سرور متصل شوید.')
            return
            
        if path is None:
            path = self.current_path
            
        response = self.send_command({
            'command': 'list_dir',
            'path': path
        })
        
        if response.get('status') == 'success':
            self.current_path = response['path']
            self.display_contents(response)
        else:
            QMessageBox.warning(self, 'خطا', response.get('message', 'خطای نامشخص'))
            
    def display_contents(self, response):
        # اینجا می‌توانید مدل سفارشی برای نمایش محتوای سرور ایجاد کنید
        # برای سادگی، فقط یک پیام نمایش می‌دهیم
        QMessageBox.information(self, 'محتوای دایرکتوری', 
                               f"مسیر: {response['path']}\n"
                               f"پوشه‌ها: {len(response['directories'])}\n"
                               f"فایل‌ها: {len(response['files'])}")
        
    def on_tree_double_click(self, index: QModelIndex):
        if not self.connected:
            return
            
        path = self.local_model.filePath(index)
        if os.path.isdir(path):
            self.refresh(path)
            
    def download_file(self):
        if not self.connected:
            QMessageBox.warning(self, 'هشدار', 'لطفاً ابتدا به سرور متصل شوید.')
            return
            
        file_path, _ = QInputDialog.getText(self, 'دانلود فایل', 'مسیر فایل در سرور:')
        if not file_path:
            return
            
        response = self.send_command({
            'command': 'get_file',
            'path': file_path
        })
        
        if response.get('status') == 'success':
            save_path, _ = QFileDialog.getSaveFileName(self, 'ذخیره فایل', os.path.basename(file_path))
            if save_path:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(response['content'])
                QMessageBox.information(self, 'موفق', 'فایل با موفقیت دانلود شد.')
        else:
            QMessageBox.warning(self, 'خطا', response.get('message', 'خطای نامشخص'))
            
    def closeEvent(self, event):
        if self.connected:
            self.disconnect_from_server()
        event.accept()

if __name__ == '__main__':
    import os
    app = QApplication([])
    explorer = RemoteFileExplorer()
    explorer.show()
    app.exec_()