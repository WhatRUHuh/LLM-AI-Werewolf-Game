#GameLogicHandler.py
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from record import create_day_record_folder
# from readrecord import get_history_summary  # 已删除，get_history_summary 已搬至此处

class GameLogicHandler:
    def __init__(self, app):
        self.app = app

    def apply_config(self):
        player_count = self.app.player_count_var.get()
        wolf_count = self.app.wolf_count_var.get()
        seer_count = self.app.seer_count_var.get()
        hunter_count = self.app.hunter_count_var.get()
        witch_count = self.app.witch_count_var.get()
        if wolf_count >= player_count:
            messagebox.showerror("配置错误", "狼人数量必须小于玩家数量！")
            return
        self.app.state = self.app.create_game_state(player_count, wolf_count, seer_count, hunter_count, witch_count)
        self.app.day_label.config(text=f"第 {self.app.state.day} 天")
        self.app.ui_handler.update_player_frames_config()
        self.app.log_system("已应用新配置，重新初始化游戏。")
        self.update_buttons_for_phase("day")

    def restart_game(self):
        self.app.state = self.app.create_game_state(
            player_count=self.app.player_count_var.get(),
            wolf_count=self.app.wolf_count_var.get(),
            seer_count=self.app.seer_count_var.get(),
            hunter_count=self.app.hunter_count_var.get(),
            witch_count=self.app.witch_count_var.get()
        )
        self.app.day_label.config(text=f"第 {self.app.state.day} 天")
        self.apply_config()
        self.app.log_system("游戏已重新开始。")

    def update_player_identity(self, player_id, new_identity):
        player = self.app.state.players[player_id]
        player.identity = new_identity
        if new_identity == "空":
            player.exists = False
            player.alive = False
        else:
            player.exists = True
        self.app.log_system(f"设置 玩家 {player_id} 的身份为 {new_identity}")

    def update_player_model(self, player_id, new_model):
        player = self.app.state.players[player_id]
        player.model = new_model
        self.app.log_system(f"设置 玩家 {player_id} 的模型为 {new_model}")

    def update_buttons_for_phase(self, phase):
        self.app.state.phase = phase
        for i, p in self.app.state.players.items():
            if not p.exists:
                self.app.speak_buttons[i].config(state=tk.DISABLED)
                self.app.vote_buttons[i].config(state=tk.DISABLED)
                self.app.lastword_buttons[i].config(state=tk.DISABLED)
            elif not p.alive:
                # 如果玩家死亡但存在，禁用发言和投票按钮，启用遗言按钮
                self.app.speak_buttons[i].config(state=tk.DISABLED)
                
                # 特殊情况：夜晚阶段的女巫，如果救人药还在，即使死亡也可以投票（自救）
                if phase == "night" and p.identity == "女巫":
                    # 检查救人药是否已使用
                    save_used = self.app.state.witch_save_used.get(i, False)
                    if not save_used:
                        self.app.vote_buttons[i].config(state=tk.NORMAL)
                    else:
                        self.app.vote_buttons[i].config(state=tk.DISABLED)
                else:
                    self.app.vote_buttons[i].config(state=tk.DISABLED)
                
                # 无论当前是什么阶段，死亡玩家的遗言按钮都保持启用
                self.app.lastword_buttons[i].config(state=tk.NORMAL)
            else:
                # 根据阶段设置按钮状态
                if phase == "day":
                    self.app.speak_buttons[i].config(state=tk.NORMAL)
                    self.app.vote_buttons[i].config(state=tk.NORMAL)
                    self.app.lastword_buttons[i].config(state=tk.DISABLED)
                else: # 夜晚阶段
                    # 狼人、预言家和女巫在夜晚可以投票
                    if p.identity == "狼人" or p.identity == "预言家" or p.identity == "女巫":
                        # 女巫没有夜晚发言
                        if p.identity == "女巫":
                            self.app.speak_buttons[i].config(state=tk.DISABLED)
                        else:
                            self.app.speak_buttons[i].config(state=tk.NORMAL)
                        
                        # 女巫特殊处理：如果两种药都用完了，夜晚不再有投票权
                        if p.identity == "女巫":
                            # 检查该女巫的药水状态
                            save_used = self.app.state.witch_save_used.get(i, False)
                            poison_used = self.app.state.witch_poison_used.get(i, False)
                            
                            if save_used and poison_used:  # 两种药都用完了
                                self.app.vote_buttons[i].config(state=tk.DISABLED)
                            else:  # 还有药可以用
                                self.app.vote_buttons[i].config(state=tk.NORMAL)
                        else:
                            self.app.vote_buttons[i].config(state=tk.NORMAL)
                            
                        self.app.lastword_buttons[i].config(state=tk.DISABLED)
                    else: #  其他身份 (包括 平民, 空, 猎人)  夜晚按钮保持禁用
                        self.app.speak_buttons[i].config(state=tk.DISABLED)
                        self.app.vote_buttons[i].config(state=tk.DISABLED)
                        self.app.lastword_buttons[i].config(state=tk.DISABLED)

    def end_game(self, winner):
        self.app.log_system(f"游戏结束，{winner}获胜！")
        messagebox.showinfo("游戏结束", f"游戏结束，{winner}获胜！")
        self.app.daytime_btn.config(state=tk.DISABLED)
        self.app.day_voting_btn.config(state=tk.DISABLED)
        self.app.night_btn.config(state=tk.DISABLED)
        self.app.night_voting_btn.config(state=tk.DISABLED)
        self.app.next_round_btn.config(state=tk.DISABLED)
        for i in self.app.speak_buttons:
            self.app.speak_buttons[i].config(state=tk.DISABLED)
        for i in self.app.vote_buttons:
            self.app.vote_buttons[i].config(state=tk.DISABLED)
        for i in self.app.lastword_buttons:
            self.app.lastword_buttons[i].config(state=tk.DISABLED)

    def start_daytime(self):
        if self.app.state.day != 1:
            self.next_round_init()
        self.app.log_system("【白天回合开始】")
        self.app.print_day_status()
        self.update_buttons_for_phase("day")

    def finalize_day_voting(self):
        vote_counts = {}
        valid_votes = {}
        for voter_id, vote_target in self.app.state.day_votes.items():
            if vote_target in self.app.state.players and self.app.state.players[vote_target].exists:
                valid_votes[voter_id] = vote_target
                vote_counts[vote_target] = vote_counts.get(vote_target, 0) + 1
        self.app.log_system(f"【白天投票结算】有效投票统计: {vote_counts}")
        if not vote_counts:
            self.app.log_system("白天平安夜：无人投票淘汰。")
        else:
            max_votes = max(vote_counts.values())
            candidates = [pid for pid, count in vote_counts.items() if count == max_votes]
            if len(candidates) > 1:
                self.app.log_system("白天平安夜：票数相同，无人淘汰。")
            else:
                eliminated = candidates[0]
                if eliminated in self.app.state.players and self.app.state.players[eliminated].alive:
                    self.app.state.players[eliminated].alive = False
                    self.app.state.dead_today.append(eliminated)
                    self.app.state.current_day_summary["deaths"].append((eliminated, "被投票投出死亡"))
                    self.app.log_system(f"玩家 {eliminated} 被白天投票淘汰！")
                else:
                    self.app.log_system("投票结果错误：指定玩家不存在或已死亡。")
        game_over, winner = self.app.state.check_game_over()
        if game_over:
            self.end_game(winner)
        # 在结算后刷新按钮状态
        self.update_buttons_for_phase(self.app.state.phase)

    def start_night(self):
        self.app.log_system("【夜晚回合开始】")
        self.update_buttons_for_phase("night")

    def finalize_night_voting(self):
        # 先处理狼人的投票
        wolf_vote_counts = {}
        wolf_target = None
        
        # 找出所有狼人
        wolves = [player_id for player_id, player in self.app.state.players.items() 
                 if player.exists and player.alive and player.identity == "狼人"]
        
        # 统计狼人投票
        for voter_id in wolves:
            if voter_id in self.app.state.night_votes:
                vote_target = self.app.state.night_votes[voter_id]
                if vote_target in self.app.state.players and self.app.state.players[vote_target].exists and self.app.state.players[vote_target].alive:
                    wolf_vote_counts[vote_target] = wolf_vote_counts.get(vote_target, 0) + 1
        
        self.app.log_system(f"【夜晚投票结算】狼人有效投票统计: {wolf_vote_counts}")
        
        # 确定狼人击杀目标
        if wolf_vote_counts:
            max_votes = max(wolf_vote_counts.values())
            candidates = [pid for pid, count in wolf_vote_counts.items() if count == max_votes]
            if len(candidates) == 1:
                wolf_target = candidates[0]
                self.app.state.wolf_kill_target = wolf_target  # 记录狼人击杀目标，供女巫救人使用
                self.app.log_system(f"狼人决定击杀玩家 {wolf_target}")
            else:
                self.app.log_system("狼人意见不统一，无法确定击杀目标")
        else:
            self.app.log_system("狼人没有选择击杀目标")
        
        # 女巫的药水效果已经在VoteHandler.py中即时处理
        # 这里只记录女巫行动
        witches = [player_id for player_id, player in self.app.state.players.items() 
                  if player.exists and player.alive and player.identity == "女巫"]
        
        witch_acted = []
        for witch_id in witches:
            if witch_id in self.app.state.night_votes:
                witch_vote = self.app.state.night_votes[witch_id]
                if witch_vote not in ["弃票", "不使用药水", "随机"]: # 这些都视为有效的"不使用药水"选项
                    witch_acted.append(witch_id)
                
        if witch_acted:
            self.app.log_system(f"今晚行动的女巫: {witch_acted}")
        
        # 执行狼人击杀（如果没有被女巫救活）
        if wolf_target and wolf_target != self.app.state.witch_save_target:
            if wolf_target in self.app.state.players and self.app.state.players[wolf_target].alive:
                self.app.state.players[wolf_target].alive = False
                self.app.state.dead_today.append(wolf_target)
                self.app.state.current_day_summary["deaths"].append((wolf_target, "夜晚死亡"))
                self.app.log_system(f"玩家 {wolf_target} 被狼人击杀！")
                
                # 启用遗言按钮
                self.app.lastword_buttons[wolf_target].config(state=tk.NORMAL)
        elif wolf_target == self.app.state.witch_save_target:
            self.app.log_system(f"玩家 {wolf_target} 被女巫救活了！")
        
        # 夜晚投票结算的总结
        if not self.app.state.dead_today:
            self.app.log_system("夜晚平安夜：无人死亡。")
        
        # 检查游戏是否结束
        game_over, winner = self.app.state.check_game_over()
        if game_over:
            self.end_game(winner)
        
        # 在结算后刷新按钮状态
        self.update_buttons_for_phase(self.app.state.phase)

    def next_round_init(self):
        """下一回合的初始化逻辑 (提取公共部分)"""
        self.app.state.reset_day()
        create_day_record_folder(self.app.state.day)
        self.app.day_label.config(text=f"第 {self.app.state.day} 天")

    def next_round(self):
        self.app.log_system("【进入下一回合】")
        self.next_round_init()
        self.app.print_day_status()
        self.update_buttons_for_phase("day")

    def get_history_summary(self):
        state = self.app.state
        lines = []
        for day_info in state.history:
            day = day_info.get("day", "?")
            deaths = day_info.get("deaths", [])
            if deaths:
                death_str = ", ".join([f"玩家{pid}({cause})" for pid, cause in deaths])
                line = f"第{day}天: 死亡: {death_str}"
            else:
                line = f"第{day}天: 无死亡"
            lines.append(line)
        return "\n".join(lines)

    def print_day_status(self):
        alive = [p.player_id for p in self.app.state.players.values() if p.exists and p.alive]
        status_text = f"【第 {self.app.state.day} 天 状态】\n存活玩家：{alive}\n"
        if self.app.state.history:
            status_text += "历史死亡信息：\n" + self.get_history_summary() + "\n"
        self.app.log_system(status_text)

    def correct_last_vote(self):
        last_voter_id = self.app.last_voter_id
        if not last_voter_id:
            self.app.log_system("[错误] 无法纠正投票： 未知最后投票玩家。")
            messagebox.showerror("错误", "无法纠正投票： 未知最后投票玩家。")
            return
        manual_vote_result = self.open_manual_vote_popup(last_voter_id)
        if manual_vote_result:
            if self.app.state.phase == "day":
                self.app.state.day_votes[last_voter_id] = manual_vote_result
                log_type = "白天"
            else:
                self.app.state.night_votes[last_voter_id] = manual_vote_result
                log_type = "夜晚"
            self.app.log_system(f"[主持人手动纠正] 玩家 {last_voter_id} 的 {log_type}投票 被修改为: {manual_vote_result}")
            messagebox.showinfo("投票已纠正", f"玩家 {last_voter_id} 的 {log_type}投票 已被手动纠正为: {manual_vote_result}")
        else:
            self.app.log_system(f"[提示] 主持人取消了 玩家 {last_voter_id} 的投票纠正操作。")
            messagebox.showinfo("取消纠正", f"玩家 {last_voter_id} 的投票纠正操作已取消。")
        self.app.correct_vote_btn.config(state=tk.DISABLED)

    def open_manual_vote_popup(self, player_id):
        popup = ttk.Toplevel(self.app.root)
        popup.title(f"玩家 {player_id} 投票选择")
        ttk.Label(popup, text=f"无法自动解析玩家 {player_id} 的投票结果，请手动选择投票目标：").pack(padx=10, pady=10)
        vote_result_var = tk.StringVar()
        player_ids = [str(p) for p in range(1, self.app.state.player_count + 1) if self.app.state.players[p].exists and self.app.state.players[p].alive]
        player_Combobox = ttk.Combobox(popup, textvariable=vote_result_var, values=player_ids, state="readonly")
        player_Combobox.pack(padx=10, pady=5)
        player_Combobox.set("请选择玩家")
        def confirm_vote():
            selected_player_id = vote_result_var.get()
            if selected_player_id in player_ids:
                popup.result = selected_player_id
                popup.destroy()
            else:
                messagebox.showerror("错误", "请选择有效的投票玩家！")
        def abstain_vote():
            popup.result = "弃票"
            popup.destroy()
        def random_vote():
            popup.result = "随机"
            popup.destroy()
        def cancel_vote():
            popup.result = None
            popup.destroy()
        confirm_button = ttk.Button(popup, text="投票给选中玩家", command=confirm_vote)
        confirm_button.pack(side=tk.LEFT, padx=10, pady=10)
        abstain_button = ttk.Button(popup, text="弃票", command=abstain_vote)
        abstain_button.pack(side=tk.LEFT, padx=10, pady=10)
        random_button = ttk.Button(popup, text="随机投票", command=random_vote)
        random_button.pack(side=tk.LEFT, padx=10, pady=10)
        cancel_button = ttk.Button(popup, text="取消", command=cancel_vote)
        cancel_button.pack(side=tk.LEFT, padx=10, pady=10)
        popup.result = None
        popup.grab_set()
        self.app.root.wait_window(popup)
        return popup.result
