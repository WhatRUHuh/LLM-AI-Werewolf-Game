#Werewolf.py
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import tkinter as tk
from tkinter import messagebox, PhotoImage
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import random
import time
from PIL import Image, ImageTk
from record import create_record_folder, create_day_record_folder

# 配置代理（确保所有请求走代理）
os.environ["HTTP_PROXY"] = "http://127.0.0.1:10808"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10808"

# 导入配置、日志、记录与模型模块
from TTS import play_tts
from config import init_config
from log import log_to_file
from record import (save_daytime_speech, save_daytime_vote,
                    save_night_speech, save_night_vote, save_last_words_record)
# from readrecord import get_history_summary  # 已删除，此函数已移至 GameLogicHandler.py
from GameState import GameState  # 导入 GameState 类
from UIHandler import UIHandler  # 导入 UIHandler 类
from GameLogicHandler import GameLogicHandler  # 导入 GameLogicHandler 类
from SpeechHandler import SpeechHandler  # 导入 SpeechHandler 类
from VoteHandler import VoteHandler  # 导入 VoteHandler 类
from ModelHandler import ModelHandler  # 导入 ModelHandler 类
from SoundHandler import SoundHandler  # 导入 SoundHandler 类


# ---------------------- 游戏启动页面 ----------------------
class StartPage:
    def __init__(self, root):
        self.root = root
        
        # 初始化声音系统
        self.sound_handler = SoundHandler()
        
        # 加载原始背景图片（不调整大小）
        self.original_bg_image = None
        try:
            print("尝试加载背景图片: source/初始背景.jpg")
            self.original_bg_image = Image.open("source/初始背景.jpg")
            print("背景图片加载成功!")
        except Exception as e:
            print(f"加载背景图片失败: {e}")
        
        # 保存实际显示的窗口大小
        self.current_width = 1200
        self.current_height = 800
        
        self.create_start_page()
        
        # 绑定窗口大小变化事件
        self.root.bind("<Configure>", self.on_window_resize)
        
        # 播放狼叫声
        self.sound_handler.play_wolf_howl()
        
    def create_start_page(self):
        # 清空root中的所有控件
        for widget in self.root.winfo_children():
            widget.destroy()
            
        # 获取当前屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 设置初始窗口大小（普通大小，不是最大化）
        if not hasattr(self, 'current_width') or not hasattr(self, 'current_height'):
            self.current_width = min(1200, screen_width-100)
            self.current_height = min(800, screen_height-100)
        
        # 窗口居中
        center_x = int(screen_width/2 - self.current_width/2)
        center_y = int(screen_height/2 - self.current_height/2)
        
        # 只有在窗口创建时设置位置，避免在全屏时重置
        if not hasattr(self, 'canvas'):
            self.root.geometry(f'{self.current_width}x{self.current_height}+{center_x}+{center_y}')
        
        # 创建一个框架覆盖整个窗口
        self.start_frame = tk.Frame(self.root)
        self.start_frame.pack(fill=tk.BOTH, expand=True)
        
        # 尝试加载背景图片并创建全屏Canvas
        try:
            if self.original_bg_image:
                # 获取当前窗口的实际大小
                window_width = self.root.winfo_width() or self.current_width
                window_height = self.root.winfo_height() or self.current_height
                
                # 更新保存的尺寸
                self.current_width = window_width
                self.current_height = window_height
                
                # 计算字体大小的缩放比例（基于基准大小1200x800）
                base_width = 1200
                base_height = 800
                width_ratio = window_width / base_width
                height_ratio = window_height / base_height
                scale_ratio = min(width_ratio, height_ratio)  # 取较小值，确保文本不会太大
                
                # 计算缩放后的字体大小
                title_font_size = int(48 * scale_ratio)
                button_font_size = int(24 * scale_ratio)
                
                # 确保字体大小不会太小
                title_font_size = max(title_font_size, 32)
                button_font_size = max(button_font_size, 18)
                
                # 调整图片大小
                resized_image = self.original_bg_image.resize((window_width, window_height), Image.LANCZOS)
                self.bg_photo = ImageTk.PhotoImage(resized_image)
                
                # 创建Canvas作为背景
                self.canvas = tk.Canvas(self.start_frame, width=window_width, height=window_height, 
                                       highlightthickness=0)
                self.canvas.pack(fill=tk.BOTH, expand=True)
                
                # 显示背景图片
                self.canvas.create_image(0, 0, image=self.bg_photo, anchor=tk.NW)
                
                # 添加标题文字直接到Canvas（使用缩放后的字体大小）
                title_text = self.canvas.create_text(
                    window_width // 2, window_height * 0.2, 
                    text="AI大模型狼人杀",
                    font=("SourceHanSansCN-Bold.otf", title_font_size, "bold"), 
                    fill="#990000"  # 红色文字
                )
                
                # 添加"开始游戏"文本到Canvas（使用缩放后的字体大小）
                button_text = self.canvas.create_text(
                    window_width // 2, window_height * 0.6,
                    text="开始游戏",
                    font=("SourceHanSansCN-Bold.otf", button_font_size, "bold"),
                    fill="#990000"  # 红色文字
                )
                
                # 为"开始游戏"文本添加点击事件
                self.canvas.tag_bind(button_text, "<Button-1>", lambda e: self.start_game())
                
                # 为"开始游戏"文本添加鼠标悬停效果
                self.canvas.tag_bind(button_text, "<Enter>", 
                                    lambda e: self.canvas.itemconfig(button_text, fill="#BB0000"))
                self.canvas.tag_bind(button_text, "<Leave>", 
                                    lambda e: self.canvas.itemconfig(button_text, fill="#990000"))
            else:
                raise Exception("背景图片未加载")
        except Exception as e:
            print(f"设置背景失败: {e}")
            self.start_frame.configure(bg="black")
            # 添加简单的文本标签
            tk.Label(self.start_frame, text="AI大模型狼人杀", font=("SourceHanSansCN-Bold.otf", 48), fg="white", bg="black").pack(pady=100)
            tk.Button(self.start_frame, text="开始游戏", font=("SourceHanSansCN-Bold.otf", 24), command=self.start_game).pack()
            
    def on_window_resize(self, event):
        """窗口大小变化事件处理"""
        # 只处理窗口大小变化事件，忽略子组件的大小变化事件
        if event.widget == self.root:
            # 获取新的窗口大小
            new_width = event.width
            new_height = event.height
            
            # 如果窗口大小变化超过一定阈值，则重新创建页面
            if (abs(new_width - self.current_width) > 10 or 
                abs(new_height - self.current_height) > 10):
                self.current_width = new_width
                self.current_height = new_height
                self.create_start_page()
                
    def start_game(self):
        """启动主游戏"""
        # 解绑窗口大小变化事件
        self.root.unbind("<Configure>")
        # 销毁开始页面
        self.start_frame.destroy()
        # 启动游戏
        app = WerewolfGameApp(self.root)


# ---------------------- 狼人杀游戏主应用 ----------------------
class WerewolfGameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("狼人杀小游戏")
        # 设置窗口大小和位置
        window_width = 1200
        window_height = 800
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        # 设置窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        create_record_folder()
        # 创建第0天的记录文件夹
        create_day_record_folder(0)
        
        self.player_count = 8    # 默认玩家人数
        self.wolf_count = 2      # 默认狼人数量
        self.seer_count = 1      # 默认预言家数量
        self.hunter_count = 0    # 默认猎人数量
        self.witch_count = 0     # 默认女巫数量
        self.tts_enabled = init_config()  # 从 config.ini 加载 TTS 启用配置，默认为 True
        self.tts_speed = "+0%"   # 默认TTS语音速度
        self.state = self.create_game_state()  # 使用专门的方法创建 GameState
        self.last_voter_id = None  # 用于记录最后投票的玩家ID，方便主持人改票
        self.sheriff_labels = {}  # 用于存储每个玩家的警长标签
        
        # 初始化音效处理器 (在UI创建前)
        self.sound_handler = SoundHandler()
        self.sound_enabled = True  # 音效开关
        self.sound_enabled_var = tk.BooleanVar(value=self.sound_enabled)  # 用于UI组件

        # 初始化各种 Handler
        self.model_handler = ModelHandler(self)          # ModelHandler *最先* 创建
        self.game_logic_handler = GameLogicHandler(self)   # 第二个创建
        self.ui_handler = UIHandler(root, self)            # 第三个创建
        self.speech_handler = SpeechHandler(self)          # 第四个创建
        self.vote_handler = VoteHandler(self)              # 第五个创建

        self.speak_buttons = self.ui_handler.app.speak_buttons
        self.vote_buttons = self.ui_handler.app.vote_buttons
        self.lastword_buttons = self.ui_handler.app.lastword_buttons
        self.identity_dropdowns = self.ui_handler.app.identity_dropdowns
        self.model_dropdowns = self.ui_handler.app.model_dropdowns
        self.day_label = self.ui_handler.app.day_label
        self.daytime_btn = self.ui_handler.app.daytime_btn
        self.day_voting_btn = self.ui_handler.app.day_voting_btn
        self.night_btn = self.ui_handler.app.night_btn
        self.night_voting_btn = self.ui_handler.app.night_voting_btn
        self.next_round_btn = self.ui_handler.app.next_round_btn
        self.summary_text = self.ui_handler.app.summary_text
        self.clear_summary_btn = self.ui_handler.app.clear_summary_btn
        self.correct_vote_btn = self.ui_handler.app.correct_vote_btn
        self.correct_vote_btn.config(command=self.ui_handler.open_correct_vote_popup)
        # self.correct_vote_btn.config(state=tk.DISABLED)  # 删除此行，按钮永远启用
        self.player_count_var = self.ui_handler.app.player_count_var
        self.player_count_spin = self.ui_handler.app.player_count_spin
        self.wolf_count_var = self.ui_handler.app.wolf_count_var
        self.wolf_count_spin = self.ui_handler.app.wolf_count_spin
        # 预言家数量变量和 Spinbox 在 UIHandler 中创建
        self.seer_count_var = self.ui_handler.app.seer_count_var
        self.seer_count_spin = self.ui_handler.app.seer_count_spin
        # 猎人数量变量和 Spinbox 在 UIHandler 中创建
        self.hunter_count_var = self.ui_handler.app.hunter_count_var
        self.hunter_count_spin = self.ui_handler.app.hunter_count_spin
        # 女巫数量变量和 Spinbox 在 UIHandler 中创建
        self.witch_count_var = self.ui_handler.app.witch_count_var
        self.witch_count_spin = self.ui_handler.app.witch_count_spin

        self.apply_config_btn = self.ui_handler.app.apply_config_btn
        self.restart_btn = self.ui_handler.app.restart_btn
        self.tts_enabled_var = self.ui_handler.app.tts_enabled_var  # TTS 开关变量

        # 添加音效开关到UI (在UIHandler创建后)
        config_frame = self.ui_handler.config_frame  # 获取配置面板引用
        if hasattr(self.ui_handler, 'config_frame'):
            ttk.Checkbutton(config_frame, text="启用音效", 
                            variable=self.sound_enabled_var, 
                            command=self.toggle_sound).grid(row=2, column=3, padx=5, pady=5, sticky="w")
        else:
            print("警告: 无法添加音效开关，找不到config_frame")

    def create_game_state(self, player_count=None, wolf_count=None, seer_count=None, hunter_count=None, witch_count=None):
        """创建 GameState 实例"""
        if player_count is None:
            player_count = self.player_count
        if wolf_count is None:
            wolf_count = self.wolf_count
        if seer_count is None:
            seer_count = self.seer_count
        if hunter_count is None:
            hunter_count = self.hunter_count
        if witch_count is None:
            witch_count = self.witch_count
        return GameState(player_count=player_count, wolf_count=wolf_count, seer_count=seer_count, hunter_count=hunter_count, witch_count=witch_count)

    def toggle_tts(self):
        """切换 TTS 启用状态"""
        self.tts_enabled = not self.tts_enabled
        self.log_system(f"TTS 已 {'启用' if self.tts_enabled else '禁用'}")
        
    def set_tts_speed(self, speed):
        """设置 TTS 语音速度"""
        self.tts_speed = speed
        self.log_system(f"TTS 语音速度已设置为 {speed}")

    def clear_summary_text(self):
        """清空游戏总统计窗口的文字"""
        self.summary_text.delete("1.0", tk.END)
        self.log_system("游戏统计信息已清空。")

    def correct_last_vote(self):  # 已删除此方法
        """纠正上次投票"""
        self.game_logic_handler.correct_last_vote()

    def update_buttons_for_phase(self, phase):
        """更新按钮状态"""
        self.game_logic_handler.update_buttons_for_phase(phase)

    def apply_config(self):
        """应用配置"""
        # 从 UI 界面获取玩家人数、狼人数量、预言家数量和猎人数量
        self.player_count = self.ui_handler.app.player_count_var.get()
        self.wolf_count = self.ui_handler.app.wolf_count_var.get()
        self.seer_count = self.ui_handler.app.seer_count_var.get()
        self.hunter_count = self.ui_handler.app.hunter_count_var.get()
        self.witch_count = self.ui_handler.app.witch_count_var.get()
        # 重新创建 GameState 对象
        self.state = self.create_game_state()
        self.ui_handler.update_player_frames_config()  # 玩家数量变化后，更新玩家框架
        self.log_system(f"游戏配置已更新：玩家人数 = {self.player_count}，狼人数量 = {self.wolf_count}，预言家数量 = {self.seer_count}，猎人数量 = {self.hunter_count}，女巫数量 = {self.witch_count}")

    def restart_game(self):
        """重新开始游戏"""
        # 先清理文件夹
        self.cleanup_folders()
        # 然后重新开始游戏
        self.game_logic_handler.restart_game()

    def update_player_identity(self, player_id, new_identity):
        """更新玩家身份"""
        self.game_logic_handler.update_player_identity(player_id, new_identity)

    def update_player_model(self, player_id, new_model):
        """更新玩家模型"""
        self.game_logic_handler.update_player_model(player_id, new_model)

    def log_system(self, message):
        """记录系统日志"""
        message = message.replace("\\n", "\n")
        self.summary_text.insert(tk.END, f"{message}\n", "system")
        self.summary_text.see(tk.END)

    def log_player(self, player_id, message):
        """记录玩家日志"""
        message = message.replace("\\n", "\n")
        tag = f"p{player_id}"
        self.summary_text.insert(tk.END, f"{message}\n", tag)
        self.summary_text.see(tk.END)

    def get_history_summary(self):
        """获取历史总结"""
        return self.game_logic_handler.get_history_summary()

    def print_day_status(self):
        """打印白天状态"""
        self.game_logic_handler.print_day_status()

    # ---------------------- 发言阶段 ----------------------
    def player_speak(self, player_id):
        """玩家发言"""
        self.speech_handler.player_speak(player_id)

    # ---------------------- 投票阶段 ----------------------
    def player_vote(self, player_id):
        """玩家投票"""
        self.last_voter_id = player_id
        # self.correct_vote_btn.config(state=tk.NORMAL)  # 删除动态启用按钮
        self.vote_handler.player_vote(player_id)

    # ---------------------- 遗言阶段 ----------------------
    # 删除 record_last_words 方法，该功能由 SpeechHandler 中的逻辑处理

    def end_game(self, winner, cleanup=False):
        """结束游戏
        
        Args:
            winner: 胜利方，"villagers"表示好人阵营胜利，"wolves"表示狼人阵营胜利
            cleanup: 是否清理record和log文件夹，默认为False
        """
        self.game_logic_handler.end_game(winner)
        
        # 如果需要清理文件夹
        if cleanup:
            self.cleanup_folders()

    def start_daytime(self):
        """开始白天"""
        self.game_logic_handler.start_daytime()

    def finalize_day_voting(self):
        """结束白天投票"""
        self.game_logic_handler.finalize_day_voting()

    def start_night(self):
        """开始夜晚"""
        self.game_logic_handler.start_night()
        # 注释掉这里的播放狼叫声，因为已经在UIHandler.phase_change_with_theme中实现
        # self.sound_handler.play_wolf_howl()
        # 确保女巫投票按钮始终启用
        for i, p in self.state.players.items():
            if p.exists and p.alive and p.identity == "女巫":
                self.vote_buttons[i].config(state=tk.NORMAL)

    def finalize_night_voting(self):
        """结束夜晚投票"""
        self.game_logic_handler.finalize_night_voting()

    def next_round(self):
        """下一回合"""
        self.game_logic_handler.next_round()

    def toggle_sound(self):
        """切换游戏音效"""
        self.sound_enabled = not self.sound_enabled
        self.sound_handler.set_enabled(self.sound_enabled)
        self.log_system(f"游戏音效已 {'启用' if self.sound_enabled else '禁用'}")
    
    def cleanup_folders(self):
        """清理record和log文件夹"""
        import shutil
        
        # 清理record文件夹
        record_folder = "record"
        if os.path.exists(record_folder):
            try:
                shutil.rmtree(record_folder)
                print(f"已删除{record_folder}文件夹")
            except Exception as e:
                print(f"删除{record_folder}文件夹失败: {e}")
        
        # 清理log文件夹
        log_folder = "log"
        if os.path.exists(log_folder):
            try:
                shutil.rmtree(log_folder)
                print(f"已删除{log_folder}文件夹")
            except Exception as e:
                print(f"删除{log_folder}文件夹失败: {e}")

    def on_closing(self):
        """处理窗口关闭事件"""
        self.end_game(None, cleanup=True)  # 结束游戏并清理文件夹
        self.root.destroy()  # 销毁窗口


if __name__ == '__main__':
    init_config()  # 初始化配置与代理设置
    # 使用ttk.Window替代tk.Tk，以支持ttkbootstrap主题
    root = ttk.Window(themename="journal", title="AI大模型狼人杀")
    # 首先显示启动页面
    start_page = StartPage(root)
    root.mainloop()
