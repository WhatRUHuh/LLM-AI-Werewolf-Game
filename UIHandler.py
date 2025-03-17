#UIHandler.py
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import random  # 导入 random 模块
from PIL import Image, ImageTk

class UIHandler:
    def __init__(self, root, app):
        self.root = root
        self.app = app  # self.app 指向 WerewolfGameApp 实例
        self.app.player_colors = {1:"red",2:"green",3:"blue",4:"magenta",5:"#4169E1",6:"#191970",7:"#F5B041",8:"#A98D6F",9:"#79CEDC",10:"#5A6A7A"}
        
        # 添加主题相关属性 - 修改为更合适的主题
        self.day_theme = "journal"  # 白天主题 - 真正的橙色系
        self.night_theme = "flatly"  # 夜晚主题 - 淡灰色系，提供更舒适的视觉体验
        self.current_theme = self.day_theme
        
        # 存储头像引用，防止被垃圾回收
        self.player_avatars = {}
        
        # 头像映射关系
        self.avatar_mapping = {
            "平民": "source/平民.jpg",
            "狼人": "source/狼人.jpg",
            "预言家": "source/预言家.jpg",
            "猎人": "source/猎人.jpg",
            "女巫": "source/女巫.jpg",
            "空": "source/默认.jpg"  # 默认头像
        }
        
        self.create_widgets()

    def create_widgets(self):
        # 配置面板
        self.config_frame = ttk.Labelframe(self.root, text="游戏配置", padding=10)
        self.config_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(self.config_frame, text="玩家数量（3-10）：").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.app.player_count_var = tk.IntVar(value=self.app.player_count)
        self.app.player_count_spin = ttk.Spinbox(self.config_frame, from_=3, to=10, textvariable=self.app.player_count_var, width=5)
        self.app.player_count_spin.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(self.config_frame, text="狼人数量：").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.app.wolf_count_var = tk.IntVar(value=self.app.wolf_count)
        self.app.wolf_count_spin = ttk.Spinbox(self.config_frame, from_=1, to=10, textvariable=self.app.wolf_count_var, width=5)
        self.app.wolf_count_spin.grid(row=0, column=3, padx=5, pady=5)
        # 新增预言家数量调整框
        ttk.Label(self.config_frame, text="预言家数量：").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.app.seer_count_var = tk.IntVar(value=self.app.seer_count)
        self.app.seer_count_spin = ttk.Spinbox(self.config_frame, from_=0, to=5, textvariable=self.app.seer_count_var, width=5)
        self.app.seer_count_spin.grid(row=1, column=1, padx=5, pady=5)
        # 新增猎人数量调整框
        ttk.Label(self.config_frame, text="猎人数量：").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.app.hunter_count_var = tk.IntVar(value=self.app.hunter_count)
        self.app.hunter_count_spin = ttk.Spinbox(self.config_frame, from_=0, to=5, textvariable=self.app.hunter_count_var, width=5)
        self.app.hunter_count_spin.grid(row=1, column=3, padx=5, pady=5)
        # 新增女巫数量调整框
        ttk.Label(self.config_frame, text="女巫数量：").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.app.witch_count_var = tk.IntVar(value=self.app.witch_count)
        self.app.witch_count_spin = ttk.Spinbox(self.config_frame, from_=0, to=5, textvariable=self.app.witch_count_var, width=5)
        self.app.witch_count_spin.grid(row=2, column=1, padx=5, pady=5)
        # TTS 开关
        self.app.tts_enabled_var = tk.BooleanVar(value=self.app.tts_enabled) # 初始化为 WerewolfGameApp 的 tts_enabled 值
        ttk.Checkbutton(self.config_frame, text="启用 TTS", variable=self.app.tts_enabled_var, command=self.app.toggle_tts).grid(row=2, column=4, padx=5, pady=5, sticky="w")

        self.app.apply_config_btn = ttk.Button(self.config_frame, text="应用配置", command=self.app.apply_config)
        self.app.apply_config_btn.grid(row=0, column=5, padx=5, pady=5)
        self.app.restart_btn = ttk.Button(self.config_frame, text="重新开始游戏", command=self.app.game_logic_handler.restart_game)
        self.app.restart_btn.grid(row=0, column=6, padx=5, pady=5)
        # 主持人控制面板
        self.app.mod_frame = ttk.Labelframe(self.root, text="主持人控制面板", padding=10)
        self.app.mod_frame.pack(fill=tk.X, padx=10, pady=5)
        self.app.day_label = ttk.Label(self.app.mod_frame, text=f"第 {self.app.state.day} 天")
        self.app.day_label.pack(side=tk.LEFT, padx=5)
        
        # 修改按钮命令以包含主题切换
        self.app.daytime_btn = ttk.Button(self.app.mod_frame, text="开始白天发言", 
                                           command=lambda: self.phase_change_with_theme("day"))
        self.app.daytime_btn.pack(side=tk.LEFT, padx=5)
        self.app.day_voting_btn = ttk.Button(self.app.mod_frame, text="开始白天投票", 
                                              command=self.app.game_logic_handler.finalize_day_voting)
        self.app.day_voting_btn.pack(side=tk.LEFT, padx=5)
        self.app.night_btn = ttk.Button(self.app.mod_frame, text="开始夜晚回合", 
                                         command=lambda: self.phase_change_with_theme("night"))
        self.app.night_btn.pack(side=tk.LEFT, padx=5)
        self.app.night_voting_btn = ttk.Button(self.app.mod_frame, text="开始夜晚投票", 
                                                command=self.app.game_logic_handler.finalize_night_voting)
        self.app.night_voting_btn.pack(side=tk.LEFT, padx=5)
        self.app.next_round_btn = ttk.Button(self.app.mod_frame, text="下一回合", 
                                              command=lambda: self.phase_change_with_theme("next_round"))
        self.app.next_round_btn.pack(side=tk.LEFT, padx=5)
        # 主体界面
        self.app.main_frame = ttk.Frame(self.root)
        self.app.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        players_container = ttk.Frame(self.app.main_frame)
        players_container.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
        self.players_canvas = tk.Canvas(players_container, borderwidth=0)
        self.players_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        v_scrollbar = ttk.Scrollbar(players_container, orient="vertical", command=self.players_canvas.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.players_canvas.configure(yscrollcommand=v_scrollbar.set)
        h_scrollbar = ttk.Scrollbar(players_container, orient="horizontal", command=self.players_canvas.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.players_canvas.configure(xscrollcommand=h_scrollbar.set)
        self.players_frame = ttk.Frame(self.players_canvas)
        self.players_canvas.create_window((0, 0), window=self.players_frame, anchor="nw")
        self.players_frame.bind("<Configure>", lambda e: self.players_canvas.configure(scrollregion=self.players_canvas.bbox("all")))
        self.app.speak_buttons = {}
        self.app.vote_buttons = {}
        self.app.lastword_buttons = {}
        self.app.identity_dropdowns = {}
        self.app.model_dropdowns = {}
        self.create_player_frames()
        self.summary_frame = ttk.Labelframe(self.app.main_frame, text="游戏总统计", padding=10)
        self.summary_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        summary_scrollbar = ttk.Scrollbar(self.summary_frame, orient="vertical")
        self.app.summary_text = tk.Text(self.summary_frame, width=60, height=30,
                                    yscrollcommand=summary_scrollbar.set, wrap="word")
        summary_scrollbar.config(command=self.app.summary_text.yview)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.app.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.app.clear_summary_btn = ttk.Button(self.summary_frame, text="清空统计", command=self.app.clear_summary_text)
        self.app.clear_summary_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        self.app.correct_vote_btn = ttk.Button(self.summary_frame, text="纠正上次投票", command=self.open_correct_vote_popup)
        self.app.correct_vote_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        # 配置 tag
        for pid, color in self.app.player_colors.items():
            self.app.summary_text.tag_config(f"p{pid}", foreground=color, font=("SourceHanSansCN-Bold.otf", 32))
        self.app.summary_text.tag_config("system", foreground="black", font=("SourceHanSansCN-Bold.otf", 32))
        self.app.game_logic_handler.update_buttons_for_phase("day")
        
        # 默认应用白天主题
        self.apply_theme(self.day_theme)

    # 添加切换主题的方法
    def apply_theme(self, theme_name):
        """应用指定的主题"""
        if theme_name == self.current_theme:
            return  # 如果已经是当前主题，不需要切换
            
        # 记录当前主题
        self.current_theme = theme_name
        
        # 更新窗口主题
        self.root.style.theme_use(theme_name)
        
        # 主题切换后的其他视觉调整
        if theme_name == self.night_theme:
            self.app.log_system("【主题切换】已切换至夜晚主题")
        else:
            self.app.log_system("【主题切换】已切换至白天主题")
    
    # 带主题切换的阶段转换方法
    def phase_change_with_theme(self, phase):
        """处理阶段变化并切换相应的主题"""
        if phase == "day" or phase == "next_round":
            # 应用白天主题
            self.apply_theme(self.day_theme)
            # 调用相应的游戏逻辑方法
            if phase == "day":
                self.app.game_logic_handler.start_daytime()
            else:
                self.app.game_logic_handler.next_round()
        elif phase == "night":
            # 应用夜晚主题
            self.apply_theme(self.night_theme)
            # 先播放狼叫声以提供即时反馈
            if hasattr(self.app, 'sound_handler') and self.app.sound_enabled:
                self.app.sound_handler.play_wolf_howl()
            # 调用夜晚逻辑
            self.app.game_logic_handler.start_night()

    def create_player_frames(self):
        """创建所有玩家的 UI 元素"""
        for i in range(1, self.app.state.player_count + 1):
            self.create_player_frame(i)

    def create_player_frame(self, i):
        """创建一个玩家的 UI 框架"""
        # 主玩家框架
        p_frame = ttk.Frame(self.players_frame)
        p_frame.pack(fill=tk.X, pady=5)  # 减小玩家框架之间的间距
        
        # 布局结构
        # 左侧头像 - 调整为更大的正方形
        avatar_size = 100  # 头像正方形大小
        avatar_frame = ttk.Frame(p_frame, width=avatar_size, height=avatar_size)
        avatar_frame.grid(row=0, column=0, rowspan=2, padx=5)  # 占据左侧两行位置
        avatar_frame.grid_propagate(False)  # 防止子控件改变Frame大小
        
        # 加载初始头像
        current_identity = self.app.state.players[i].identity
        photo = self.load_avatar(current_identity)
        
        # 创建头像标签
        avatar_label = tk.Label(avatar_frame, image=photo, bg="#f0f0f0")
        avatar_label.place(relwidth=1, relheight=1)  # 填充整个avatar_frame
        
        # 保存头像引用
        self.player_avatars[i] = {"label": avatar_label, "photo": photo}
        
        # 第一行 - 玩家信息、按钮
        # 玩家标签
        player_label = tk.Label(p_frame, text=f"玩家 {i}", fg=self.app.player_colors.get(i, "black"),
                 font=("SourceHanSansCN-Bold.otf", 16, "bold"))
        player_label.grid(row=0, column=1, padx=5, pady=(5, 2), sticky="w")  # 调整上下内边距
        
        # 按钮框架
        button_frame = ttk.Frame(p_frame)
        button_frame.grid(row=0, column=2, pady=(5, 2), sticky="w")  # 调整上下内边距
        
        # 发言按钮
        speak_btn = ttk.Button(button_frame, text="发言", command=lambda pid=i: self.app.speech_handler.player_speak(pid))
        speak_btn.pack(side=tk.LEFT, padx=5)
        self.app.speak_buttons[i] = speak_btn
        
        # 投票按钮
        vote_btn = ttk.Button(button_frame, text="投票", command=lambda pid=i: self.app.vote_handler.player_vote(pid))
        vote_btn.pack(side=tk.LEFT, padx=5)
        self.app.vote_buttons[i] = vote_btn
        
        # 遗言按钮
        lw_btn = ttk.Button(button_frame, text="遗言", command=lambda pid=i: self.app.speech_handler.player_speak(pid))
        lw_btn.pack(side=tk.LEFT, padx=5)
        lw_btn.config(state=tk.DISABLED)
        self.app.lastword_buttons[i] = lw_btn
        
        # 第二行 - 身份和模型选择
        dropdown_frame = ttk.Frame(p_frame)
        dropdown_frame.grid(row=1, column=1, columnspan=2, pady=(2, 5), sticky="w")  # 调整上下内边距
        
        # 身份下拉菜单
        identity_var = tk.StringVar(value=self.app.state.players[i].identity)
        identity_dropdown = ttk.Combobox(dropdown_frame, textvariable=identity_var, values=["平民", "狼人", "预言家", "猎人", "女巫", "空"],
                                         state="readonly", width=8)
        identity_dropdown.pack(side=tk.LEFT, padx=5)
        
        # 修改身份选择事件，使其同时更新头像
        def on_identity_change(event, pid=i, var=identity_var):
            new_identity = var.get()
            # 更新游戏状态中的身份
            self.app.game_logic_handler.update_player_identity(pid, new_identity)
            # 更新头像
            self.update_player_avatar(pid, new_identity)
            
        identity_dropdown.bind("<<ComboboxSelected>>", on_identity_change)
        self.app.identity_dropdowns[i] = identity_dropdown
        
        # 模型下拉菜单
        model_var = tk.StringVar(value=self.app.state.players[i].model)
        model_dropdown = ttk.Combobox(dropdown_frame, textvariable=model_var,
                                      values=["gemini","deepseek","glm4","sparkmax","cohere","mistral","qwq","hunyuan"],
                                      state="readonly", width=10)
        model_dropdown.pack(side=tk.LEFT, padx=5)
        model_dropdown.bind("<<ComboboxSelected>>", lambda e, pid=i, var=model_var: self.app.game_logic_handler.update_player_model(pid, var.get()))
        self.app.model_dropdowns[i] = model_dropdown

    def update_player_frames_config(self):
        """当玩家数量变化后，更新玩家框架"""
        for widget in self.players_frame.winfo_children():
            widget.destroy()
        self.app.speak_buttons.clear()
        self.app.vote_buttons.clear()
        self.app.lastword_buttons.clear()
        self.app.identity_dropdowns.clear()
        self.app.model_dropdowns.clear()
        self.player_avatars.clear()  # 清空头像引用
        self.create_player_frames()

    def open_manual_vote_popup(self, player_id):
        """打开手动投票弹窗"""
        popup = ttk.Toplevel(self.root)
        popup.title(f"玩家 {player_id} 手动投票")
        ttk.Label(popup, text=f"请手动选择玩家 {player_id} 的投票对象：").pack(padx=10, pady=10)
        selected_player_var = tk.StringVar()
        ttk.Radiobutton(popup, text="随机投票", variable=selected_player_var, value="random").pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(popup, text="弃票", variable=selected_player_var, value="abstain").pack(anchor=tk.W, padx=20)
        for p_id in range(1, self.app.state.player_count + 1):
            if self.app.state.players[p_id].exists and self.app.state.players[p_id].alive and p_id != player_id:
                ttk.Radiobutton(popup, text=f"玩家 {p_id}", variable=selected_player_var, value=str(p_id)).pack(anchor=tk.W, padx=20)
        def confirm_vote():
            vote_target = selected_player_var.get()
            if vote_target:
                popup.destroy()
                if vote_target in ["random", "abstain"]:
                    self.app.log_system(f"玩家 {player_id} 手动选择 {vote_target}")
                    return vote_target
                else:
                    self.app.log_system(f"玩家 {player_id} 手动投票给玩家 {vote_target}")
                    return int(vote_target)
            else:
                tk.messagebox.showerror("错误", "请选择投票对象！")
        confirm_btn = ttk.Button(popup, text="确认投票", command=confirm_vote)
        confirm_btn.pack(pady=10)
        popup.grab_set()
        self.root.wait_window(popup)
        return selected_player_var.get()

    def open_correct_vote_popup(self):
        """打开纠正上次投票弹窗"""
        popup = ttk.Toplevel(self.root)
        popup.title("纠正上次投票")
        ttk.Label(popup, text="请选择要修改的投票及新的投票对象：").pack(padx=10, pady=10)
        vote_player_var = tk.StringVar()
        vote_target_var = tk.StringVar()
        player_selector_frame = ttk.Frame(popup)
        player_selector_frame.pack(pady=5)
        ttk.Label(player_selector_frame, text="选择玩家:").pack(side=tk.LEFT, padx=5)
        player_dropdown = ttk.Combobox(player_selector_frame, textvariable=vote_player_var,
                                          values=[str(p_id) for p_id in range(1, self.app.state.player_count + 1) if self.app.state.players[p_id].exists and self.app.state.players[p_id].alive],
                                          state="readonly", width=5)
        player_dropdown.pack(side=tk.LEFT)
        target_selector_frame = ttk.Frame(popup)
        target_selector_frame.pack(pady=5)
        ttk.Label(target_selector_frame, text="新的投票:").pack(side=tk.LEFT, padx=5)
        target_dropdown_values = ["随机投票", "弃票"] + [str(p_id) for p_id in range(1, self.app.state.player_count + 1) if self.app.state.players[p_id].exists and self.app.state.players[p_id].alive]
        target_dropdown = ttk.Combobox(target_selector_frame, textvariable=vote_target_var,
                                          values=target_dropdown_values,
                                          state="readonly", width=10)
        target_dropdown.pack(side=tk.LEFT)
        def confirm_correct_vote():
            player_to_correct = vote_player_var.get()
            new_vote_target_str = vote_target_var.get()
            if not player_to_correct:
                tk.messagebox.showerror("错误", "请选择要修改投票的玩家！")
                return
            if not new_vote_target_str:
                 tk.messagebox.showerror("错误", "请选择新的投票目标！")
                 return
            popup.destroy()
            new_vote_target = None
            if new_vote_target_str == "随机投票":
                new_vote_target = "random"
            elif new_vote_target_str == "弃票":
                new_vote_target = "abstain"
            else:
                try:
                    new_vote_target = int(new_vote_target_str)
                except ValueError:
                    tk.messagebox.showerror("错误", "无效的玩家编号！")
                    return
            player_id_int = int(player_to_correct)
            if self.app.state.phase == "day":
                self.app.state.day_votes[player_id_int] = new_vote_target
                record_type = "白天投票"
            else:
                self.app.state.night_votes[player_id_int] = new_vote_target
                record_type = "夜晚投票"
            vote_target_display = new_vote_target if isinstance(new_vote_target, str) else f"玩家 {new_vote_target}"
            self.app.log_system(f"[主持人操作]  {record_type} -  玩家 {player_id_int} 的投票被修改为:  {vote_target_display}")
        confirm_btn = ttk.Button(popup, text="确认修改投票", command=confirm_correct_vote)
        confirm_btn.pack(pady=10)
        popup.grab_set()
        self.root.wait_window(popup)

    def load_avatar(self, identity, size=(100, 100)):
        """根据身份加载对应的头像图片"""
        try:
            # 获取对应身份的头像路径
            avatar_path = self.avatar_mapping.get(identity)
            if not avatar_path:
                avatar_path = self.avatar_mapping.get("空")  # 使用默认头像
                
            # 加载并调整大小
            img = Image.open(avatar_path)
            img = img.resize(size, Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            return photo
        except Exception as e:
            print(f"加载头像失败: {e}")
            return None

    def update_player_avatar(self, player_id, identity):
        """更新玩家头像"""
        if player_id in self.player_avatars:
            # 获取保存的头像标签引用
            avatar_label = self.player_avatars[player_id]["label"]
            
            # 加载新头像
            photo = self.load_avatar(identity)
            if photo:
                # 更新头像显示
                avatar_label.configure(image=photo)
                avatar_label.image = photo  # 保留引用，防止被垃圾回收
                self.player_avatars[player_id]["photo"] = photo
