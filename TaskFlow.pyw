import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import json
import os
import time
from typing import List, Dict, Optional, Tuple
import calendar

import hashlib

import pystray
from PIL import Image, ImageTk
import threading

class UserManager:
    """用户管理类"""
    
    def __init__(self):
        self.users_file = "users.json"
        self.current_user = None
        self.users = {}
        self.load_users()
        self.config_file = "app_config.json"
        self.load_config()
        
    def load_config(self):
        """加载应用配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except:
                self.config = {}
        else:
            self.config = {}
    
    def save_config(self):

        """保存应用配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
   
    def remember_user(self, username, password):
        """记住用户登录信息"""
        # 对密码进行简单加密（实际应用中应该使用更安全的加密方式）
        import base64
        encoded_password = base64.b64encode(password.encode()).decode()
        self.config['remembered_user'] = {
            'username': username,
            'password': encoded_password,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self.save_config()
    
    def auto_login(self):
        """尝试自动登录"""
        username, password = self.get_remembered_user()
        if username and password:
            return self.login(username, password)
        return False, "无记住的登录信息"
    
    def load_users(self):
        """加载用户数据"""
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            except:
                self.users = {}
    
    def save_users(self):
        """保存用户数据"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存用户数据失败: {e}")
            return False
    
    def hash_password(self, password: str) -> str:
        """密码哈希处理"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register(self, username: str, password: str) -> tuple:
        """用户注册"""
        if not username or not password:
            return False, "用户名和密码不能为空"
        
        if len(username) < 3:
            return False, "用户名至少需要3个字符"
        
        if len(password) < 6:
            return False, "密码至少需要6个字符"
        
        if username in self.users:
            return False, "用户名已存在"
        
        # 创建用户数据
        self.users[username] = {
            'password': self.hash_password(password),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': None
        }
        
        if self.save_users():
            return True, "注册成功"
        else:
            return False, "注册失败，请重试"
    
    def login(self, username: str, password: str) -> tuple:
        """用户登录"""
        if not username or not password:
            return False, "用户名和密码不能为空"
        
        if username not in self.users:
            return False, "用户名不存在"
        
        if self.users[username]['password'] != self.hash_password(password):
            return False, "密码错误"
        
        # 更新最后登录时间
        self.users[username]['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.save_users()
        
        self.current_user = username
        return True, "登录成功"
    
    def logout(self):
        """用户登出"""
        self.current_user = None
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self.current_user is not None
    
    def get_current_user(self) -> Optional[str]:
        """获取当前用户"""
        return self.current_user
    
    def get_user_data_file(self) -> str:
        """获取当前用户的数据文件路径"""
        if self.current_user:
            return f"todo_data_{self.current_user}.json"
        return "todo_data.json"
        
    def forget_user(self):
        """忘记用户登录信息"""
        if 'remembered_user' in self.config:
            del self.config['remembered_user']
            self.save_config()
    
    def get_remembered_user(self):
        """获取记住的用户信息"""
        if 'remembered_user' in self.config:
            remembered = self.config['remembered_user']
            # 检查是否在7天内（可调整）
            try:
                timestamp = datetime.strptime(remembered['timestamp'], '%Y-%m-%d %H:%M:%S')
                if (datetime.now() - timestamp).days <= 7:  # 7天内有效
                    import base64
                    password = base64.b64decode(remembered['password'].encode()).decode()
                    return remembered['username'], password
            except:
                pass
        return None, None
        
class LoginDialog:
    """登录注册对话框"""
    
    def __init__(self, parent, user_manager, on_success_callback):
        self.parent = parent
        self.user_manager = user_manager
        self.on_success_callback = on_success_callback
        
        # 设置颜色
        self.colors = {
            'primary': '#4361ee',
            'primary_light': '#4895ef',
            'success': '#4cc9f0',
            'danger': '#e63946',
            'bg_main': '#f8f9fa',
            'bg_card': '#ffffff',
            'text_dark': '#212529',
            'text_gray': '#6c757d',
            
            # 添加缺失的颜色定义
            'gray_light': '#e9ecef',  # 添加这一行
            'gray': '#adb5bd',       # 添加这一行
            'gray_dark': '#495057'   # 添加这一行
        }
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("用户登录 - TaskFlow")
        self.dialog.configure(bg='#f8f9fa')
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 先计算并设置窗口位置，再设置大小（效仿统计窗口）
        self.center_window()
        
        # 创建界面
        self.setup_ui()
        
        # 确保窗口正确显示
        self.dialog.update_idletasks()
    
    def center_window(self):
        """窗口居中显示 - 修复版本"""
        # 设置窗口大小
        width = 400
        height = 520
        
        # 计算居中位置
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # 一次性设置几何属性（效仿统计窗口）
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def setup_ui(self):
        """设置登录注册界面"""
        # 主容器
        main_frame = tk.Frame(self.dialog, bg=self.colors['bg_main'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 应用标题
        title_frame = tk.Frame(main_frame, bg=self.colors['bg_main'])
        title_frame.pack(fill=tk.X, pady=(0, 30))
        
        title_label = tk.Label(title_frame,
                              text="🔐 TaskFlow",
                              font=('Microsoft YaHei', 24, 'bold'),
                              bg=self.colors['bg_main'],
                              fg=self.colors['primary'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame,
                                 text="请登录或注册以继续",
                                 font=('Microsoft YaHei', 12),
                                 bg=self.colors['bg_main'],
                                 fg=self.colors['text_gray'])
        subtitle_label.pack(pady=(5, 0))
        
        # 登录注册卡片
        card_frame = tk.Frame(main_frame, bg=self.colors['bg_card'], relief=tk.RAISED, bd=1)
        card_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # 选项卡
        self.tab_var = tk.StringVar(value="login")
        
        # 选项卡按钮框架
        tab_frame = tk.Frame(card_frame, bg=self.colors['bg_card'])
        tab_frame.pack(fill=tk.X, padx=20, pady=20)
        
        login_tab = tk.Radiobutton(tab_frame,
                                  text="登录",
                                  variable=self.tab_var,
                                  value="login",
                                  command=self.switch_tab,
                                  font=('Microsoft YaHei', 12, 'bold'),
                                  bg=self.colors['bg_card'],
                                  fg=self.colors['text_dark'],
                                  selectcolor=self.colors['bg_card'],
                                  cursor="hand2")
        login_tab.pack(side=tk.LEFT)
        
        register_tab = tk.Radiobutton(tab_frame,
                                     text="注册",
                                     variable=self.tab_var,
                                     value="register",
                                     command=self.switch_tab,
                                     font=('Microsoft YaHei', 12, 'bold'),
                                     bg=self.colors['bg_card'],
                                     fg=self.colors['text_dark'],
                                     selectcolor=self.colors['bg_card'],
                                     cursor="hand2")
        register_tab.pack(side=tk.LEFT, padx=(20, 0))
        
        # 为选项卡添加悬停效果
        self.setup_tab_hover(login_tab)
        self.setup_tab_hover(register_tab)
        
        # 内容区域
        self.content_frame = tk.Frame(card_frame, bg=self.colors['bg_card'])
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # 状态标签
        self.status_label = tk.Label(card_frame,
                                    text="",
                                    font=('Microsoft YaHei', 10),
                                    bg=self.colors['bg_card'],
                                    fg=self.colors['danger'])
        self.status_label.pack(pady=(0, 10))
        
        # 初始显示登录界面
        self.show_login_form()
        
    def setup_tab_hover(self, radio_button):
        """为选项卡设置悬停效果"""
        original_bg = radio_button.cget('bg')
        original_fg = radio_button.cget('fg')
        
        def on_enter(event):
            if radio_button.cget('state') != 'disabled':
                radio_button.configure(bg=self.colors['gray_light'], fg=self.colors['primary'])
        
        def on_leave(event):
            if radio_button.cget('state') != 'disabled':
                radio_button.configure(bg=original_bg, fg=original_fg)
        
        radio_button.bind("<Enter>", on_enter)
        radio_button.bind("<Leave>", on_leave)
        
    def switch_tab(self):
        """切换选项卡"""
        # 清空状态信息
        self.status_label.config(text="")
        
        # 清空内容区域
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # 显示对应表单
        if self.tab_var.get() == "login":
            self.show_login_form()
        else:
            self.show_register_form()
    
    def show_login_form(self):
        """显示登录表单"""
        # 用户名
        username_label = tk.Label(self.content_frame,
                                 text="用户名:",
                                 font=('Microsoft YaHei', 11),
                                 bg=self.colors['bg_card'],
                                 fg=self.colors['text_dark'])
        username_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.login_username = tk.Entry(self.content_frame,
                                      font=('Microsoft YaHei', 11),
                                      bg='#ffffff',
                                      relief=tk.FLAT,
                                      highlightthickness=1,
                                      highlightcolor=self.colors['primary'])
        self.login_username.pack(fill=tk.X, pady=(0, 15))
        self.login_username.focus()
        
        # 密码
        password_label = tk.Label(self.content_frame,
                                 text="密码:",
                                 font=('Microsoft YaHei', 11),
                                 bg=self.colors['bg_card'],
                                 fg=self.colors['text_dark'])
        password_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.login_password = tk.Entry(self.content_frame,
                                      font=('Microsoft YaHei', 11),
                                      show="*",
                                      bg='#ffffff',
                                      relief=tk.FLAT,
                                      highlightthickness=1,
                                      highlightcolor=self.colors['primary'])
        self.login_password.pack(fill=tk.X, pady=(0, 20))
        
        # 绑定回车键
        self.login_password.bind('<Return>', lambda e: self.do_login())
        
        # 记住登录复选框
        self.remember_var = tk.BooleanVar(value=False)
        
        remember_frame = tk.Frame(self.content_frame, bg=self.colors['bg_card'])
        remember_frame.pack(fill=tk.X, pady=(10, 20))
        
        # 自定义复选框
        self.remember_check = tk.Checkbutton(
            remember_frame,
            text="记住登录",
            variable=self.remember_var,
            font=('Microsoft YaHei', 10),
            bg=self.colors['bg_card'],
            fg=self.colors['text_dark'],
            selectcolor=self.colors['bg_card'],
            activebackground=self.colors['bg_card'],
            activeforeground=self.colors['primary'],
            cursor="hand2"
        )
        self.remember_check.pack(side=tk.LEFT)
        
        # 为复选框添加悬停效果
        self.setup_checkbutton_hover(self.remember_check)
        
        # 检查是否有记住的用户
        remembered_username, _ = self.user_manager.get_remembered_user()
        if remembered_username:
            self.login_username.insert(0, remembered_username)
            self.remember_var.set(True)
        
    def setup_checkbutton_hover(self, checkbutton):
        """为复选框设置悬停效果"""
        original_bg = checkbutton.cget('bg')
        original_fg = checkbutton.cget('fg')
        
        def on_enter(event):
            checkbutton.configure(bg=self.colors['gray_light'], fg=self.colors['primary'])
        
        def on_leave(event):
            checkbutton.configure(bg=original_bg, fg=original_fg)
        
        checkbutton.bind("<Enter>", on_enter)
        checkbutton.bind("<Leave>", on_leave)
    
    def show_register_form(self):
        """显示注册表单"""
        # 用户名
        username_label = tk.Label(self.content_frame,
                                 text="用户名:",
                                 font=('Microsoft YaHei', 11),
                                 bg=self.colors['bg_card'],
                                 fg=self.colors['text_dark'])
        username_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.register_username = tk.Entry(self.content_frame,
                                         font=('Microsoft YaHei', 11),
                                         bg='#ffffff',
                                         relief=tk.FLAT,
                                         highlightthickness=1,
                                         highlightcolor=self.colors['primary'])
        self.register_username.pack(fill=tk.X, pady=(0, 15))
        self.register_username.focus()
        
        # 密码
        password_label = tk.Label(self.content_frame,
                                 text="密码:",
                                 font=('Microsoft YaHei', 11),
                                 bg=self.colors['bg_card'],
                                 fg=self.colors['text_dark'])
        password_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.register_password = tk.Entry(self.content_frame,
                                         font=('Microsoft YaHei', 11),
                                         show="*",
                                         bg='#ffffff',
                                         relief=tk.FLAT,
                                         highlightthickness=1,
                                         highlightcolor=self.colors['primary'])
        self.register_password.pack(fill=tk.X, pady=(0, 15))
        
        # 确认密码
        confirm_label = tk.Label(self.content_frame,
                                text="确认密码:",
                                font=('Microsoft YaHei', 11),
                                bg=self.colors['bg_card'],
                                fg=self.colors['text_dark'])
        confirm_label.pack(anchor=tk.W, pady=(0, 5))
        
        self.register_confirm = tk.Entry(self.content_frame,
                                         font=('Microsoft YaHei', 11),
                                         show="*",
                                         bg='#ffffff',
                                         relief=tk.FLAT,
                                         highlightthickness=1,
                                         highlightcolor=self.colors['primary'])
        self.register_confirm.pack(fill=tk.X, pady=(0, 20))
        
        # 绑定回车键
        self.register_confirm.bind('<Return>', lambda e: self.do_register())
        
    def do_login(self):
        """执行登录操作 - 添加记住登录功能"""
        username = self.login_username.get().strip()
        password = self.login_password.get().strip()
        
        if not username or not password:
            self.status_label.config(text="请输入用户名和密码")
            return
        
        success, message = self.user_manager.login(username, password)
        
        if success:
            # 如果勾选了记住登录，保存用户信息
            if self.remember_var.get():
                self.user_manager.remember_user(username, password)
            else:
                # 如果没有勾选，清除之前记住的信息
                self.user_manager.forget_user()
            
            self.status_label.config(text=message, fg=self.colors['success'])
            self.dialog.after(1000, self.on_success)
        else:
            self.status_label.config(text=message, fg=self.colors['danger'])
    
    def do_register(self):
        """执行注册操作"""
        username = self.register_username.get().strip()
        password = self.register_password.get().strip()
        confirm = self.register_confirm.get().strip()
        
        if not username or not password or not confirm:
            self.status_label.config(text="请填写所有字段")
            return
        
        if password != confirm:
            self.status_label.config(text="两次输入的密码不一致")
            return
        
        success, message = self.user_manager.register(username, password)
        
        if success:
            self.status_label.config(text=message, fg=self.colors['success'])
            # 注册成功后自动切换到登录标签页
            self.dialog.after(1000, lambda: self.tab_var.set("login"))
            self.dialog.after(1200, self.switch_tab)
        else:
            self.status_label.config(text=message, fg=self.colors['danger'])
    
    def on_success(self):
        """登录成功后的回调"""
        self.dialog.destroy()
        self.on_success_callback()

class TodoItem:
    """待办事项项类"""
    def __init__(self, id: int, note: str, date_type: str, 
                 date1: Optional[datetime] = None, date2: Optional[datetime] = None):
        self.id = id
        self.note = note
        self.date_type = date_type  # "instant"、"long" 或 "timeless"
        self.date1 = date1  # 对于即时事项是时间点，对于长期事项是开始时间，无时限任务为None
        self.date2 = date2  # 仅对长期事项有效，是结束时间
        self.completed = False
        self.completed_date = None
        self.created_date = datetime.now()
    
    def to_dict(self) -> Dict:
        """将事项转换为字典格式以便保存"""
        return {
            'id': self.id,
            'note': self.note,
            'date_type': self.date_type,
            'date1': self.date1.strftime('%Y-%m-%d %H:%M') if self.date1 else None,
            'date2': self.date2.strftime('%Y-%m-%d %H:%M') if self.date2 else None,
            'completed': self.completed,
            'completed_date': self.completed_date.strftime('%Y-%m-%d %H:%M') if self.completed_date else None,
            'created_date': self.created_date.strftime('%Y-%m-%d %H:%M')
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TodoItem':
        """从字典创建事项"""
        item = cls(
            id=data['id'],
            note=data['note'],
            date_type=data['date_type']
        )
        
        if data['date1']:
            item.date1 = datetime.strptime(data['date1'], '%Y-%m-%d %H:%M')
        
        if data['date2']:
            item.date2 = datetime.strptime(data['date2'], '%Y-%m-%d %H:%M')
        
        item.completed = data['completed']
        if data['completed_date']:
            item.completed_date = datetime.strptime(data['completed_date'], '%Y-%m-%d %H:%M')
        
        item.created_date = datetime.strptime(data['created_date'], '%Y-%m-%d %H:%M')
        return item
            
    def get_time_info(self) -> Tuple[str, str, str]:
        """
        获取时间信息
        返回: (显示日期, 星期几, 状态信息)
        """
        now = datetime.now()
        
        if self.completed and self.completed_date:
            # 已完成事项的时间显示逻辑
            if self.date_type == "instant":
                due_date = self.date1
                time_diff = self.completed_date - due_date
                total_seconds = time_diff.total_seconds()
                
                # 判断是否准时完成（前后6小时内）
                if abs(total_seconds) <= 6 * 3600:  # 6小时内的完成视为准时
                    if total_seconds < 0:
                        status = "准时完成（提前）"
                    else:
                        status = "准时完成"
                    # 但卡片显示保持原有逻辑
                    if total_seconds < 0:
                        total_seconds = abs(total_seconds)
                        if total_seconds < 3600:
                            minutes = int(total_seconds // 60)
                            status = f"超前完成 {minutes} 分钟"
                        elif total_seconds < 86400:
                            hours = int(total_seconds // 3600)
                            status = f"超前完成 {hours} 小时"
                        else:
                            days = time_diff.days
                            status = f"超前完成 {-days} 天"
                    else:
                        if total_seconds < 3600:
                            minutes = int(total_seconds // 60)
                            status = f"延后完成 {minutes} 分钟"
                        elif total_seconds < 86400:
                            hours = int(total_seconds // 3600)
                            status = f"延后完成 {hours} 小时"
                        else:
                            days = time_diff.days
                            status = f"延后完成 {days} 天"
                else:
                    # 原有逻辑保持不变
                    if total_seconds < 0:
                        total_seconds = abs(total_seconds)
                        if total_seconds < 3600:
                            minutes = int(total_seconds // 60)
                            status = f"超前完成 {minutes} 分钟"
                        elif total_seconds < 86400:
                            hours = int(total_seconds // 3600)
                            status = f"超前完成 {hours} 小时"
                        else:
                            days = time_diff.days
                            status = f"超前完成 {-days} 天"
                    else:
                        if total_seconds < 3600:
                            minutes = int(total_seconds // 60)
                            status = f"延后完成 {minutes} 分钟"
                        elif total_seconds < 86400:
                            hours = int(total_seconds // 3600)
                            status = f"延后完成 {hours} 小时"
                        else:
                            days = time_diff.days
                            status = f"延后完成 {days} 天"
                
                date_str = self.date1.strftime('%Y-%m-%d %H:%M')
                week_day = self.completed_date.strftime('%A')
                
            elif self.date_type == "long":
                due_date = self.date2
                time_diff = self.completed_date - due_date
                total_seconds = time_diff.total_seconds()
                
                # 判断是否准时完成（前后6小时内）
                if abs(total_seconds) <= 6 * 3600:
                    if total_seconds < 0:
                        status = "准时完成（提前）"
                    else:
                        status = "准时完成"
                    # 但卡片显示保持原有逻辑
                    if total_seconds < 0:
                        total_seconds = abs(total_seconds)
                        if total_seconds < 3600:
                            minutes = int(total_seconds // 60)
                            status = f"超前完成 {minutes} 分钟"
                        elif total_seconds < 86400:
                            hours = int(total_seconds // 3600)
                            status = f"超前完成 {hours} 小时"
                        else:
                            days = time_diff.days
                            status = f"超前完成 {-days} 天"
                    else:
                        if total_seconds < 3600:
                            minutes = int(total_seconds // 60)
                            status = f"延后完成 {minutes} 分钟"
                        elif total_seconds < 86400:
                            hours = int(total_seconds // 3600)
                            status = f"延后完成 {hours} 小时"
                        else:
                            days = time_diff.days
                            status = f"延后完成 {days} 天"
                else:
                    # 原有逻辑保持不变
                    if total_seconds < 0:
                        total_seconds = abs(total_seconds)
                        if total_seconds < 3600:
                            minutes = int(total_seconds // 60)
                            status = f"超前完成 {minutes} 分钟"
                        elif total_seconds < 86400:
                            hours = int(total_seconds // 3600)
                            status = f"超前完成 {hours} 小时"
                        else:
                            days = time_diff.days
                            status = f"超前完成 {-days} 天"
                    else:
                        if total_seconds < 3600:
                            minutes = int(total_seconds // 60)
                            status = f"延后完成 {minutes} 分钟"
                        elif total_seconds < 86400:
                            hours = int(total_seconds // 3600)
                            status = f"延后完成 {hours} 小时"
                        else:
                            days = time_diff.days
                            status = f"延后完成 {days} 天"
                
                date_str = f"{self.date1.strftime('%Y-%m-%d')} 至 {self.date2.strftime('%Y-%m-%d')}"
                week_day = self.completed_date.strftime('%A')
                
            else:  # timeless
                date_str = "无时限"
                week_day = self.completed_date.strftime('%A')
                status = f"完成于 {self.completed_date.strftime('%Y-%m-%d %H:%M')}"
            
            return date_str, week_day, status
        
        # 未完成事项的逻辑保持不变...
        # [原有的未完成事项逻辑]
        
        # 未完成事项 - 这是需要修改的部分
        if self.date_type == "instant":
            date_str = self.date1.strftime('%Y-%m-%d %H:%M')
            week_day = self.date1.strftime('%A')
            
            if now < self.date1:
                # 距离开始时间
                time_diff = self.date1 - now
                total_seconds = time_diff.total_seconds()
                
                if total_seconds < 3600:  # 小于1小时
                    minutes = int(total_seconds // 60)
                    status = f"距离截止还有 {minutes} 分钟"
                elif total_seconds < 86400:  # 小于1天
                    hours = int(total_seconds // 3600)
                    status = f"距离截止还有 {hours} 小时"
                else:
                    days = time_diff.days
                    status = f"距离截止还有 {days} 天"
            elif now > self.date1:
                # 已逾期时间
                time_diff = now - self.date1
                total_seconds = time_diff.total_seconds()
                
                if total_seconds < 3600:  # 小于1小时
                    minutes = int(total_seconds // 60)
                    status = f"已逾期 {minutes} 分钟"
                elif total_seconds < 86400:  # 小于1天
                    hours = int(total_seconds // 3600)
                    status = f"已逾期 {hours} 小时"
                else:
                    days = time_diff.days
                    status = f"已逾期 {days} 天"
            else:
                status = "今天到期"
            return date_str, week_day, status
        
        elif self.date_type == "long":
            date_str = f"{self.date1.strftime('%Y-%m-%d')} 至 {self.date2.strftime('%Y-%m-%d')}"
            week_day = self.date1.strftime('%A')
            
            if now < self.date1:
                # 距离开始时间
                time_diff = self.date1 - now
                total_seconds = time_diff.total_seconds()
                
                if total_seconds < 3600:  # 小于1小时
                    minutes = int(total_seconds // 60)
                    status = f"距离开始还有 {minutes} 分钟"
                elif total_seconds < 86400:  # 小于1天
                    hours = int(total_seconds // 3600)
                    status = f"距离开始还有 {hours} 小时"
                else:
                    days = time_diff.days
                    status = f"距离开始还有 {days} 天"
            elif self.date1 <= now <= self.date2:
                # 距离结束时间
                time_diff = self.date2 - now
                total_seconds = time_diff.total_seconds()
                
                if total_seconds < 3600:  # 小于1小时
                    minutes = int(total_seconds // 60)
                    status = f"距离结束还有 {minutes} 分钟"
                elif total_seconds < 86400:  # 小于1天
                    hours = int(total_seconds // 3600)
                    status = f"距离结束还有 {hours} 小时"
                else:
                    days = time_diff.days
                    status = f"距离结束还有 {days} 天"
            else:  # now > self.date2
                # 已逾期时间
                time_diff = now - self.date2
                total_seconds = time_diff.total_seconds()
                
                if total_seconds < 3600:  # 小于1小时
                    minutes = int(total_seconds // 60)
                    status = f"已逾期 {minutes} 分钟"
                elif total_seconds < 86400:  # 小于1天
                    hours = int(total_seconds // 3600)
                    status = f"已逾期 {hours} 小时"
                else:
                    days = time_diff.days
                    status = f"已逾期 {days} 天"
            return date_str, week_day, status
        
        else:  # timeless
            date_str = "无时限"
            week_day = "随时"
            status = "无时间限制"
            return date_str, week_day, status

class ModernButton(tk.Frame):
    """现代化按钮组件"""
    def __init__(self, parent, text, command, bg_color, fg_color="white", width=120, height=40, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)
        
        self.command = command
        self.bg_color = bg_color
        self.hover_color = self.adjust_color(bg_color, 20)  # 悬停时变亮
        
        # 创建画布
        self.canvas = tk.Canvas(self, width=width, height=height, bg=bg_color, highlightthickness=0)
        self.canvas.pack()
        
        # 绘制圆角矩形
        self.rect = self.canvas.create_rectangle(0, 0, width, height, fill=bg_color, outline=bg_color, width=0)
        self.text = self.canvas.create_text(width/2, height/2, text=text, fill=fg_color, font=('Microsoft YaHei', 10, 'bold'))
        
        # 绑定事件
        self.canvas.bind("<Enter>", self.on_enter)
        self.canvas.bind("<Leave>", self.on_leave)
        self.canvas.bind("<Button-1>", self.on_click)
        
        # 配置大小
        self.config(width=width, height=height)
        
    def on_enter(self, event):
        """鼠标进入时效果"""
        self.canvas.config(bg=self.hover_color)
        self.canvas.itemconfig(self.rect, fill=self.hover_color, outline=self.hover_color)
        
    def on_leave(self, event):
        """鼠标离开时效果"""
        self.canvas.config(bg=self.bg_color)
        self.canvas.itemconfig(self.rect, fill=self.bg_color, outline=self.bg_color)
        
    def on_click(self, event):
        """点击时效果"""
        self.canvas.itemconfig(self.rect, fill=self.adjust_color(self.bg_color, -20))
        self.canvas.after(100, lambda: self.canvas.itemconfig(self.rect, fill=self.hover_color))
        self.command()
        
    def adjust_color(self, color, delta):
        """调整颜色亮度"""
        if isinstance(color, str) and color.startswith("#"):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            
            r = max(0, min(255, r + delta))
            g = max(0, min(255, g + delta))
            b = max(0, min(255, b + delta))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        return color

class TodoApp:
    """待办事项应用主类"""
        
    def __init__(self, root):
        self.root = root
        self.root.title("待办事项管理器 - TaskFlow")
        self.root.geometry("1320x880")
        self.root.configure(bg='#f8f9fa')
        
        # 初始化用户管理器
        self.user_manager = UserManager()
        
        # 设置图标
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 添加托盘图标相关变量
        self.tray_icon = None
        self.is_minimized_to_tray = False
        
        # 修改窗口关闭行为
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        
        # 检查自动登录
        if not self.user_manager.is_logged_in():
            # 尝试自动登录
            auto_success, auto_message = self.user_manager.auto_login()
            if auto_success:
                # 自动登录成功，直接初始化应用
                self.initialize_application()
                return
        
        # 检查登录状态
        if not self.user_manager.is_logged_in():
            # 显示登录对话框
            self.show_login_dialog()
            return
        
        # 如果已登录，继续初始化应用
        self.initialize_application()
    
    def minimize_to_tray(self):
        """最小化到系统托盘 - 添加渐变效果"""
        def fade_out_window():
            """窗口渐变消失效果"""
            current_alpha = self.root.attributes('-alpha')
            
            def fade_step(alpha):
                try:
                    if alpha > 0:
                        self.root.attributes('-alpha', alpha)
                        # 每15毫秒减少0.1透明度
                        self.root.after(15, lambda: fade_step(alpha - 0.1))
                    else:
                        # 渐变完成后隐藏窗口并创建托盘图标
                        self.root.withdraw()
                        self.is_minimized_to_tray = True
                        self.create_tray_icon()
                except Exception as e:
                    # 如果渐变过程中出错，直接隐藏窗口
                    self.root.withdraw()
                    self.is_minimized_to_tray = True
                    self.create_tray_icon()
            
            # 开始渐变
            fade_step(current_alpha)
        
        # 开始渐变消失
        fade_out_window()

    def show_app(self, icon=None, item=None):
        """显示应用界面 - 修复托盘图标停止时机"""
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
            
        # 先显示窗口但设置为透明
        self.root.deiconify()
        self.root.attributes('-alpha', 0.0)
        self.root.lift()
        self.root.focus_force()
        
        # 添加渐变显示效果
        self.fade_in_window()
        
        self.is_minimized_to_tray = False

    def fade_in_window(self):
        """渐变显示窗口 - 优化版本"""
        def fade_step(alpha=0.0):
            try:
                self.root.attributes('-alpha', alpha)
                if alpha < 1.0:
                    # 每15毫秒增加0.1透明度
                    self.root.after(15, lambda: fade_step(alpha + 0.1))
                else:
                    # 渐变完成后强制重绘界面
                    self.force_redraw()
            except Exception as e:
                # 如果渐变过程中出错，确保窗口完全显示
                self.root.attributes('-alpha', 1.0)
        
        # 开始渐变
        fade_step(0.1)
        
    def create_tray_icon(self):
        """创建系统托盘图标"""
        # 加载图标
        try:
            if os.path.exists("icon.ico"):
                image = Image.open("icon.ico")
            else:
                # 创建一个简单的默认图标
                image = Image.new('RGB', (64, 64), color='#4361ee')
        except:
            # 创建默认图标
            image = Image.new('RGB', (64, 64), color='#4361ee')
        
        # 创建托盘菜单
        menu = pystray.Menu(
            pystray.MenuItem("显示应用界面", self.show_app, default=True),
            pystray.MenuItem("退出", self.quit_app)
        )
        
        # 创建托盘图标
        self.tray_icon = pystray.Icon("TaskFlow", image, "TaskFlow", menu)
        
        # 在单独的线程中运行托盘图标
        def run_tray():
            self.tray_icon.run()
        
        tray_thread = threading.Thread(target=run_tray, daemon=True)
        tray_thread.start()

    def quit_app(self, icon=None, item=None):
        """退出应用"""
        if self.tray_icon:
            self.tray_icon.stop()
        
        # 保存数据
        self.save_data()
        
        # 退出应用
        self.root.quit()
        self.root.destroy()
           
    def on_closing(self):
        """原有的关闭方法，现在用于菜单中的退出功能"""
        self.quit_app()

    def switch_user(self):
        """切换用户 - 修复托盘图标问题"""
        if messagebox.askyesno("切换用户", "确定要切换用户吗？当前用户的数据将会自动保存。"):
            # 如果存在托盘图标，先关闭
            if self.tray_icon:
                self.tray_icon.stop()
                self.tray_icon = None
            
            # 保存当前数据
            self.save_data()
            
            # 清除记住的登录信息
            self.user_manager.forget_user()
            
            # 登出当前用户
            self.user_manager.logout()
            
            # 隐藏菜单
            self.hide_user_menu()
            
            # 清空主界面内容
            self.clear_main_interface()
            
            # 显示登录对话框
            self.show_login_dialog()

    def show_login_dialog(self):
        """显示登录对话框 - 修复版本"""
        # 确保窗口显示
        self.root.deiconify()
        
        def on_login_success():
            """登录成功后的回调"""
            # 登录成功后重新初始化应用
            self.initialize_application()
            # 安全地更新状态标签
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.config(text="✅ 用户切换成功")
        
        def on_login_cancel():
            """登录取消后的处理 - 直接渐变关闭"""
            def fade_out(alpha=1.0):
                """透明度渐变关闭效果"""
                try:
                    if alpha > 0:
                        self.root.attributes('-alpha', alpha)
                        # 每20毫秒减少0.1透明度
                        self.root.after(20, lambda: fade_out(alpha - 0.1))
                    else:
                        # 渐变完成后直接退出
                        self.root.quit()
                except Exception as e:
                    # 如果渐变过程中出错，直接退出
                    self.root.quit()
            
            # 开始渐变关闭
            fade_out()
        
        # 创建登录对话框
        self.login_dialog = LoginDialog(self.root, self.user_manager, on_login_success)
        
        # 监听对话框关闭事件
        self.login_dialog.dialog.protocol("WM_DELETE_WINDOW", on_login_cancel)
    
    def on_login_dialog_close(self):
        """登录对话框关闭事件 - 简化版本"""
        # 直接销毁对话框，不进行任何界面操作
        if hasattr(self, 'login_dialog') and self.login_dialog:
            self.login_dialog.dialog.destroy()
    
    def initialize_application(self):
        """初始化应用主界面"""
        # 设置颜色方案 - 必须先设置
        self.setup_colors()
        
        # 设置字体
        self.setup_fonts()
        
        # 设置样式
        self.setup_styles()
        
        # 数据存储 - 使用用户特定的数据文件
        self.todo_items: List[TodoItem] = []
        self.completed_items: List[TodoItem] = []
        self.next_id = 1
        self.data_file = self.user_manager.get_user_data_file()  # 用户特定数据文件
        
        # 加载已有数据
        self.load_data()
        
        # 创建界面
        self.setup_ui()
        
        # 刷新显示
        self.refresh_display()       
    
    def setup_colors(self):
        """设置颜色方案 - 必须先设置"""
        self.colors = {
            # 主色调
            'primary': '#4361ee',
            'primary_light': '#4895ef',
            'primary_dark': '#3a0ca3',
            
            # 辅助色
            'secondary': '#7209b7',
            'success': '#4cc9f0',
            'warning': '#f72585',
            'danger': '#e63946',
            'info': '#4895ef',
            
            # 中性色
            'light': '#f8f9fa',
            'gray_light': '#e9ecef',
            'gray': '#adb5bd',
            'gray_dark': '#495057',
            'dark': '#212529',
            
            # 状态色
            'todo_bg': '#ffffff',
            'completed_bg': '#f1faee',
            'overdue_bg': '#ffccd5',
            'ongoing_bg': '#caf0f8',
            'upcoming_bg': '#e9ecef',
            'timeless_bg': '#f0f4f8',
            
            # 卡片阴影
            'card_shadow': '#dee2e6',
            
            # 背景
            'bg_main': '#f8f9fa',
            'bg_sidebar': '#ffffff',
            'bg_card': '#ffffff',
        }

    def setup_fonts(self):
        """设置字体，支持中文"""
        # 定义字体
        self.fonts = {
            'title': ('Microsoft YaHei', 24, 'bold'),
            'subtitle': ('Microsoft YaHei', 14, 'bold'),
            'normal': ('Microsoft YaHei', 11),
            'small': ('Microsoft YaHei', 10),
            'bold': ('Microsoft YaHei', 11, 'bold'),
            'monospace': ('Cascadia Code', 10)
        }
        
        # 设置tkinter默认字体
        default_font = ('Microsoft YaHei', 10)
        self.root.option_add('*Font', default_font)

    def setup_styles(self):
        """设置ttk样式"""
        style = ttk.Style()
        
        # 尝试使用clam主题，如果可用的话
        try:
            style.theme_use('clam')
        except:
            pass
        
        # 配置按钮样式
        style.configure('Primary.TButton',
                       font=self.fonts['normal'],
                       padding=10,
                       background=self.colors['primary'],
                       foreground='white',
                       borderwidth=0,
                       focusthickness=3,
                       focuscolor='none')
        
        style.map('Primary.TButton',
                 background=[('active', self.colors['primary_light']),
                           ('disabled', self.colors['gray']),
                           ('pressed', self.colors['primary_dark'])])
        
        style.configure('Secondary.TButton',
                       font=self.fonts['normal'],
                       padding=8,
                       background=self.colors['light'],
                       foreground=self.colors['dark'],
                       borderwidth=1,
                       bordercolor=self.colors['gray'])
        
        # 配置标签样式
        style.configure('Title.TLabel',
                       font=self.fonts['title'],
                       background=self.colors['bg_main'],
                       foreground=self.colors['primary_dark'])
        
        style.configure('Subtitle.TLabel',
                       font=self.fonts['subtitle'],
                       background=self.colors['bg_main'],
                       foreground=self.colors['gray_dark'])
        
        # 配置框架样式
        style.configure('Card.TFrame',
                       background=self.colors['bg_card'],
                       relief='flat',
                       borderwidth=1)
        
        style.configure('Sidebar.TFrame',
                       background=self.colors['bg_sidebar'],
                       relief='flat')

    def create_rounded_frame(self, parent, bg_color, radius=15, **kwargs):
        """创建圆角框架"""
        frame = tk.Frame(parent, bg=bg_color, **kwargs)
        
        def draw_rounded_rect(canvas, width, height, radius, **kwargs):
            points = [
                radius, 0,
                width - radius, 0,
                width, radius,
                width, height - radius,
                width - radius, height,
                radius, height,
                0, height - radius,
                0, radius
            ]
            return canvas.create_polygon(points, smooth=True, **kwargs)
        
        # 创建画布
        canvas = tk.Canvas(frame, bg=bg_color, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        # 绘制圆角矩形
        canvas.bind("<Configure>", 
                   lambda e: draw_rounded_rect(canvas, e.width, e.height, radius, 
                                             fill=bg_color, outline=self.colors['gray_light']))
        
        return frame, canvas

    def setup_ui(self):
        """设置用户界面 - 添加悬停效果"""
        # 主容器
        main_container = tk.Frame(self.root, bg=self.colors['bg_main'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题栏
        title_frame = tk.Frame(main_container, bg=self.colors['bg_main'])
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 应用标题
        title_label = tk.Label(title_frame, 
                              text="📋TaskFlow 待办事项管理器",
                              font=self.fonts['title'],
                              bg=self.colors['bg_main'],
                              fg=self.colors['primary_dark'])
        title_label.pack(side=tk.LEFT)
        
        # 用户信息和当前日期
        info_frame = tk.Frame(title_frame, bg=self.colors['bg_main'])
        info_frame.pack(side=tk.RIGHT)
        
        # 当前日期
        current_date = datetime.now().strftime("%Y年%m月%d日 %A")
        date_label = tk.Label(info_frame,
                             text=f"📅{current_date}",
                             font=self.fonts['small'],
                             bg=self.colors['bg_main'],
                             fg=self.colors['gray_dark'])
        date_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 用户信息区域 - 修改为下拉菜单样式
        self.user_info_frame = tk.Frame(info_frame, bg=self.colors['bg_main'], cursor="hand2")
        self.user_info_frame.pack(side=tk.RIGHT)
        
        # 用户图标和名称
        user_info = f"👤{self.user_manager.get_current_user()}"
        self.user_label = tk.Label(self.user_info_frame,
                                 text=user_info,
                                 font=self.fonts['bold'],
                                 bg=self.colors['bg_main'],
                                 fg=self.colors['secondary'],
                                 cursor="hand2")
        self.user_label.pack(side=tk.LEFT)
    
        # 下拉箭头
        self.arrow_label = tk.Label(self.user_info_frame,
                                   text="▼",
                                   font=('Microsoft YaHei', 8),
                                   bg=self.colors['bg_main'],
                                   fg=self.colors['secondary'],
                                   cursor="hand2")
        self.arrow_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 绑定点击事件
        self.user_label.bind("<Button-1>", self.toggle_user_menu)
        self.arrow_label.bind("<Button-1>", self.toggle_user_menu)
        self.user_info_frame.bind("<Button-1>", self.toggle_user_menu)
        
        # 用户菜单框架（初始隐藏）
        self.user_menu_frame = None
        self.user_menu_visible = False
        
        # 主要内容区域
        content_frame = tk.Frame(main_container, bg=self.colors['bg_main'])
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：添加事项区域
        left_frame = tk.Frame(content_frame, bg=self.colors['bg_sidebar'])
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        
        # 添加事项卡片
        add_card, add_canvas = self.create_rounded_frame(left_frame, self.colors['bg_card'], radius=12)
        add_card.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # 卡片标题
        add_title = tk.Label(add_canvas, 
                            text="添加新任务",
                            font=self.fonts['subtitle'],
                            bg=self.colors['bg_card'],
                            fg=self.colors['primary'])
        add_title_window = add_canvas.create_window(20, 20, window=add_title, anchor=tk.NW)
        
        # 备注输入
        note_label = tk.Label(add_canvas, 
                             text="任务描述:",
                             font=self.fonts['bold'],
                             bg=self.colors['bg_card'],
                             fg=self.colors['gray_dark'])
        note_label_window = add_canvas.create_window(20, 60, window=note_label, anchor=tk.NW)
        
        self.note_text = tk.Text(add_canvas, 
                                height=4, 
                                width=30, 
                                font=self.fonts['normal'],
                                bg=self.colors['light'],
                                fg=self.colors['dark'],
                                relief=tk.FLAT,
                                padx=10,
                                pady=10,
                                highlightthickness=1,
                                highlightcolor=self.colors['primary'],
                                highlightbackground=self.colors['gray'])
        self.note_text_window = add_canvas.create_window(20, 90, window=self.note_text, anchor=tk.NW)
        
        # 事项类型选择
        type_label = tk.Label(add_canvas,
                             text="任务类型:",
                             font=self.fonts['bold'],
                             bg=self.colors['bg_card'],
                             fg=self.colors['gray_dark'])
        type_label_window = add_canvas.create_window(20, 180, window=type_label, anchor=tk.NW)
        
        self.todo_type = tk.StringVar(value="instant")
        
        # 创建单选按钮的样式框架
        type_frame = tk.Frame(add_canvas, bg=self.colors['bg_card'])
        type_frame_window = add_canvas.create_window(20, 210, window=type_frame, anchor=tk.NW)
        
        # 即时事项单选按钮
        instant_frame = tk.Frame(type_frame, bg=self.colors['bg_card'])
        instant_frame.pack(side=tk.LEFT, padx=(0,0))
        
        self.instant_radio = tk.Radiobutton(instant_frame,
                                           text="⏰即时任务",
                                           variable=self.todo_type,
                                           value="instant",
                                           command=self.toggle_date_fields,
                                           font=self.fonts['normal'],
                                           bg=self.colors['bg_card'],
                                           fg=self.colors['dark'],
                                           selectcolor=self.colors['bg_card'],
                                           activebackground=self.colors['bg_card'],
                                           activeforeground=self.colors['primary'],
                                           cursor="hand2")  # 添加手型光标
        self.instant_radio.pack()
        
        # 长期事项单选按钮
        long_frame = tk.Frame(type_frame, bg=self.colors['bg_card'])
        long_frame.pack(side=tk.LEFT, padx=(0,0))
        
        self.long_radio = tk.Radiobutton(long_frame,
                                        text="📅长期任务",
                                        variable=self.todo_type,
                                        value="long",
                                        command=self.toggle_date_fields,
                                        font=self.fonts['normal'],
                                        bg=self.colors['bg_card'],
                                        fg=self.colors['dark'],
                                        selectcolor=self.colors['bg_card'],
                                        activebackground=self.colors['bg_card'],
                                        activeforeground=self.colors['primary'],
                                        cursor="hand2")  # 添加手型光标
        self.long_radio.pack()
        
        # 无时限事项单选按钮
        timeless_frame = tk.Frame(type_frame, bg=self.colors['bg_card'])
        timeless_frame.pack(side=tk.LEFT)
        
        self.timeless_radio = tk.Radiobutton(timeless_frame,
                                            text="∞无时限任务",
                                            variable=self.todo_type,
                                            value="timeless",
                                            command=self.toggle_date_fields,
                                            font=self.fonts['normal'],
                                            bg=self.colors['bg_card'],
                                            fg=self.colors['dark'],
                                            selectcolor=self.colors['bg_card'],
                                            activebackground=self.colors['bg_card'],
                                            activeforeground=self.colors['primary'],
                                            cursor="hand2")  # 添加手型光标
        self.timeless_radio.pack()
        
        # 为单选按钮添加悬停效果
        self.setup_radio_hover(self.instant_radio)
        self.setup_radio_hover(self.long_radio)
        self.setup_radio_hover(self.timeless_radio)
        
        # 日期时间输入框架
        self.date_frame = tk.Frame(add_canvas, bg=self.colors['bg_card'])
        self.date_frame_window = add_canvas.create_window(20, 250, window=self.date_frame, anchor=tk.NW)
        
        # 日期输入组件
        self.setup_date_widgets()
        
        # 统计卡片
        stats_card, stats_canvas = self.create_rounded_frame(left_frame, self.colors['bg_card'], radius=12)
        stats_card.pack(fill=tk.X, pady=(0, 0))

        # 统计标题
        stats_title = tk.Label(stats_canvas,
                              text="📊快速统计",
                              font=self.fonts['subtitle'],
                              bg=self.colors['bg_card'],
                              fg=self.colors['primary'])
        stats_title_window = stats_canvas.create_window(20, 20, window=stats_title, anchor=tk.NW)

        # 统计信息框架
        stats_info_frame = tk.Frame(stats_canvas, bg=self.colors['bg_card'])
        stats_info_window = stats_canvas.create_window(20, 60, window=stats_info_frame, anchor=tk.NW)

        # 简化显示：只显示总数
        self.todo_count_label = tk.Label(stats_info_frame,
                                        text="待办: 0",
                                        font=self.fonts['normal'],
                                        bg=self.colors['bg_card'],
                                        fg=self.colors['primary'])
        self.todo_count_label.pack(anchor=tk.W, pady=5)

        self.completed_count_label = tk.Label(stats_info_frame,
                                            text="已完成: 0",
                                            font=self.fonts['normal'],
                                            bg=self.colors['bg_card'],
                                            fg=self.colors['success'])
        self.completed_count_label.pack(anchor=tk.W, pady=5)

        # 添加查看详细统计的链接
        view_details_label = tk.Label(stats_info_frame,
                                     text="点击底部'📊任务统计'查看详情",
                                     font=('Microsoft YaHei', 8),
                                     bg=self.colors['bg_card'],
                                     fg=self.colors['gray'],
                                     cursor="hand2")
        view_details_label.pack(anchor=tk.W, pady=(10, 5))
        view_details_label.bind("<Button-1>", lambda e: self.show_task_statistics())
        
        # 为统计卡片添加悬停效果
        self.setup_card_hover(stats_card, stats_canvas)
        
        # 中间和右侧：任务列表区域
        tasks_frame = tk.Frame(content_frame, bg=self.colors['bg_main'])
        tasks_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 标签页容器
        notebook = ttk.Notebook(tasks_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 设置选项卡样式
        self.setup_notebook_style(notebook)
        
        # 待办事项标签页
        todo_tab = tk.Frame(notebook, bg=self.colors['bg_main'])
        notebook.add(todo_tab, text=f"📋待办事项 ({len(self.todo_items)})")
        
        # 已完成事项标签页
        completed_tab = tk.Frame(notebook, bg=self.colors['bg_main'])
        notebook.add(completed_tab, text=f"✅已完成 ({len(self.completed_items)})")
        
        # 待办事项滚动区域
        todo_canvas_frame = tk.Frame(todo_tab, bg=self.colors['bg_main'])
        todo_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建Canvas和Scrollbar
        self.todo_canvas = tk.Canvas(todo_canvas_frame, bg=self.colors['bg_main'], highlightthickness=0)
        todo_scrollbar = ttk.Scrollbar(todo_canvas_frame, orient="vertical", command=self.todo_canvas.yview)
        
        # 创建可滚动的框架
        self.todo_container = tk.Frame(self.todo_canvas, bg=self.colors['bg_main'])
        self.todo_container.bind(
            "<Configure>",
            lambda e: self.todo_canvas.configure(scrollregion=self.todo_canvas.bbox("all"))
        )
        
        # 创建Canvas窗口
        self.todo_canvas.create_window((0, 0), window=self.todo_container, anchor="nw")
        self.todo_canvas.configure(yscrollcommand=todo_scrollbar.set)
        
        # 布置Canvas和Scrollbar
        self.todo_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        todo_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定鼠标滚轮
        self.todo_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # 已完成事项滚动区域
        completed_canvas_frame = tk.Frame(completed_tab, bg=self.colors['bg_main'])
        completed_canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建Canvas和Scrollbar
        self.completed_canvas = tk.Canvas(completed_canvas_frame, bg=self.colors['bg_main'], highlightthickness=0)
        completed_scrollbar = ttk.Scrollbar(completed_canvas_frame, orient="vertical", command=self.completed_canvas.yview)
        
        # 创建可滚动的框架
        self.completed_container = tk.Frame(self.completed_canvas, bg=self.colors['bg_main'])
        self.completed_container.bind(
            "<Configure>",
            lambda e: self.completed_canvas.configure(scrollregion=self.completed_canvas.bbox("all"))
        )
        
        # 创建Canvas窗口
        self.completed_canvas.create_window((0, 0), window=self.completed_container, anchor="nw")
        self.completed_canvas.configure(yscrollcommand=completed_scrollbar.set)
        
        # 布置Canvas和Scrollbar
        self.completed_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        completed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 底部控制栏
        control_frame = tk.Frame(main_container, bg=self.colors['bg_main'])
        control_frame.pack(fill=tk.X, pady=(20, 0))
        
        # 控制按钮
        button_container = tk.Frame(control_frame, bg=self.colors['bg_main'])
        button_container.pack()
        
        # 添加任务按钮
        add_button = ModernButton(button_container,
                                 text="➕添加任务",
                                 command=self.add_todo_item,
                                 bg_color=self.colors['primary'],
                                 width=100,
                                 height=35)
        add_button.pack(side=tk.LEFT, padx=5)
        
        # 刷新按钮 - 使用增强的刷新功能
        refresh_button = ModernButton(button_container,
                                     text="🔄刷新",
                                     command=self.enhanced_refresh,
                                     bg_color=self.colors['info'],
                                     width=100,
                                     height=35)
        refresh_button.pack(side=tk.LEFT, padx=5)
        
        # 任务统计按钮
        stats_button = ModernButton(button_container,
                                  text="📊任务统计",
                                  command=self.show_task_statistics,
                                  bg_color=self.colors['secondary'],
                                  width=100,
                                  height=35)
        stats_button.pack(side=tk.LEFT, padx=5)
        
        # 导出未完成任务按钮
        export_button = ModernButton(button_container,
                                   text="📤导出未完成",
                                   command=self.export_pending_tasks,
                                   bg_color=self.colors['success'],
                                   width=120,
                                   height=35)
        export_button.pack(side=tk.LEFT, padx=5)
        
        # 清空已完成按钮
        clear_button = ModernButton(button_container,
                                   text="🗑清空已完成",
                                   command=self.clear_completed,
                                   bg_color=self.colors['warning'],
                                   width=120,
                                   height=35)
        clear_button.pack(side=tk.LEFT, padx=5)
        
        # 退出按钮
        exit_button = ModernButton(button_container,
                                  text="🚪退出",
                                  command=self.on_closing,
                                  bg_color=self.colors['danger'],
                                  width=100,
                                  height=35)
        exit_button.pack(side=tk.LEFT, padx=5)
        
        # 状态标签
        self.status_label = tk.Label(control_frame,
                                    text="✅就绪",
                                    font=self.fonts['small'],
                                    bg=self.colors['bg_main'],
                                    fg=self.colors['gray_dark'])
        self.status_label.pack(side=tk.RIGHT, pady=5)
        
        # 绑定标签页切换事件
        notebook.bind("<<NotebookTabChanged>>", lambda e: self.on_tab_changed(notebook))

    # 添加用户菜单相关的方法
    def create_user_menu(self):
        """创建用户下拉菜单"""
        if self.user_menu_frame and self.user_menu_frame.winfo_exists():
            return self.user_menu_frame
        
        # 获取用户信息框架的位置
        user_frame = self.user_info_frame
        x = user_frame.winfo_rootx() - self.root.winfo_rootx()
        y = user_frame.winfo_rooty() - self.root.winfo_rooty() + user_frame.winfo_height()
        
        # 创建菜单框架
        menu_frame = tk.Frame(self.root, 
                             bg=self.colors['bg_card'],
                             relief=tk.RAISED,
                             bd=1,
                             highlightthickness=1,
                             highlightcolor=self.colors['primary_light'])
        
        # 设置菜单位置
        menu_frame.place(x=x, y=y, width=180, height=130)
        
        # 菜单标题
        title_frame = tk.Frame(menu_frame, bg=self.colors['primary_light'], height=30)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame,
                              text="用户菜单",
                              font=self.fonts['bold'],
                              bg=self.colors['primary_light'],
                              fg='white')
        title_label.pack(expand=True)
        
        # 菜单内容
        content_frame = tk.Frame(menu_frame, bg=self.colors['bg_card'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 菜单项框架
        menu_items_frame = tk.Frame(content_frame, bg=self.colors['bg_card'])
        menu_items_frame.pack(fill=tk.X)
        
        # 检查是否有记住的登录信息
        remembered_username, _ = self.user_manager.get_remembered_user()
        
        if remembered_username:
            # 忘记登录按钮
            forget_btn = self.create_menu_item(menu_items_frame, "🔓 忘记登录", self.forget_login)
            forget_btn.pack(fill=tk.X, pady=2)
        
        # 切换用户按钮
        switch_btn = self.create_menu_item(menu_items_frame, "🔄 切换用户", self.switch_user)
        switch_btn.pack(fill=tk.X, pady=2)
        
        # 退出按钮
        exit_btn = self.create_menu_item(menu_items_frame, "🚪 退出应用", self.on_closing)
        exit_btn.pack(fill=tk.X, pady=2)
        
        return menu_frame

    def create_menu_item(self, parent, text, command):
        """创建菜单项按钮"""
        frame = tk.Frame(parent, bg=self.colors['bg_card'], height=25)
        frame.pack_propagate(False)
        
        # 按钮标签
        btn = tk.Label(frame,
                      text=text,
                      font=self.fonts['small'],
                      bg=self.colors['bg_card'],
                      fg=self.colors['dark'],
                      cursor="hand2",
                      anchor=tk.W)
        btn.pack(fill=tk.BOTH, expand=True, padx=5)
        
        # 绑定事件
        btn.bind("<Button-1>", lambda e: command())
        frame.bind("<Button-1>", lambda e: command())
        
        # 悬停效果
        def on_enter(e):
            frame.configure(bg=self.colors['gray_light'])
            btn.configure(bg=self.colors['gray_light'])
        
        def on_leave(e):
            frame.configure(bg=self.colors['bg_card'])
            btn.configure(bg=self.colors['bg_card'])
        
        for widget in [frame, btn]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
        
        return frame

    def toggle_user_menu(self, event=None):
        """切换用户菜单显示状态"""
        if self.user_menu_visible:
            self.hide_user_menu()
        else:
            self.show_user_menu()

    def show_user_menu(self):
        """显示用户菜单"""
        if self.user_menu_visible:
            return
            
        self.user_menu_frame = self.create_user_menu()
        self.user_menu_visible = True
        
        # 更新箭头方向
        self.arrow_label.config(text="▲")
        
        # 绑定全局点击事件来关闭菜单
        self.root.bind("<Button-1>", self.check_menu_click)

    def hide_user_menu(self):
        """隐藏用户菜单"""
        if self.user_menu_frame and self.user_menu_frame.winfo_exists():
            self.user_menu_frame.destroy()
        self.user_menu_visible = False
        self.arrow_label.config(text="▼")
        
        # 解绑全局点击事件
        self.root.unbind("<Button-1>")

    def check_menu_click(self, event):
        """检查点击事件，如果点击在菜单外部则关闭菜单"""
        if self.user_menu_frame and self.user_menu_frame.winfo_exists():
            # 获取菜单框架的几何信息
            menu_x = self.user_menu_frame.winfo_x()
            menu_y = self.user_menu_frame.winfo_y()
            menu_width = self.user_menu_frame.winfo_width()
            menu_height = self.user_menu_frame.winfo_height()
            
            # 获取用户信息框架的几何信息
            user_x = self.user_info_frame.winfo_x()
            user_y = self.user_info_frame.winfo_y()
            user_width = self.user_info_frame.winfo_width()
            user_height = self.user_info_frame.winfo_height()
            
            # 检查点击是否在菜单或用户信息区域外
            click_in_menu = (menu_x <= event.x <= menu_x + menu_width and 
                            menu_y <= event.y <= menu_y + menu_height)
            click_in_user = (user_x <= event.x <= user_x + user_width and 
                            user_y <= event.y <= user_y + user_height)
            
            if not click_in_menu and not click_in_user:
                self.hide_user_menu()

    def setup_date_widgets(self):
        """设置日期时间输入组件"""
        # 清除现有组件
        for widget in self.date_frame.winfo_children():
            widget.destroy()
        
        if self.todo_type.get() == "instant":
            # 即时事项：单个日期时间
            # 日期标签
            date_label = tk.Label(self.date_frame,
                                 text="📅 截止日期:",
                                 font=self.fonts['bold'],
                                 bg=self.colors['bg_card'],
                                 fg=self.colors['gray_dark'])
            date_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5), columnspan=4)
            
            # 日期输入框
            date_frame = tk.Frame(self.date_frame, bg=self.colors['bg_card'])
            date_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))
            
            tk.Label(date_frame, text="日期:", 
                    bg=self.colors['bg_card'],
                    fg=self.colors['gray_dark']).pack(side=tk.LEFT, padx=(0, 5))
            
            self.date_entry = tk.Entry(date_frame, 
                                      width=12, 
                                      font=self.fonts['normal'],
                                      bg=self.colors['light'],
                                      fg=self.colors['dark'],
                                      relief=tk.FLAT,
                                      highlightthickness=1,
                                      highlightcolor=self.colors['primary'],
                                      highlightbackground=self.colors['gray'])
            self.date_entry.pack(side=tk.LEFT, padx=(0, 20))
            self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
            
            tk.Label(date_frame, text="时间:", 
                    bg=self.colors['bg_card'],
                    fg=self.colors['gray_dark']).pack(side=tk.LEFT, padx=(0, 5))
            
            self.time_entry = tk.Entry(date_frame, 
                                      width=8, 
                                      font=self.fonts['normal'],
                                      bg=self.colors['light'],
                                      fg=self.colors['dark'],
                                      relief=tk.FLAT,
                                      highlightthickness=1,
                                      highlightcolor=self.colors['primary'],
                                      highlightbackground=self.colors['gray'])
            self.time_entry.pack(side=tk.LEFT)
            self.time_entry.insert(0, "12:00")
            
        elif self.todo_type.get() == "long":
            # 长期事项：开始和结束日期
            # 开始日期
            start_label = tk.Label(self.date_frame,
                                  text="⏰开始时间:",
                                  font=self.fonts['bold'],
                                  bg=self.colors['bg_card'],
                                  fg=self.colors['gray_dark'])
            start_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5), columnspan=4)
            
            # 开始日期输入框
            start_date_frame = tk.Frame(self.date_frame, bg=self.colors['bg_card'])
            start_date_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))
            
            tk.Label(start_date_frame, text="日期:", 
                    bg=self.colors['bg_card'],
                    fg=self.colors['gray_dark']).pack(side=tk.LEFT, padx=(0, 5))
            
            self.start_date_entry = tk.Entry(start_date_frame, 
                                            width=12, 
                                            font=self.fonts['normal'],
                                            bg=self.colors['light'],
                                            fg=self.colors['dark'],
                                            relief=tk.FLAT,
                                            highlightthickness=1,
                                            highlightcolor=self.colors['primary'],
                                            highlightbackground=self.colors['gray'])
            self.start_date_entry.pack(side=tk.LEFT, padx=(0, 20))
            self.start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
            
            tk.Label(start_date_frame, text="时间:", 
                    bg=self.colors['bg_card'],
                    fg=self.colors['gray_dark']).pack(side=tk.LEFT, padx=(0, 5))
            
            self.start_time_entry = tk.Entry(start_date_frame, 
                                            width=8, 
                                            font=self.fonts['normal'],
                                            bg=self.colors['light'],
                                            fg=self.colors['dark'],
                                            relief=tk.FLAT,
                                            highlightthickness=1,
                                            highlightcolor=self.colors['primary'],
                                            highlightbackground=self.colors['gray'])
            self.start_time_entry.pack(side=tk.LEFT)
            self.start_time_entry.insert(0, "00:00")
            
            # 结束日期
            end_label = tk.Label(self.date_frame,
                                text="🏁结束时间:",
                                font=self.fonts['bold'],
                                bg=self.colors['bg_card'],
                                fg=self.colors['gray_dark'])
            end_label.grid(row=2, column=0, sticky=tk.W, pady=(5, 5), columnspan=4)
            
            # 结束日期输入框
            end_date_frame = tk.Frame(self.date_frame, bg=self.colors['bg_card'])
            end_date_frame.grid(row=3, column=0, columnspan=4, sticky=tk.W, pady=(0, 10))
            
            tk.Label(end_date_frame, text="日期:", 
                    bg=self.colors['bg_card'],
                    fg=self.colors['gray_dark']).pack(side=tk.LEFT, padx=(0, 5))
            
            self.end_date_entry = tk.Entry(end_date_frame, 
                                          width=12, 
                                          font=self.fonts['normal'],
                                          bg=self.colors['light'],
                                          fg=self.colors['dark'],
                                          relief=tk.FLAT,
                                          highlightthickness=1,
                                          highlightcolor=self.colors['primary'],
                                          highlightbackground=self.colors['gray'])
            self.end_date_entry.pack(side=tk.LEFT, padx=(0, 20))
            self.end_date_entry.insert(0, (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
            
            tk.Label(end_date_frame, text="时间:", 
                    bg=self.colors['bg_card'],
                    fg=self.colors['gray_dark']).pack(side=tk.LEFT, padx=(0, 5))
            
            self.end_time_entry = tk.Entry(end_date_frame, 
                                          width=8, 
                                          font=self.fonts['normal'],
                                          bg=self.colors['light'],
                                          fg=self.colors['dark'],
                                          relief=tk.FLAT,
                                          highlightthickness=1,
                                          highlightcolor=self.colors['primary'],
                                          highlightbackground=self.colors['gray'])
            self.end_time_entry.pack(side=tk.LEFT)
            self.end_time_entry.insert(0, "23:59")
        
        else:  # timeless
            # 无时限事项：不显示日期输入
            timeless_label = tk.Label(self.date_frame,
                                    text="∞ 无时限任务，无需设置时间",
                                    font=self.fonts['bold'],
                                    bg=self.colors['bg_card'],
                                    fg=self.colors['info'])
            timeless_label.grid(row=0, column=0, sticky=tk.W, pady=(10, 10), columnspan=4)

    def toggle_date_fields(self):
        """切换日期输入字段"""
        self.setup_date_widgets()

    def _on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        if event.delta:
            self.todo_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            self.completed_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
    def on_tab_changed(self, notebook):
        """标签页切换事件处理 - 确保标题数量正确更新"""
        tab_text = notebook.tab(notebook.select(), "text")
        if "待办事项" in tab_text:
            notebook.tab(notebook.select(), text=f"📋待办事项 ({len(self.todo_items)})")
        elif "已完成" in tab_text:
            notebook.tab(notebook.select(), text=f"✅已完成 ({len(self.completed_items)})")

    def parse_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """解析日期时间字符串"""
        try:
            datetime_str = f"{date_str} {time_str}"
            return datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
        except ValueError:
            return None

    def validate_time_format(self, time_str: str) -> bool:
        """验证时间格式"""
        try:
            if ":" in time_str:
                hour, minute = time_str.split(":")
                if 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59:
                    return True
            return False
        except:
            return False

    def add_todo_item(self):
        """添加新的待办事项"""
        note = self.note_text.get("1.0", tk.END).strip()
        if not note:
            messagebox.showwarning("输入错误", "请输入任务描述！")
            return
        
        if self.todo_type.get() == "instant":
            # 即时事项
            date_str = self.date_entry.get().strip()
            time_str = self.time_entry.get().strip()
            
            if not self.validate_time_format(time_str):
                messagebox.showwarning("输入错误", "时间格式不正确！请使用HH:MM格式（如12:30）")
                return
                
            date_time = self.parse_datetime(date_str, time_str)
            
            if not date_time:
                messagebox.showwarning("输入错误", "日期格式不正确！请使用YYYY-MM-DD格式（如2023-12-31）")
                return
            
            todo_item = TodoItem(
                id=self.next_id,
                note=note,
                date_type="instant",
                date1=date_time
            )
            
        elif self.todo_type.get() == "long":
            # 长期事项
            start_date_str = self.start_date_entry.get().strip()
            start_time_str = self.start_time_entry.get().strip()
            end_date_str = self.end_date_entry.get().strip()
            end_time_str = self.end_time_entry.get().strip()
            
            if not self.validate_time_format(start_time_str) or not self.validate_time_format(end_time_str):
                messagebox.showwarning("输入错误", "时间格式不正确！请使用HH:MM格式（如12:30）")
                return
                
            start_time = self.parse_datetime(start_date_str, start_time_str)
            end_time = self.parse_datetime(end_date_str, end_time_str)
            
            if not start_time or not end_time:
                messagebox.showwarning("输入错误", "日期格式不正确！请使用YYYY-MM-DD格式（如2023-12-31）")
                return
            
            if end_time <= start_time:
                messagebox.showwarning("输入错误", "结束时间必须晚于开始时间！")
                return
            
            todo_item = TodoItem(
                id=self.next_id,
                note=note,
                date_type="long",
                date1=start_time,
                date2=end_time
            )
        
        else:  # timeless
            # 无时限事项
            todo_item = TodoItem(
                id=self.next_id,
                note=note,
                date_type="timeless"
            )
        
        self.todo_items.append(todo_item)
        self.next_id += 1
        
        # 清空输入
        self.note_text.delete("1.0", tk.END)
        
        # 刷新显示
        self.refresh_display()
        self.status_label.config(text=f"✅已添加任务: {todo_item.note[:30]}...")
        
        # 自动保存
        self.save_data()

    def create_todo_widget(self, todo_item: TodoItem, parent: tk.Frame, index: int, is_completed: bool = False):
        """创建待办事项的小部件 - 添加悬停效果"""
        # 根据状态确定背景色
        date_str, week_day, status = todo_item.get_time_info()
        
        if is_completed:
            bg_color = self.colors['completed_bg']
            border_color = self.colors['success']
        elif todo_item.date_type == "timeless":
            bg_color = self.colors['timeless_bg']
            border_color = self.colors['info']
        elif "逾期" in status:
            bg_color = self.colors['overdue_bg']
            border_color = self.colors['danger']
        elif "距离结束" in status:
            bg_color = self.colors['ongoing_bg']
            border_color = self.colors['info']
        elif "距离截止" in status or "距离开始" in status:
            bg_color = self.colors['upcoming_bg']
            border_color = self.colors['primary']
        else:
            bg_color = self.colors['todo_bg']
            border_color = self.colors['gray_light']
        
        # 创建卡片容器
        card_frame = tk.Frame(parent, bg=bg_color, highlightbackground=border_color, highlightthickness=2)
        card_frame.pack(fill=tk.X, padx=5, pady=8, ipadx=10, ipady=10)
        
        # 创建右键菜单
        context_menu = tk.Menu(card_frame, tearoff=0, bg=self.colors['light'], fg=self.colors['dark'], 
                              font=self.fonts['small'])
        
        # 获取同组任务
        same_group_items = self.get_same_group_items(todo_item)
        
        # 检查是否显示置顶和上移功能（仅对未完成的任务有效）
        if not is_completed and len(same_group_items) > 1:
            # 检查当前任务是否不是同组中的第一个任务
            if todo_item in same_group_items:
                current_index = same_group_items.index(todo_item)
                
                # 添加置顶功能（如果不在顶部）
                if current_index > 0:
                    context_menu.add_command(label="🚀 置顶", 
                                           command=lambda item=todo_item: self.move_to_top(item))
                
                # 添加上移功能（如果不是第一个）
                if current_index > 0:
                    context_menu.add_separator()
                    context_menu.add_command(label="⬆️ 上移", 
                                           command=lambda item=todo_item: self.move_up_item(item))
        
        context_menu.add_command(label="标记完成/未完成", 
                               command=lambda item=todo_item: self.toggle_completion(item))
        context_menu.add_command(label="编辑任务", 
                               command=lambda item=todo_item: self.edit_item(item))
        context_menu.add_separator()
        context_menu.add_command(label="删除任务", 
                               command=lambda item=todo_item: self.delete_item_with_confirmation(item))
               
        def show_context_menu(event):
            """显示右键菜单"""
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        # 绑定右键点击事件到整个卡片
        card_frame.bind("<Button-3>", show_context_menu)  # Button-3 是右键
        
        # 为卡片内的所有子部件也绑定右键事件
        def bind_context_menu_to_children(widget):
            widget.bind("<Button-3>", show_context_menu)
            for child in widget.winfo_children():
                bind_context_menu_to_children(child)
        
        # 左侧：复选框和主要信息
        left_frame = tk.Frame(card_frame, bg=bg_color)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 复选框
        checkbox_frame = tk.Frame(left_frame, bg=bg_color)
        checkbox_frame.pack(side=tk.LEFT, padx=(0, 15))
        
        # 自定义复选框
        checkbox_canvas = tk.Canvas(checkbox_frame, width=24, height=24, bg=bg_color, highlightthickness=0)
        checkbox_canvas.pack()
        
        # 绘制复选框
        if todo_item.completed:
            checkbox_canvas.create_rectangle(2, 2, 22, 22, 
                                           fill=self.colors['success'], 
                                           outline=self.colors['success'], 
                                           width=2)
            checkbox_canvas.create_text(12, 12, text="✓", fill="white", font=('Arial', 12, 'bold'))
        else:
            checkbox_canvas.create_rectangle(2, 2, 22, 22, 
                                           fill=bg_color, 
                                           outline=self.colors['gray'], 
                                           width=2)
                                        
        # 添加悬停效果 - 包括已完成状态的复选框
        def on_checkbox_enter(event):
            if todo_item.completed:
                # 已完成状态的悬停效果：稍微变亮
                hover_color = self.adjust_color(self.colors['success'], 20)
                checkbox_canvas.itemconfig(checkbox_canvas.find_all()[0], 
                                         fill=hover_color, outline=hover_color)
            else:
                # 未完成状态的悬停效果：边框变主题色
                checkbox_canvas.itemconfig(checkbox_canvas.find_all()[0], 
                                         outline=self.colors['primary'], width=2)
        
        def on_checkbox_leave(event):
            if todo_item.completed:
                # 恢复已完成状态的原色
                checkbox_canvas.itemconfig(checkbox_canvas.find_all()[0], 
                                         fill=self.colors['success'], 
                                         outline=self.colors['success'])
            else:
                # 恢复未完成状态的原色
                checkbox_canvas.itemconfig(checkbox_canvas.find_all()[0], 
                                         outline=self.colors['gray'], width=2)
        
        checkbox_canvas.bind("<Enter>", on_checkbox_enter)
        checkbox_canvas.bind("<Leave>", on_checkbox_leave)
        checkbox_canvas.bind("<Button-1>", lambda e, item=todo_item: self.toggle_completion(item))
        
        # 任务信息
        info_frame = tk.Frame(left_frame, bg=bg_color)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 任务描述
        note_label = tk.Label(info_frame, 
                             text=todo_item.note,
                             bg=bg_color,
                             font=('Microsoft YaHei', 11, 'bold'),
                             anchor=tk.W,
                             wraplength=400,
                             justify=tk.LEFT)
        note_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 时间信息
        time_info_frame = tk.Frame(info_frame, bg=bg_color)
        time_info_frame.pack(anchor=tk.W)
        
        # 日期
        date_label = tk.Label(time_info_frame,
                             text=f"📅{date_str}",
                             bg=bg_color,
                             font=('Microsoft YaHei', 9),
                             fg=self.colors['gray_dark'])
        date_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 星期
        week_label = tk.Label(time_info_frame,
                             text=f"({week_day})",
                             bg=bg_color,
                             font=('Microsoft YaHei', 9),
                             fg=self.colors['gray'])
        week_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # 状态
        status_color = self.colors['danger'] if "逾期" in status and not is_completed else self.colors['info']
        if is_completed:
            status_color = self.colors['success']
        elif todo_item.date_type == "timeless":
            status_color = self.colors['info']
        
        status_label = tk.Label(time_info_frame,
                               text=f"⏰{status}",
                               bg=bg_color,
                               fg=status_color,
                               font=('Microsoft YaHei', 9, 'bold'))
        status_label.pack(side=tk.LEFT)
        
        # 右侧：操作按钮
        button_frame = tk.Frame(card_frame, bg=bg_color)
        button_frame.pack(side=tk.RIGHT, padx=(10, 0))
        
        if is_completed:
            # 已完成事项：删除按钮
            delete_btn = ModernButton(button_frame,
                                     text="🗑删除",
                                     command=lambda item=todo_item: self.delete_item_with_confirmation(item),
                                     bg_color=self.colors['danger'],
                                     width=80,
                                     height=30)
            delete_btn.pack(pady=5)
        else:
            # 未完成事项：编辑按钮
            edit_btn = ModernButton(button_frame,
                                   text="✏编辑",
                                   command=lambda item=todo_item: self.edit_item(item),
                                   bg_color=self.colors['info'],
                                   width=80,
                                   height=30)
            edit_btn.pack(pady=5)
        
        # 为所有子部件绑定右键菜单
        bind_context_menu_to_children(card_frame)
        
        return card_frame
        
    def move_to_top(self, todo_item: TodoItem):
        """将任务移至同组最顶端"""
        # 获取同组任务
        same_group_items = self.get_same_group_items(todo_item)
        
        if len(same_group_items) <= 1:
            return  # 只有一个或没有同组任务，无法置顶
        
        current_index = same_group_items.index(todo_item)
        if current_index == 0:
            return  # 已经在顶部，无需置顶
        
        # 从原列表中移除当前任务
        self.todo_items.remove(todo_item)
        
        # 找到同组第一个任务的位置
        first_group_item = same_group_items[0]
        first_group_index = self.todo_items.index(first_group_item)
        
        # 将任务插入到同组第一个位置
        self.todo_items.insert(first_group_index, todo_item)
        
        # 刷新显示
        self.refresh_display()
        self.save_data()
        
        # 根据任务类型设置状态消息
        if todo_item.date_type == "timeless":
            self.status_label.config(text="🚀 已将无时限任务置顶")
        elif todo_item.date_type == "instant":
            self.status_label.config(text="🚀 已将即时任务置顶")
        else:  # long
            self.status_label.config(text="🚀 已将长期任务置顶")

    def get_same_group_items(self, todo_item: TodoItem) -> List[TodoItem]:
        """获取与给定任务在同一组内的所有未完成任务（保持原始顺序）"""
        if todo_item.completed:
            return []
        
        same_group_items = []
        
        if todo_item.date_type == "timeless":
            # 无时限任务：所有无时限任务为一组
            same_group_items = [item for item in self.todo_items 
                              if item.date_type == "timeless" and not item.completed]
        
        elif todo_item.date_type == "instant":
            # 即时任务：截止时间相同的任务为一组
            same_group_items = [item for item in self.todo_items 
                              if item.date_type == "instant" and not item.completed 
                              and item.date1 == todo_item.date1]
        
        elif todo_item.date_type == "long":
            # 长期任务：起始时间和终止时间都相同的任务为一组
            same_group_items = [item for item in self.todo_items 
                              if item.date_type == "long" and not item.completed 
                              and item.date1 == todo_item.date1 and item.date2 == todo_item.date2]
        
        # 保持原始列表中的顺序
        same_group_items.sort(key=lambda x: self.todo_items.index(x))
        
        return same_group_items

    def get_same_group_items(self, todo_item: TodoItem) -> List[TodoItem]:
        """获取与给定任务在同一组内的所有未完成任务"""
        if todo_item.completed:
            return []
        
        same_group_items = []
        
        if todo_item.date_type == "timeless":
            # 无时限任务：所有无时限任务为一组
            same_group_items = [item for item in self.todo_items 
                              if item.date_type == "timeless" and not item.completed]
        
        elif todo_item.date_type == "instant":
            # 即时任务：截止时间相同的任务为一组
            same_group_items = [item for item in self.todo_items 
                              if item.date_type == "instant" and not item.completed 
                              and item.date1 == todo_item.date1]
        
        elif todo_item.date_type == "long":
            # 长期任务：起始时间和终止时间都相同的任务为一组
            same_group_items = [item for item in self.todo_items 
                              if item.date_type == "long" and not item.completed 
                              and item.date1 == todo_item.date1 and item.date2 == todo_item.date2]
        
        return same_group_items

    def move_up_item(self, todo_item: TodoItem):
        """将任务上移一个位置（在同一组内）"""
        # 获取同组任务
        same_group_items = self.get_same_group_items(todo_item)
        
        if len(same_group_items) <= 1:
            return  # 只有一个或没有同组任务，无法上移
        
        current_index = same_group_items.index(todo_item)
        if current_index == 0:
            return  # 已经是第一个，无法上移
        
        # 获取上一个同组任务
        previous_item = same_group_items[current_index - 1]
        
        # 在原始列表中交换位置
        todo_index = self.todo_items.index(todo_item)
        previous_index = self.todo_items.index(previous_item)
        
        # 交换位置
        self.todo_items[todo_index], self.todo_items[previous_index] = \
            self.todo_items[previous_index], self.todo_items[todo_index]
        
        # 刷新显示
        self.refresh_display()
        self.save_data()
        
        # 根据任务类型设置状态消息
        if todo_item.date_type == "timeless":
            self.status_label.config(text="⬆️已上移无时限任务")
        elif todo_item.date_type == "instant":
            self.status_label.config(text="⬆️已上移即时任务")
        else:  # long
            self.status_label.config(text="⬆️已上移长期任务")

    def delete_item_with_confirmation(self, todo_item: TodoItem):
        """带确认对话框的删除功能"""
        if messagebox.askyesno("确认删除", f"确定要删除任务 '{todo_item.note[:50]}...' 吗？\n\n此操作不可撤销！"):
            if todo_item in self.completed_items:
                self.completed_items.remove(todo_item)
            elif todo_item in self.todo_items:
                self.todo_items.remove(todo_item)
            
            self.refresh_display()
            self.save_data()
            self.status_label.config(text="🗑已删除任务")

    def toggle_completion(self, todo_item: TodoItem):
        """切换事项完成状态"""
        if not todo_item.completed:
            # 标记为完成
            todo_item.completed = True
            todo_item.completed_date = datetime.now()
            self.completed_items.append(todo_item)
            self.todo_items.remove(todo_item)
            self.status_label.config(text=f"✅已完成任务: {todo_item.note[:30]}...")
        else:
            # 标记为未完成
            todo_item.completed = False
            todo_item.completed_date = None
            self.todo_items.append(todo_item)
            self.completed_items.remove(todo_item)
            self.status_label.config(text=f"↩已恢复任务: {todo_item.note[:30]}...")
        
        # 刷新显示
        self.refresh_display()
        self.save_data()

    def delete_item(self, todo_item: TodoItem):
        """删除事项"""
        if messagebox.askyesno("确认删除", f"确定要删除任务 '{todo_item.note[:50]}...' 吗？"):
            if todo_item in self.completed_items:
                self.completed_items.remove(todo_item)
            elif todo_item in self.todo_items:
                self.todo_items.remove(todo_item)
            
            self.refresh_display()
            self.save_data()
            self.status_label.config(text="🗑已删除任务")

    def edit_item(self, todo_item: TodoItem):
        """编辑事项（包括日期）"""
        # 创建编辑对话框
        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.title("编辑任务")
        edit_dialog.geometry("500x500")
        edit_dialog.transient(self.root)
        edit_dialog.grab_set()
        edit_dialog.configure(bg=self.colors['bg_card'])
        
        # 设置对话框为模态
        edit_dialog.focus_set()
        
        # 对话框标题
        title_label = tk.Label(edit_dialog,
                              text="✏编辑任务",
                              font=self.fonts['subtitle'],
                              bg=self.colors['bg_card'],
                              fg=self.colors['primary'])
        title_label.pack(pady=(20, 10))
        
        # 备注
        note_label = tk.Label(edit_dialog, 
                             text="任务描述:",
                             font=self.fonts['bold'],
                             bg=self.colors['bg_card'],
                             fg=self.colors['gray_dark'])
        note_label.pack(anchor=tk.W, padx=40, pady=(0, 5))
        
        note_text = tk.Text(edit_dialog, 
                           height=4, 
                           width=50, 
                           font=self.fonts['normal'],
                           bg=self.colors['light'],
                           fg=self.colors['dark'],
                           relief=tk.FLAT,
                           padx=10,
                           pady=10,
                           highlightthickness=1,
                           highlightcolor=self.colors['primary'],
                           highlightbackground=self.colors['gray'])
        note_text.pack(padx=40, pady=(0, 20))
        note_text.insert("1.0", todo_item.note)
        
        # 事项类型选择
        type_frame = tk.Frame(edit_dialog, bg=self.colors['bg_card'])
        type_frame.pack(anchor=tk.W, padx=40, pady=(0, 10))
        
        ttk.Label(type_frame, text="任务类型:", 
                 style='Subtitle.TLabel').pack(side=tk.LEFT)
        
        todo_type_var = tk.StringVar(value=todo_item.date_type)
        
        ttk.Radiobutton(type_frame, 
                       text="即时任务", 
                       variable=todo_type_var, 
                       value="instant").pack(side=tk.LEFT, padx=(10, 20))
        
        ttk.Radiobutton(type_frame, 
                       text="长期任务", 
                       variable=todo_type_var, 
                       value="long").pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Radiobutton(type_frame, 
                       text="无时限任务", 
                       variable=todo_type_var, 
                       value="timeless").pack(side=tk.LEFT)
        
        # 日期时间输入框架
        date_frame = tk.Frame(edit_dialog, bg=self.colors['bg_card'])
        date_frame.pack(fill=tk.X, padx=40, pady=10)
        
        def update_date_fields():
            """更新日期字段显示 - 修复了类型转换时的逻辑"""
            for widget in date_frame.winfo_children():
                widget.destroy()
            
            if todo_type_var.get() == "instant":
                # 即时事项
                ttk.Label(date_frame, text="截止日期:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5), columnspan=4)
                
                date_entry = ttk.Entry(date_frame, width=15)
                date_entry.grid(row=1, column=0, padx=(0, 20), pady=5, sticky=tk.W)
                
                # 智能填充逻辑：根据原任务类型决定默认值
                if todo_item.date_type == "instant":
                    # 原为即时任务：使用原截止时间
                    date_entry.insert(0, todo_item.date1.strftime('%Y-%m-%d'))
                elif todo_item.date_type == "long":
                    # 原为长期任务：使用结束时间作为截止时间
                    date_entry.insert(0, todo_item.date2.strftime('%Y-%m-%d'))
                else:
                    # 原为无时限任务：使用当前时间
                    date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
                
                ttk.Label(date_frame, text="时间:").grid(row=1, column=1, sticky=tk.W, pady=5)
                time_entry = ttk.Entry(date_frame, width=8)
                time_entry.grid(row=1, column=2, padx=(5, 0), pady=5, sticky=tk.W)
                
                # 智能填充时间逻辑
                if todo_item.date_type == "instant":
                    time_entry.insert(0, todo_item.date1.strftime('%H:%M'))
                elif todo_item.date_type == "long":
                    time_entry.insert(0, todo_item.date2.strftime('%H:%M'))
                else:
                    time_entry.insert(0, "12:00")
                
                date_frame.date_widgets = {
                    'date_entry': date_entry,
                    'time_entry': time_entry
                }
                
            elif todo_type_var.get() == "long":
                # 长期事项
                ttk.Label(date_frame, text="开始日期:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5), columnspan=4)
                
                start_date_entry = ttk.Entry(date_frame, width=15)
                start_date_entry.grid(row=1, column=0, padx=(0, 20), pady=5, sticky=tk.W)
                
                # 智能填充开始时间逻辑
                if todo_item.date_type == "instant":
                    # 原为即时任务：使用当前时间作为开始时间
                    start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
                elif todo_item.date_type == "long":
                    # 原为长期任务：使用原开始时间
                    start_date_entry.insert(0, todo_item.date1.strftime('%Y-%m-%d'))
                else:
                    # 原为无时限任务：使用当前时间
                    start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
                
                ttk.Label(date_frame, text="时间:").grid(row=1, column=1, sticky=tk.W, pady=5)
                start_time_entry = ttk.Entry(date_frame, width=8)
                start_time_entry.grid(row=1, column=2, padx=(5, 0), pady=5, sticky=tk.W)
                
                if todo_item.date_type == "instant":
                    start_time_entry.insert(0, datetime.now().strftime('%H:%M'))
                elif todo_item.date_type == "long":
                    start_time_entry.insert(0, todo_item.date1.strftime('%H:%M'))
                else:
                    start_time_entry.insert(0, "00:00")
                
                ttk.Label(date_frame, text="结束日期:").grid(row=2, column=0, sticky=tk.W, pady=(5, 5), columnspan=4)
                
                end_date_entry = ttk.Entry(date_frame, width=15)
                end_date_entry.grid(row=3, column=0, padx=(0, 20), pady=5, sticky=tk.W)
                
                # 关键修复：即时任务转换为长期任务时，截止时间应该成为结束时间
                if todo_item.date_type == "instant":
                    # 原为即时任务：使用原截止时间作为结束时间
                    end_date_entry.insert(0, todo_item.date1.strftime('%Y-%m-%d'))
                elif todo_item.date_type == "long":
                    # 原为长期任务：使用原结束时间
                    end_date_entry.insert(0, todo_item.date2.strftime('%Y-%m-%d'))
                else:
                    # 原为无时限任务：使用明天作为结束时间
                    end_date_entry.insert(0, (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'))
                
                ttk.Label(date_frame, text="时间:").grid(row=3, column=1, sticky=tk.W, pady=5)
                end_time_entry = ttk.Entry(date_frame, width=8)
                end_time_entry.grid(row=3, column=2, padx=(5, 0), pady=5, sticky=tk.W)
                
                if todo_item.date_type == "instant":
                    end_time_entry.insert(0, todo_item.date1.strftime('%H:%M'))
                elif todo_item.date_type == "long":
                    end_time_entry.insert(0, todo_item.date2.strftime('%H:%M'))
                else:
                    end_time_entry.insert(0, "23:59")
                
                date_frame.date_widgets = {
                    'start_date_entry': start_date_entry,
                    'start_time_entry': start_time_entry,
                    'end_date_entry': end_date_entry,
                    'end_time_entry': end_time_entry
                }
            else:  # timeless
                # 无时限事项：不显示日期输入
                timeless_label = ttk.Label(date_frame, 
                                          text="∞ 无时限任务，无需设置时间",
                                          style='Subtitle.TLabel')
                timeless_label.grid(row=0, column=0, sticky=tk.W, pady=(10, 10), columnspan=4)
                # 确保date_widgets字典存在但为空
                date_frame.date_widgets = {}
        
        # 初始化日期字段
        update_date_fields()
        
        # 绑定类型变化事件
        todo_type_var.trace('w', lambda *args: update_date_fields())
        
        def save_changes():
            """保存修改"""
            new_note = note_text.get("1.0", tk.END).strip()
            if not new_note:
                messagebox.showwarning("输入错误", "请输入任务描述！")
                return
            
            current_type = todo_type_var.get()
            
            if current_type == "instant":
                # 检查是否存在对应的组件
                if 'date_entry' not in date_frame.date_widgets or 'time_entry' not in date_frame.date_widgets:
                    messagebox.showwarning("输入错误", "日期时间输入框未正确初始化！")
                    return
                    
                # 即时事项
                date_str = date_frame.date_widgets['date_entry'].get().strip()
                time_str = date_frame.date_widgets['time_entry'].get().strip()
                
                if not self.validate_time_format(time_str):
                    messagebox.showwarning("输入错误", "时间格式不正确！请使用HH:MM格式（如12:30）")
                    return
                    
                date_time = self.parse_datetime(date_str, time_str)
                
                if not date_time:
                    messagebox.showwarning("输入错误", "日期格式不正确！请使用YYYY-MM-DD格式（如2023-12-31）")
                    return
                
                # 更新事项
                todo_item.note = new_note
                todo_item.date_type = "instant"
                todo_item.date1 = date_time
                todo_item.date2 = None
                
            elif current_type == "long":
                # 检查是否存在对应的组件
                required_keys = ['start_date_entry', 'start_time_entry', 'end_date_entry', 'end_time_entry']
                if not all(key in date_frame.date_widgets for key in required_keys):
                    messagebox.showwarning("输入错误", "日期时间输入框未正确初始化！")
                    return
                    
                # 长期事项
                start_date_str = date_frame.date_widgets['start_date_entry'].get().strip()
                start_time_str = date_frame.date_widgets['start_time_entry'].get().strip()
                end_date_str = date_frame.date_widgets['end_date_entry'].get().strip()
                end_time_str = date_frame.date_widgets['end_time_entry'].get().strip()
                
                if not self.validate_time_format(start_time_str) or not self.validate_time_format(end_time_str):
                    messagebox.showwarning("输入错误", "时间格式不正确！请使用HH:MM格式（如12:30）")
                    return
                    
                start_time = self.parse_datetime(start_date_str, start_time_str)
                end_time = self.parse_datetime(end_date_str, end_time_str)
                
                if not start_time or not end_time:
                    messagebox.showwarning("输入错误", "日期格式不正确！请使用YYYY-MM-DD格式（如2023-12-31）")
                    return
                
                if end_time <= start_time:
                    messagebox.showwarning("输入错误", "结束时间必须晚于开始时间！")
                    return
                
                # 更新事项
                todo_item.note = new_note
                todo_item.date_type = "long"
                todo_item.date1 = start_time
                todo_item.date2 = end_time
            
            else:  # timeless
                # 无时限事项
                todo_item.note = new_note
                todo_item.date_type = "timeless"
                todo_item.date1 = None
                todo_item.date2 = None
            
            # 刷新显示并保存
            self.refresh_display()
            self.save_data()
            edit_dialog.destroy()
            self.status_label.config(text="✅ 已更新任务")
        
        # 按钮框架
        button_frame = tk.Frame(edit_dialog, bg=self.colors['bg_card'])
        button_frame.pack(pady=20)
        
        save_button = ModernButton(button_frame,
                                  text="💾保存",
                                  command=save_changes,
                                  bg_color=self.colors['success'],
                                  width=120,
                                  height=40)
        save_button.pack(side=tk.LEFT, padx=10)
        
        cancel_button = ModernButton(button_frame,
                                    text="❌取消",
                                    command=edit_dialog.destroy,
                                    bg_color=self.colors['danger'],
                                    width=120,
                                    height=40)
        cancel_button.pack(side=tk.LEFT, padx=10)

    def refresh_display(self):
        """刷新显示所有事项 - 改进排序逻辑"""
        # 更新统计信息
        todo_count = len(self.todo_items)
        completed_count = len(self.completed_items)
        overdue_count = sum(1 for item in self.todo_items if "逾期" in item.get_time_info()[2])
        timeless_count = sum(1 for item in self.todo_items if item.date_type == "timeless")
        
        self.todo_count_label.config(text=f"📋待办: {todo_count}")
        self.completed_count_label.config(text=f"✅已完成: {completed_count}")
        
        # 清空容器
        for widget in self.todo_container.winfo_children():
            widget.destroy()
        
        for widget in self.completed_container.winfo_children():
            widget.destroy()
        
        # 改进的排序逻辑：逾期最前，进行中其次，未开始最后
        def get_priority(item: TodoItem) -> Tuple[int, datetime]:
            """计算任务优先级"""
            now = datetime.now()
            _, _, status = item.get_time_info()
            
            if item.completed:
                return (3, item.completed_date if item.completed_date else datetime.max)
            
            if item.date_type == "timeless":
                return (2, datetime.max)  # 无时限任务放在最后
            
            # 有时限任务的优先级计算
            if "逾期" in status:
                # 逾期任务：优先级0（最高）
                if item.date_type == "instant":
                    return (0, item.date1)  # 按逾期时间排序
                else:  # long
                    return (0, item.date2)
            elif "距离结束" in status:
                # 进行中任务：优先级1
                return (1, item.date2)  # 按结束时间排序
            else:
                # 未开始任务：优先级2
                if item.date_type == "instant":
                    return (2, item.date1)  # 按开始时间排序
                else:  # long
                    return (2, item.date1)
        
        # 按优先级排序
        self.todo_items.sort(key=get_priority)
        
        # 显示待办事项
        if not self.todo_items:
            empty_frame = tk.Frame(self.todo_container, bg=self.colors['bg_main'])
            empty_frame.pack(fill=tk.BOTH, expand=True, pady=50)
            
            empty_label = tk.Label(empty_frame,
                                  text="🎉暂无待办任务！\n\n点击左侧添加新任务",
                                  font=self.fonts['subtitle'],
                                  bg=self.colors['bg_main'],
                                  fg=self.colors['gray'],
                                  justify=tk.CENTER)
            empty_label.pack()
        else:
            for i, item in enumerate(self.todo_items):
                self.create_todo_widget(item, self.todo_container, i, False)
        
        # 显示已完成事项（按完成时间倒序排列）
        if not self.completed_items:
            empty_frame = tk.Frame(self.completed_container, bg=self.colors['bg_main'])
            empty_frame.pack(fill=tk.BOTH, expand=True, pady=50)
            
            empty_label = tk.Label(empty_frame,
                                  text="📝暂无已完成任务",
                                  font=self.fonts['subtitle'],
                                  bg=self.colors['bg_main'],
                                  fg=self.colors['gray'],
                                  justify=tk.CENTER)
            empty_label.pack()
        else:
            # 按完成时间倒序排列
            completed_sorted = sorted(
                self.completed_items, 
                key=lambda x: x.completed_date if x.completed_date else datetime.min, 
                reverse=True
            )
            for i, item in enumerate(completed_sorted):
                self.create_todo_widget(item, self.completed_container, i, True)
        
        # 更新Canvas的滚动区域
        self.todo_canvas.configure(scrollregion=self.todo_canvas.bbox("all"))
        self.completed_canvas.configure(scrollregion=self.completed_canvas.bbox("all"))
        
        # 更新标签页标题
        for child in self.root.winfo_children():
            if isinstance(child, ttk.Notebook):
                child.tab(0, text=f"📋待办事项 ({todo_count})")
                child.tab(1, text=f"✅已完成 ({completed_count})")
        
    def clear_completed(self):
        """清空已完成事项 - 增强版本，包含导出选项"""
        if not self.completed_items:
            messagebox.showinfo("清空已完成", "暂无已完成任务可清空！")
            return
        
        # 创建自定义对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("清空已完成任务")
        dialog.configure(bg=self.colors['bg_main'])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # 对话框内容
        title_label = tk.Label(dialog,
                              text="🗑 清空已完成任务",
                              font=self.fonts['subtitle'],
                              bg=self.colors['bg_main'],
                              fg=self.colors['primary_dark'])
        
        info_label = tk.Label(dialog,
                             text=f"当前有 {len(self.completed_items)} 个已完成任务",
                             font=self.fonts['normal'],
                             bg=self.colors['bg_main'],
                             fg=self.colors['gray_dark'])
        
        warning_label = tk.Label(dialog,
                                text="此操作不可撤销，请谨慎选择！",
                                font=self.fonts['small'],
                                bg=self.colors['bg_main'],
                                fg=self.colors['danger'])
        
        # 按钮框架
        button_frame = tk.Frame(dialog, bg=self.colors['bg_main'])
        
        def clear_and_export():
            """清空并导出已完成任务"""
            dialog.destroy()
            self.export_completed_tasks()  # 先导出
            self.completed_items.clear()   # 再清空
            self.refresh_display()
            self.save_data()
            self.status_label.config(text="✅ 已清空并导出已完成任务")
        
        def clear_without_export():
            """清空不导出"""
            dialog.destroy()
            self.completed_items.clear()
            self.refresh_display()
            self.save_data()
            self.status_label.config(text="🗑 已清空所有已完成任务")
        
        def cancel_clear():
            """取消清空"""
            dialog.destroy()
            self.status_label.config(text="❌ 取消清空操作")
        
        # 创建三个按钮
        export_button = ModernButton(button_frame,
                                    text="📤 清空并导出",
                                    command=clear_and_export,
                                    bg_color=self.colors['success'],
                                    width=120,
                                    height=35)
        
        clear_button = ModernButton(button_frame,
                                   text="🗑 清空不导出",
                                   command=clear_without_export,
                                   bg_color=self.colors['warning'],
                                   width=120,
                                   height=35)
        
        cancel_button = ModernButton(button_frame,
                                    text="❌ 取消",
                                    command=cancel_clear,
                                    bg_color=self.colors['danger'],
                                    width=80,
                                    height=35)
        
        # 布局控件
        title_label.pack(pady=20)
        info_label.pack(pady=(0, 10))
        warning_label.pack(pady=(0, 20))
        
        export_button.pack(side=tk.LEFT, padx=5)
        clear_button.pack(side=tk.LEFT, padx=5)
        cancel_button.pack(side=tk.LEFT, padx=5)
        button_frame.pack(pady=10)
        
        # 让对话框更新布局以获取正确的尺寸
        dialog.update_idletasks()
        
        # 计算对话框大小
        dialog_width = dialog.winfo_reqwidth()
        dialog_height = dialog.winfo_reqheight()
        
        # 计算屏幕中心位置
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2
        
        # 设置对话框位置，确保居中
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
    def export_completed_tasks(self):
        """导出已完成任务到文件，格式与未完成任务导出相同"""
        if not self.completed_items:
            messagebox.showinfo("导出", "没有已完成任务可导出！")
            return
        
        # 创建文件对话框
        from tkinter import filedialog
        import os
        
        # 获取默认文件名（当前日期）
        default_filename = f"已完成任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # 打开文件保存对话框
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile=default_filename,
            title="导出已完成任务"
        )
        
        if not file_path:  # 用户取消了保存
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入文件头
                f.write("=" * 60 + "\n")
                f.write(f"已完成任务导出报告\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
                f.write(f"任务总数: {len(self.completed_items)} 个\n")
                f.write("=" * 60 + "\n\n")
                
                # 按完成时间倒序排列
                completed_sorted = sorted(
                    self.completed_items, 
                    key=lambda x: x.completed_date if x.completed_date else datetime.min, 
                    reverse=True
                )
                
                # 按完成状态分组
                on_time_tasks = []
                early_tasks = []
                late_tasks = []
                timeless_tasks = []
                
                for item in completed_sorted:
                    if item.date_type == "timeless":
                        timeless_tasks.append(item)
                    else:
                        # 判断完成时间是否在前后6小时内
                        if item.date_type == "instant":
                            due_date = item.date1
                        else:  # long
                            due_date = item.date2
                            
                        time_diff = item.completed_date - due_date
                        total_seconds = time_diff.total_seconds()
                        
                        if abs(total_seconds) <= 6 * 3600:  # 6小时内视为准时
                            on_time_tasks.append(item)
                        elif total_seconds < 0:  # 提前完成
                            early_tasks.append(item)
                        else:  # 延后完成
                            late_tasks.append(item)
                
                # 导出准时完成的任务
                if on_time_tasks:
                    f.write("⏰ 准时完成的任务\n")
                    f.write("-" * 40 + "\n")
                    for i, item in enumerate(on_time_tasks, 1):
                        self._write_completed_task_to_file(f, item, i)
                    f.write("\n")
                
                # 导出提前完成的任务
                if early_tasks:
                    f.write("⬆️ 提前完成的任务\n")
                    f.write("-" * 40 + "\n")
                    for i, item in enumerate(early_tasks, 1):
                        self._write_completed_task_to_file(f, item, i)
                    f.write("\n")
                
                # 导出延后完成的任务
                if late_tasks:
                    f.write("⬇️ 延后完成的任务\n")
                    f.write("-" * 40 + "\n")
                    for i, item in enumerate(late_tasks, 1):
                        self._write_completed_task_to_file(f, item, i)
                    f.write("\n")
                
                # 导出无时限任务
                if timeless_tasks:
                    f.write("∞ 无时限任务\n")
                    f.write("-" * 40 + "\n")
                    for i, item in enumerate(timeless_tasks, 1):
                        self._write_completed_task_to_file(f, item, i)
                    f.write("\n")
                
                # 写入统计信息
                f.write("=" * 60 + "\n")
                f.write("📊 完成情况统计\n")
                f.write("=" * 60 + "\n")
                f.write(f"• 准时完成: {len(on_time_tasks)} 个\n")
                f.write(f"• 提前完成: {len(early_tasks)} 个\n")
                f.write(f"• 延后完成: {len(late_tasks)} 个\n")
                f.write(f"• 无时限任务: {len(timeless_tasks)} 个\n")
                f.write(f"• 总计完成: {len(self.completed_items)} 个\n")
                
                # 完成率统计（如果有未完成任务）
                total_tasks = len(self.todo_items) + len(self.completed_items)
                if total_tasks > 0:
                    completion_rate = (len(self.completed_items) / total_tasks) * 100
                    f.write(f"• 任务完成率: {completion_rate:.1f}%\n")
            
            # 显示成功消息
            messagebox.showinfo("导出成功", 
                              f"成功导出 {len(self.completed_items)} 个已完成任务到：\n{os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("导出错误", f"导出文件时发生错误：\n{str(e)}")

    def _write_completed_task_to_file(self, file_obj, todo_item, index):
        """将单个已完成任务信息写入文件"""
        date_str, week_day, status = todo_item.get_time_info()
        
        # 任务基本信息
        file_obj.write(f"{index}. {todo_item.note}\n")
        
        # 时间信息
        if todo_item.date_type == "instant":
            file_obj.write(f"   📅 原定截止: {todo_item.date1.strftime('%Y-%m-%d %H:%M')}\n")
        elif todo_item.date_type == "long":
            file_obj.write(f"   📅 原定时间: {todo_item.date1.strftime('%Y-%m-%d')} 至 {todo_item.date2.strftime('%Y-%m-%d')}\n")
        else:  # timeless
            file_obj.write(f"   📅 无时限任务\n")
        
        # 完成时间
        if todo_item.completed_date:
            completed_time = todo_item.completed_date.strftime('%Y-%m-%d %H:%M')
            file_obj.write(f"   ✅ 完成时间: {completed_time}\n")
        
        # 完成状态
        status_icon = "⏰" if "准时" in status else "⬆️" if "超前" in status else "⬇️" if "延后" in status else "✅"
        file_obj.write(f"   {status_icon} 完成状态: {status}\n")
        
        # 创建时间
        created_time = todo_item.created_date.strftime('%Y-%m-%d %H:%M')
        file_obj.write(f"   🕒 创建时间: {created_time}\n")
        
        file_obj.write("\n")  # 空行分隔
            
    def load_data(self):
        """从文件加载数据 - 使用用户特定文件"""
        data_file = self.user_manager.get_user_data_file()
        
        if not os.path.exists(data_file):
            return
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.todo_items = [TodoItem.from_dict(item) for item in data.get('todo_items', [])]
            self.completed_items = [TodoItem.from_dict(item) for item in data.get('completed_items', [])]
            self.next_id = data.get('next_id', 1)
            
            # 确保ID不会重复
            all_items = self.todo_items + self.completed_items
            if all_items:
                max_id = max(item.id for item in all_items)
                self.next_id = max(max_id + 1, self.next_id)
                
        except Exception as e:
            print(f"加载数据时出错: {e}")
            messagebox.showwarning("数据错误", "无法加载保存的数据，将使用空白数据")

    def save_data(self):
        """保存数据到文件 - 使用用户特定文件"""
        data_file = self.user_manager.get_user_data_file()
        data = {
            'todo_items': [item.to_dict() for item in self.todo_items],
            'completed_items': [item.to_dict() for item in self.completed_items],
            'next_id': self.next_id
        }
        
        try:
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.status_label.config(text="💾数据已保存")
        except Exception as e:
            self.status_label.config(text=f"❌保存失败: {str(e)}")

    def auto_refresh(self):
        """自动刷新显示"""
        self.refresh_display()
        self.root.after(60000, self.auto_refresh)  # 每分钟刷新一次
        
    def export_pending_tasks(self):
        """导出未完成任务到文本文件"""
        if not self.todo_items:
            messagebox.showinfo("导出", "没有未完成任务可导出！")
            return
        
        # 创建文件对话框
        from tkinter import filedialog
        import os
        
        # 获取默认文件名（当前日期）
        default_filename = f"未完成任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # 打开文件保存对话框
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile=default_filename,
            title="导出未完成任务"
        )
        
        if not file_path:  # 用户取消了保存
            return
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # 写入文件头
                f.write("=" * 60 + "\n")
                f.write(f"未完成任务导出报告\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
                f.write(f"任务总数: {len(self.todo_items)} 个\n")
                f.write("=" * 60 + "\n\n")
                
                # 按优先级分组导出
                overdue_tasks = []
                ongoing_tasks = []
                upcoming_tasks = []
                timeless_tasks = []
                
                for item in self.todo_items:
                    _, _, status = item.get_time_info()
                    
                    if "逾期" in status:
                        overdue_tasks.append(item)
                    elif "距离结束" in status:
                        ongoing_tasks.append(item)
                    elif item.date_type == "timeless":
                        timeless_tasks.append(item)
                    else:
                        upcoming_tasks.append(item)
                
                # 导出逾期任务
                if overdue_tasks:
                    f.write("🚨 逾期任务（需立即处理）\n")
                    f.write("-" * 40 + "\n")
                    for i, item in enumerate(overdue_tasks, 1):
                        self._write_task_to_file(f, item, i)
                    f.write("\n")
                
                # 导出进行中任务
                if ongoing_tasks:
                    f.write("⏳ 进行中任务\n")
                    f.write("-" * 40 + "\n")
                    for i, item in enumerate(ongoing_tasks, 1):
                        self._write_task_to_file(f, item, i)
                    f.write("\n")
                
                # 导出即将开始任务
                if upcoming_tasks:
                    f.write("📅 即将开始任务\n")
                    f.write("-" * 40 + "\n")
                    for i, item in enumerate(upcoming_tasks, 1):
                        self._write_task_to_file(f, item, i)
                    f.write("\n")
                
                # 导出无时限任务
                if timeless_tasks:
                    f.write("∞ 无时限任务\n")
                    f.write("-" * 40 + "\n")
                    for i, item in enumerate(timeless_tasks, 1):
                        self._write_task_to_file(f, item, i)
                    f.write("\n")
                
                # 写入统计信息
                f.write("=" * 60 + "\n")
                f.write("📊 任务统计摘要\n")
                f.write("=" * 60 + "\n")
                f.write(f"• 逾期任务: {len(overdue_tasks)} 个\n")
                f.write(f"• 进行中任务: {len(ongoing_tasks)} 个\n")
                f.write(f"• 即将开始任务: {len(upcoming_tasks)} 个\n")
                f.write(f"• 无时限任务: {len(timeless_tasks)} 个\n")
                f.write(f"• 总计未完成: {len(self.todo_items)} 个\n")
                
            # 显示成功消息
            self.status_label.config(text=f"✅ 已导出 {len(self.todo_items)} 个任务到: {os.path.basename(file_path)}")
            messagebox.showinfo("导出成功", 
                               f"成功导出 {len(self.todo_items)} 个未完成任务到：\n{file_path}")
            
        except Exception as e:
            self.status_label.config(text=f"❌ 导出失败: {str(e)}")
            messagebox.showerror("导出错误", f"导出文件时发生错误：\n{str(e)}")

    def _write_task_to_file(self, file_obj, todo_item, index):
        """将单个任务信息写入文件"""
        date_str, week_day, status = todo_item.get_time_info()
        
        # 任务基本信息
        file_obj.write(f"{index}. {todo_item.note}\n")
        
        # 时间信息
        if todo_item.date_type == "instant":
            file_obj.write(f"   📅 截止时间: {date_str} ({week_day})\n")
        elif todo_item.date_type == "long":
            file_obj.write(f"   📅 时间范围: {date_str}\n")
        else:  # timeless
            file_obj.write(f"   📅 无时限任务\n")
        
        # 状态信息
        status_icon = "🚨" if "逾期" in status else "⏳" if "距离结束" in status else "📅"
        file_obj.write(f"   {status_icon} 状态: {status}\n")
        
        # 创建时间
        created_time = todo_item.created_date.strftime('%Y-%m-%d %H:%M')
        file_obj.write(f"   🕒 创建时间: {created_time}\n")
        
        file_obj.write("\n")  # 空行分隔

    def export_pending_tasks_simple(self):
        """简化版导出功能 - 直接导出到桌面"""
        if not self.todo_items:
            messagebox.showinfo("导出", "没有未完成任务可导出！")
            return
        
        try:
            # 获取桌面路径
            import os
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            filename = f"未完成任务_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            file_path = os.path.join(desktop, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"未完成任务列表 - 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write("=" * 50 + "\n\n")
                
                for i, item in enumerate(self.todo_items, 1):
                    date_str, week_day, status = item.get_time_info()
                    f.write(f"{i}. {item.note}\n")
                    f.write(f"   时间: {date_str} | 状态: {status}\n\n")
            
            self.status_label.config(text=f"✅ 已导出到桌面: {filename}")
            messagebox.showinfo("导出成功", f"已成功导出到桌面文件：\n{filename}")
            
        except Exception as e:
            messagebox.showerror("导出错误", f"导出失败：{str(e)}")
            
    # 在TodoApp类中添加以下方法
    def setup_window_management(self):
        """设置窗口状态管理"""
        # 记录窗口状态
        self.window_state = 'normal'
        self.last_redraw_time = 0
        
        # 绑定窗口事件
        self.root.bind('<Unmap>', self.on_window_minimize)  # 窗口最小化时
        self.root.bind('<Map>', self.on_window_restore)      # 窗口恢复时
        
    def on_window_minimize(self, event=None):
        """窗口最小化时的处理"""
        self.window_state = 'minimized'
        
    def on_window_restore(self, event=None):
        """窗口从最小化恢复时的处理"""
        if self.window_state == 'minimized':
            self.window_state = 'normal'
            current_time = time.time()
            
            # 避免频繁重绘（至少间隔100ms）
            if current_time - self.last_redraw_time > 0.1:
                self.last_redraw_time = current_time
                # 使用渐变效果恢复窗口
                self.fade_in_window()

    def force_redraw(self):
        """强制重绘整个界面"""
        try:
            # 强制更新所有待处理的任务
            self.root.update_idletasks()
            
            # 触发完整的重绘流程
            self.root.update()
            
            # 刷新显示
            self.refresh_display()
            
            # 强制重绘所有子组件
            for widget in self.root.winfo_children():
                widget.update_idletasks()
                
        except Exception as e:
            # 忽略重绘过程中的小错误
            pass
            
    def get_pending_task_stats(self) -> Dict[str, int]:
        """获取未完成任务统计"""
        stats = {
            'not_started': 0,  # 未开始任务
            'ongoing': 0,      # 进行中任务
            'overdue': 0,      # 逾期任务
            'timeless': 0      # 无时限任务
        }
        
        for item in self.todo_items:
            if item.completed:
                continue
                
            if item.date_type == "timeless":
                stats['timeless'] += 1
            else:
                now = datetime.now()
                if item.date_type == "instant":
                    # 即时任务默认视为进行中
                    if now > item.date1:
                        stats['overdue'] += 1
                    else:
                        stats['ongoing'] += 1
                elif item.date_type == "long":
                    if now < item.date1:
                        stats['not_started'] += 1
                    elif item.date1 <= now <= item.date2:
                        stats['ongoing'] += 1
                    else:  # now > item.date2
                        stats['overdue'] += 1
        
        return stats

    def get_completed_task_stats(self) -> Dict[str, int]:
        """获取已完成任务统计"""
        stats = {
            'on_time': 0,      # 准时完成
            'early': 0,        # 提前完成
            'late': 0,         # 延后完成
            'timeless': 0      # 无时限任务完成
        }
        
        for item in self.completed_items:
            if not item.completed or not item.completed_date:
                continue
                
            if item.date_type == "timeless":
                stats['timeless'] += 1
            else:
                # 判断完成时间是否在前后6小时内
                if item.date_type == "instant":
                    due_date = item.date1
                else:  # long
                    due_date = item.date2
                    
                time_diff = item.completed_date - due_date
                total_seconds = time_diff.total_seconds()
                
                if abs(total_seconds) <= 6 * 3600:  # 6小时内视为准时
                    stats['on_time'] += 1
                elif total_seconds < 0:  # 提前完成
                    stats['early'] += 1
                else:  # 延后完成
                    stats['late'] += 1
        
        return stats
        
    def show_task_statistics(self):
        """显示任务统计信息窗口"""
        # 获取统计数据
        pending_stats = self.get_pending_task_stats()
        completed_stats = self.get_completed_task_stats()
        
        # 先计算居中位置
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 600
        window_height = 530
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 创建统计窗口时直接设置居中位置
        stats_window = tk.Toplevel(self.root)
        stats_window.title(" 任务统计")
        stats_window.geometry(f"{window_width}x{window_height}+{x}+{y}")  # 一次性设置大小和位置
        stats_window.configure(bg=self.colors['bg_main'])
        stats_window.transient(self.root)
        stats_window.grab_set()
        
        # 确保窗口在创建时就正确显示
        stats_window.update_idletasks()
        
        # 主标题
        title_label = tk.Label(stats_window,
                              text="📊 任务统计分析",
                              font=self.fonts['title'],
                              bg=self.colors['bg_main'],
                              fg=self.colors['primary_dark'])
        title_label.pack(pady=20)
        
        # 创建选项卡 - 应用与主界面相同的样式
        notebook = ttk.Notebook(stats_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # 设置统计窗口选项卡的样式
        self.setup_notebook_style(notebook)
        
        # 未完成任务统计标签页
        uncompleted_frame = tk.Frame(notebook, bg=self.colors['bg_main'])
        notebook.add(uncompleted_frame, text="📋 未完成任务")
        
        # 已完成任务统计标签页
        completed_frame = tk.Frame(notebook, bg=self.colors['bg_main'])
        notebook.add(completed_frame, text="✅ 已完成任务")
        
        # 填充未完成任务统计
        self._fill_pending_stats(uncompleted_frame, pending_stats)
        
        # 填充已完成任务统计
        self._fill_completed_stats(completed_frame, completed_stats)
        
        # 关闭按钮
        close_button = ModernButton(stats_window,
                                   text="关闭",
                                   command=stats_window.destroy,
                                   bg_color=self.colors['primary'],
                                   width=120,
                                   height=40)
        close_button.pack(pady=20)

    def _fill_pending_stats(self, parent, stats):
        """填充未完成任务统计信息"""
        # 总览卡片
        overview_frame = tk.Frame(parent, bg=self.colors['bg_card'], relief=tk.RAISED, bd=1)
        overview_frame.pack(fill=tk.X, padx=10, pady=10, ipadx=10, ipady=10)
        
        total_pending = sum(stats.values())
        tk.Label(overview_frame, 
                 text=f"📊 未完成任务总览: {total_pending} 个",
                 font=self.fonts['subtitle'],
                 bg=self.colors['bg_card']).pack(anchor=tk.W)
        
        # 详细分类
        details_frame = tk.Frame(parent, bg=self.colors['bg_main'])
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 使用网格布局显示统计信息
        categories = [
            ("⏳ 未开始任务", stats['not_started'], self.colors['info']),
            ("🔄 进行中任务", stats['ongoing'], self.colors['primary']),
            ("⚠️ 逾期任务", stats['overdue'], self.colors['danger']),
            ("∞ 无时限任务", stats['timeless'], self.colors['secondary'])
        ]
        
        for i, (label, count, color) in enumerate(categories):
            row = i // 2
            col = i % 2
            
            # 创建统计卡片
            card = tk.Frame(details_frame, bg=color, relief=tk.RAISED, bd=1)
            card.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
            
            # 配置网格权重
            details_frame.grid_rowconfigure(row, weight=1)
            details_frame.grid_columnconfigure(col, weight=1)
            
            # 数量显示
            count_label = tk.Label(card, 
                                  text=str(count),
                                  font=('Microsoft YaHei', 24, 'bold'),
                                  bg=color,
                                  fg='white')
            count_label.pack(pady=(10, 5))
            
            # 类别标签
            type_label = tk.Label(card,
                                 text=label,
                                 font=self.fonts['normal'],
                                 bg=color,
                                 fg='white')
            type_label.pack(pady=(0, 10))

    def _fill_completed_stats(self, parent, stats):
        """填充已完成任务统计信息"""
        # 总览卡片
        overview_frame = tk.Frame(parent, bg=self.colors['bg_card'], relief=tk.RAISED, bd=1)
        overview_frame.pack(fill=tk.X, padx=10, pady=10, ipadx=10, ipady=10)
        
        total_completed = sum(stats.values())
        tk.Label(overview_frame, 
                 text=f"📊 已完成任务总览: {total_completed} 个",
                 font=self.fonts['subtitle'],
                 bg=self.colors['bg_card']).pack(anchor=tk.W)
        
        # 详细分类
        details_frame = tk.Frame(parent, bg=self.colors['bg_main'])
        details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 使用网格布局显示统计信息
        categories = [
            ("⏰ 准时完成", stats['on_time'], self.colors['success']),
            ("⬆️ 提前完成", stats['early'], self.colors['info']),
            ("⬇️ 延后完成", stats['late'], self.colors['warning']),
            # ("∞ 无时限任务完成", stats['timeless'], self.colors['secondary'])
        ]
        
        for i, (label, count, color) in enumerate(categories):
            row = i
            col = 0
            
            # 创建统计卡片
            card = tk.Frame(details_frame, bg=color, relief=tk.RAISED, bd=1)
            card.grid(row=row, column=col, padx=5, pady=5, sticky='ew')
            
            # 配置网格权重
            details_frame.grid_rowconfigure(row, weight=1)
            details_frame.grid_columnconfigure(col, weight=1)
            
            # 水平布局
            content_frame = tk.Frame(card, bg=color)
            content_frame.pack(fill=tk.X, padx=10, pady=10)
            
            # 数量显示
            count_label = tk.Label(content_frame, 
                                  text=str(count),
                                  font=('Microsoft YaHei', 20, 'bold'),
                                  bg=color,
                                  fg='white',
                                  width=3)
            count_label.pack(side=tk.LEFT, padx=(0, 10))
            
            # 类别标签
            type_label = tk.Label(content_frame,
                                 text=label,
                                 font=self.fonts['normal'],
                                 bg=color,
                                 fg='white')
            type_label.pack(side=tk.LEFT)
            
            # 百分比（如果有总数）
            if total_completed > 0:
                percentage = (count / total_completed) * 100
                percent_label = tk.Label(content_frame,
                                        text=f"{percentage:.1f}%",
                                        font=self.fonts['small'],
                                        bg=color,
                                        fg='white')
                percent_label.pack(side=tk.RIGHT)
        
    def setup_notebook_style(self, notebook):
        """设置选项卡的样式 - 去掉悬停放大效果"""
        style = ttk.Style()
        
        # 配置选项卡样式 - 去掉放大效果，只保留颜色变化
        style.configure('Custom.TNotebook.Tab', font=self.fonts['bold'])
        
        style.map('Custom.TNotebook.Tab',
                 background=[('active', self.colors['gray_light']),
                            ('!active', self.colors['light'])],
                 foreground=[('active', self.colors['primary_dark']),
                            ('!active', self.colors['gray_dark'])])
        
        # 应用样式
        notebook.configure(style='Custom.TNotebook')
        
    def setup_radio_hover(self, radio_button):
        """为单选按钮设置悬停效果"""
        original_bg = radio_button.cget('bg')
        original_fg = radio_button.cget('fg')
        
        def on_enter(event):
            radio_button.configure(bg=self.colors['gray_light'], fg=self.colors['primary'])
        
        def on_leave(event):
            radio_button.configure(bg=original_bg, fg=original_fg)
        
        radio_button.bind("<Enter>", on_enter)
        radio_button.bind("<Leave>", on_leave)
        
    def setup_card_hover(self, card_frame, canvas):
        """为卡片设置悬停效果"""
        original_bg = card_frame.cget('bg')
        hover_bg = self.adjust_color(original_bg, -5)  # 稍微变暗
        
        def on_enter(event):
            card_frame.configure(bg=hover_bg)
            canvas.configure(bg=hover_bg)
            # 更新画布背景
            for item in canvas.find_all():
                if canvas.type(item) == 'rectangle':
                    canvas.itemconfig(item, fill=hover_bg)
        
        def on_leave(event):
            card_frame.configure(bg=original_bg)
            canvas.configure(bg=original_bg)
            # 恢复画布背景
            for item in canvas.find_all():
                if canvas.type(item) == 'rectangle':
                    canvas.itemconfig(item, fill=original_bg)
        
        card_frame.bind("<Enter>", on_enter)
        card_frame.bind("<Leave>", on_leave)
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
                
    def enhanced_refresh(self):
        """增强的刷新功能，带有视觉反馈"""
        # 显示加载状态
        original_text = self.status_label.cget('text')
        self.status_label.config(text="🔄刷新中...")
        
        # 强制更新界面
        self.root.update()
        
        try:
            # 执行刷新
            self.refresh_display()
            
            # 显示成功状态
            self.status_label.config(text="✅刷新完成")
            
            # 2秒后恢复原始状态
            self.root.after(2000, lambda: self.status_label.config(text=original_text))
            
        except Exception as e:
            self.status_label.config(text=f"❌刷新失败: {str(e)}")
            
    def adjust_color(self, color, delta):
        """调整颜色亮度"""
        if isinstance(color, str) and color.startswith("#"):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            
            r = max(0, min(255, r + delta))
            g = max(0, min(255, g + delta))
            b = max(0, min(255, b + delta))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        return color
        
    def update_tab_titles(self):
        """专门更新选项卡标题中的任务数量"""
        # 查找Notebook组件
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame):
                # 在主容器中查找Notebook
                for child in widget.winfo_children():
                    if isinstance(child, tk.Frame):
                        for grandchild in child.winfo_children():
                            if isinstance(grandchild, ttk.Notebook):
                                # 更新选项卡标题
                                if grandchild.tabs():
                                    grandchild.tab(0, text=f"📋待办事项 ({len(self.todo_items)})")
                                    if len(grandchild.tabs()) > 1:
                                        grandchild.tab(1, text=f"✅已完成 ({len(self.completed_items)})")
                                return

    # 修改现有的相关方法
    def forget_login(self):
        """忘记登录信息"""
        if messagebox.askyesno("忘记登录", "确定要清除记住的登录信息吗？下次启动时需要重新登录。"):
            self.user_manager.forget_user()
            self.hide_user_menu()  # 关闭菜单
            self.status_label.config(text="✅ 已清除记住的登录信息")

    def safe_update_status(self, message):
        """安全更新状态标签"""
        try:
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.config(text=message)
        except Exception as e:
            print(f"更新状态标签失败: {e}")
 
    def clear_main_interface(self):
        """清空主界面内容，准备显示登录界面"""
        try:
            # 保存窗口尺寸和位置
            window_geometry = self.root.geometry()
            
            # 销毁主界面所有组件
            for widget in self.root.winfo_children():
                widget.destroy()
            
            # 重新设置窗口基本属性
            self.root.title("待办事项管理器 - TaskFlow")
            self.root.geometry(window_geometry)  # 保持窗口尺寸和位置
            self.root.configure(bg='#f8f9fa')
            
            # 设置图标
            try:
                self.root.iconbitmap("icon.ico")
            except:
                pass
                
        except Exception as e:
            print(f"清空界面时出错: {e}")
            # 如果出错，重新创建应用实例
            self.reinitialize_application()

    def reinitialize_application(self):
        """重新初始化应用"""
        # 完全重新初始化
        self.__init__(self.root)

    def show_login_dialog(self):
        """显示登录对话框 - 修复版本"""
        # 确保窗口显示
        self.root.deiconify()
        
        def on_login_success():
            """登录成功后的回调"""
            # 登录成功后重新初始化应用
            self.initialize_application()
            # 安全地更新状态标签
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.config(text="✅ 用户切换成功")
        
        def on_login_cancel():
            """登录取消后的处理 - 直接渐变关闭"""
            def fade_out(alpha=1.0):
                """透明度渐变关闭效果"""
                try:
                    if alpha > 0:
                        self.root.attributes('-alpha', alpha)
                        # 每20毫秒减少0.1透明度
                        self.root.after(20, lambda: fade_out(alpha - 0.1))
                    else:
                        # 渐变完成后直接退出
                        self.root.quit()
                except Exception as e:
                    # 如果渐变过程中出错，直接退出
                    self.root.quit()
            
            # 开始渐变关闭
            fade_out()
        
        # 创建登录对话框
        self.login_dialog = LoginDialog(self.root, self.user_manager, on_login_success)
        
        # 监听对话框关闭事件
        self.login_dialog.dialog.protocol("WM_DELETE_WINDOW", on_login_cancel)
    
def show_splash_screen(root):
    """显示启动界面"""
    splash = tk.Toplevel(root)
    splash.title("TaskFlow - 启动中")
    splash.geometry("500x400")
    splash.configure(bg='#f8f9fa')
    
    # 居中显示
    splash.overrideredirect(True)
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width - 500) // 2
    y = (screen_height - 400) // 2
    splash.geometry(f"500x400+{x}+{y}")
    
    # 设置颜色方案
    colors = {
        'primary': '#4361ee',
        'primary_light': '#4895ef',
        'bg_main': '#f8f9fa',
        'bg_card': '#ffffff',
        'text_primary': '#212529',
        'text_secondary': '#6c757d'
    }
    
    # 创建启动界面UI
    main_frame = tk.Frame(splash, bg=colors['bg_main'], 
                         highlightbackground=colors['primary'], 
                         highlightthickness=2)
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 应用标题和图标
    title_frame = tk.Frame(main_frame, bg=colors['bg_main'])
    title_frame.pack(fill=tk.X, pady=(40, 20))
    
    icon_label = tk.Label(title_frame, text="📋", font=('Arial', 48), 
                         bg=colors['bg_main'], fg=colors['primary'])
    icon_label.pack()
    
    app_name_label = tk.Label(title_frame, text="TaskFlow", 
                             font=('Microsoft YaHei', 24, 'bold'),
                             bg=colors['bg_main'], fg=colors['primary'])
    app_name_label.pack(pady=(10, 5))
    
    subtitle_label = tk.Label(title_frame, text="待办事项管理器", 
                             font=('Microsoft YaHei', 12),
                             bg=colors['bg_main'], fg=colors['text_secondary'])
    subtitle_label.pack()
    
    # 进度条
    progress_frame = tk.Frame(main_frame, bg=colors['bg_main'])
    progress_frame.pack(fill=tk.X, padx=50, pady=(40, 20))
    
    progress = ttk.Progressbar(progress_frame, mode='determinate', length=400, maximum=100)
    progress.pack(fill=tk.X)
    
    progress_label = tk.Label(progress_frame, text="正在初始化应用... 0%",
                             font=('Microsoft YaHei', 9), bg=colors['bg_main'],
                             fg=colors['text_secondary'])
    progress_label.pack(pady=(10, 0))
    
    # status_label = tk.Label(main_frame, text="准备启动...",
                           # font=('Microsoft YaHei', 8), bg=colors['bg_main'],
                           # fg=colors['text_secondary'])
    # status_label.pack(side=tk.BOTTOM, pady=(0, 15))
    
    # 版权信息
    copyright_label = tk.Label(main_frame, 
                              text="© 2026 TaskFlow. All rights reserved.",
                              font=('Microsoft YaHei', 7),
                              bg=colors['bg_main'],
                              fg=colors['text_secondary'])
    copyright_label.pack(side=tk.BOTTOM, pady=(0, 5))
    
    # 更新进度函数
    def update_progress(value, message=""):
        progress['value'] = min(value, 100)
        progress_label.config(text=f"{message} {progress['value']}%")
        splash.update()
    
    def update_status(message):
        status_label.config(text=message)
        splash.update()
    
    # 模拟加载过程
    def simulate_loading():
        loading_steps = [
            (10, "正在初始化应用..."), 
            (25, "正在加载配置文件..."),
            (40, "正在初始化界面..."), 
            (60, "正在加载数据..."),
            (80, "正在启动服务..."), 
            (95, "正在完成启动..."),
            (100, "启动完成!")
        ]
        
        for progress_val, message in loading_steps:
            splash.after(300, update_progress, progress_val, message)
            splash.update()
            time.sleep(0.3)  # 模拟加载延迟
    
    # 开始加载动画
    splash.after(100, simulate_loading)
    return splash
    
def main():
    """主函数 - 添加托盘支持"""
    root = tk.Tk()
    root.withdraw()  # 先隐藏主窗口
    
    # 显示启动界面
    splash = show_splash_screen(root)
    
    # 全局应用实例
    app_instance = None
    
    def safe_status_update(message):
        """安全更新状态标签"""
        if app_instance and hasattr(app_instance, 'status_label') and app_instance.status_label:
            try:
                app_instance.status_label.config(text=message)
            except Exception as e:
                print(f"更新状态标签失败: {e}")

    def initialize_app():
        nonlocal app_instance
        try:
            # 创建应用实例
            app_instance = TodoApp(root)
            
            # 计算居中位置
            root.update_idletasks()
            width = 1320
            height = 880
            x = (root.winfo_screenwidth() // 2) - (width // 2)
            y = (root.winfo_screenheight() // 2) - (height // 2)
            root.geometry(f'{width}x{height}+{x}+{y}')
            
            # 设置窗口初始为完全透明
            root.attributes('-alpha', 0.0)
            
            # 显示主窗口
            root.deiconify()
            
            def fade_in_window():
                """透明度渐变效果"""
                current_alpha = 0.0
                
                def fade_step():
                    nonlocal current_alpha
                    try:
                        current_alpha += 0.1
                        root.attributes('-alpha', current_alpha)
                        
                        if current_alpha < 1.0:
                            root.after(25, fade_step)
                        else:
                            splash.destroy()
                            root.focus_force()
                            safe_status_update("✅ 应用启动完成")
                    except Exception as e:
                        print(f"渐变效果错误: {e}")
                        try:
                            splash.destroy()
                            root.attributes('-alpha', 1.0)
                            root.focus_force()
                        except:
                            pass
                
                fade_step()
            
            root.after(300, fade_in_window)
            
            return app_instance
            
        except Exception as e:
            try:
                splash.destroy()
            except:
                pass
            root.quit()
            messagebox.showerror("启动错误", f"应用启动失败: {str(e)}")
            return None

    # 延迟初始化
    root.after(2800, initialize_app)
    
    root.mainloop()

if __name__ == "__main__":
    main()