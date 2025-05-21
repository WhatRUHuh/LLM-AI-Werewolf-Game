import tkinter as tk
from record import save_daytime_vote, save_night_vote, save_sheriff_vote, append_check_record
import re
import random
from readrecord import (get_last_words_content, get_day_vote_reasoning_player, get_night_vote_reasoning_player)
import os
from TTS import play_tts  # 导入 TTS 模块

# Import role-specific vote prompt generation modules
from . import common_vote
from . import werewolf_vote
from . import seer_vote
from . import witch_vote
# Hunter voting is typically a speech action on death, handled in SpeechHandler,
# but we can have a placeholder if direct voting logic for hunter is ever needed.
# from . import hunter_vote 

class VoteHandler:
    def __init__(self, app):
        self.app = app
        self.model_handler = app.model_handler  # 获取 ModelHandler 实例

    def player_vote(self, player_id):
        player = self.app.state.players[player_id]
        
        # Basic validation
        if player.identity == "女巫" and self.app.state.phase == "night":
            pass # Witch can vote (use potions) even if "dead" in some contexts (e.g. self-save)
        elif not (player.exists and player.alive):
            self.app.ui_handler.log_system(f"玩家 {player_id} 不存在或已死亡，无法投票。")
            return

        # Prepare common information for prompts
        history_info_formatted = self._get_history_info_formatted()
        game_state_info = self._get_game_state_info()
        
        extra_info_params = {
            "player_id": player_id,
            "identity": player.identity,
            "game_state_info": game_state_info,
            "teammates": [p.player_id for p in self.app.state.players.values() if p.identity == "狼人" and p.player_id != player_id] if player.identity == "狼人" else []
        }
        extra_info = self._get_extra_info(**extra_info_params)
        
        header = self._get_header(player_id=player_id, extra_info=extra_info, history_info_formatted=history_info_formatted)
        footer = self._get_footer(player_id=player_id, extra_info=extra_info)
        
        last_words_content = get_last_words_content() # General utility

        common_prefix = (
            "投票给已死亡或不存在的玩家将视为空票\n"
            "返回格式应为 [玩家编号]（例如 [1]），或返回 随机 或 弃票 分别代表随机投票或弃票\n"
            "如果白天放逐票和夜晚击杀票数相同，则投票无效\n"
            "【注意】请务必将你的投票控制在300字以内，以免耽误其他玩家的时间。\n"
        )
        common_suffix = (
            "\n【提醒】请保持投票内容简洁明了，限于300字以内。\n"
            "投票给已死亡或不存在的玩家将视为空票\n"
            "返回格式应为 [玩家编号]（例如 [1]），或返回 随机 或 弃票 分别代表随机投票或弃票\n"
            "如果白天放逐票和夜晚击杀票数相同，则投票无效"
        )

        prompt_params = {
            "handler": self,
            "player": player,
            "header": header,
            "footer": footer,
            "common_prefix": common_prefix,
            "common_suffix": common_suffix,
            "last_words_content": last_words_content,
            # Other params like daytime_speeches, history_speeches will be fetched by role modules
        }

        prompt = ""
        # Determine phase and role to call the correct prompt generation function
        if self.app.state.phase == "day":
            self.app.ui_handler.log_system(f"玩家 {player_id} 准备进行白天投票...")
            # Common vote handles daytime voting for all roles, including sheriff election
            prompt = common_vote.generate_daytime_vote_prompt(**prompt_params)
        
        elif self.app.state.phase == "night":
            self.app.ui_handler.log_system(f"{player.identity} 玩家 {player_id} 准备进行夜晚投票/查验...")
            if player.identity == "狼人":
                prompt = werewolf_vote.generate_werewolf_night_vote_prompt(**prompt_params)
            elif player.identity == "预言家":
                prompt = seer_vote.generate_seer_night_check_prompt(**prompt_params)
            elif player.identity == "女巫":
                prompt = witch_vote.generate_witch_night_action_prompt(**prompt_params)
            else:
                # Other roles typically don't vote at night unless specific rules apply
                self.app.ui_handler.log_system(f"玩家 {player_id} ({player.identity}) 在夜晚没有常规投票动作。")
                return # Or generate a generic "do nothing" prompt if necessary
        else:
            self.app.ui_handler.log_system(f"未知投票阶段: {self.app.state.phase} for player {player_id}")
            return
            
        if not prompt:
            self.app.ui_handler.log_system(f"错误：未能为玩家 {player_id} (身份: {player.identity}, 阶段: {self.app.state.phase}) 生成投票提示。")
            return

        def vote_callback(final_answer_text):
            text_parsed = final_answer_text.replace("\\n", "\n")
            vote_result = None

            # Add parsing logic (remains similar to original)
            player_brackets = re.findall(r'\[玩家(\d+)\]', text_parsed)
            brackets_number = re.findall(r'\[(\d+)\]', text_parsed)
            eng_random_choice = re.search(r'\[随机\]', text_parsed)
            eng_abstain_choice = re.search(r'\[弃票\]', text_parsed)
            eng_skip_choice = re.search(r'\[跳过\]|\[不使用\]|\[不用\]', text_parsed)
            chinese_player_brackets = re.findall(r'【玩家(\d+)】', text_parsed)
            chinese_brackets_number = re.findall(r'【(\d+)】', text_parsed)
            cn_random_choice = re.search(r'【随机】', text_parsed)
            cn_abstain_choice = re.search(r'【弃票】', text_parsed)
            cn_skip_choice = re.search(r'【跳过】|【不使用】|【不用】', text_parsed)
            direct_random_choice = re.search(r'(?<!\[|【)随机(?!\]|】)', text_parsed)
            direct_abstain_choice = re.search(r'(?<!\[|【)弃票(?!\]|】)', text_parsed)
            direct_skip_choice = re.search(r'(?<!\[|【)跳过(?!\]|】)|(?<!\[|【)不使用(?!\]|】)|(?<!\[|【)不用(?!\]|】)', text_parsed)
            direct_player_mention = re.findall(r'玩家\s*(\d+)', text_parsed)
            direct_number = re.findall(r'(?<![【\[（\(])\b(\d+)\b(?![\]】）\)])', text_parsed)

            if player_brackets:
                vote_result = player_brackets[-1]
                try: vote_target = int(vote_result)
                except ValueError: self.app.ui_handler.log_system(f"[警告] 无法解析 玩家 {player_id} 的投票目标编号 (英文方括号玩家数字)，投票作废。"); return
            elif brackets_number:
                vote_result = brackets_number[-1]
                try: vote_target = int(vote_result)
                except ValueError: self.app.ui_handler.log_system(f"[警告] 无法解析 玩家 {player_id} 的投票目标编号 (英文方括号数字)，投票作废。"); return
            elif eng_random_choice:
                alive_players = [i for i, p in self.app.state.players.items() if p.exists and p.alive and i != player_id]
                if not alive_players: self.app.ui_handler.log_system(f"[警告] 玩家 {player_id} 选择随机投票，但没有有效的目标！"); return
                vote_target = random.choice(alive_players); vote_result = str(vote_target)
                self.app.ui_handler.log_system(f"玩家 {player_id} 选择了[随机]投票，系统选择了玩家 {vote_target}")
            elif eng_abstain_choice or eng_skip_choice:
                vote_target = "弃票"; vote_result = "弃票"
                self.app.ui_handler.log_system(f"玩家 {player_id} 选择了[弃票]")
                if player.identity == "女巫" and self.app.state.phase == "night":
                    self.app.ui_handler.log_system(f"女巫 {player_id} 选择本回合不使用药水")
                    self.app.state.night_votes[player_id] = "不使用药水"; save_night_vote(player_id, self.app.state.day, text_parsed); return
            elif chinese_player_brackets:
                vote_result = chinese_player_brackets[-1]
                try: vote_target = int(vote_result)
                except ValueError: self.app.ui_handler.log_system(f"[警告] 无法解析 玩家 {player_id} 的投票目标编号 (中文方括号玩家数字)，投票作废。"); return
            elif chinese_brackets_number:
                vote_result = chinese_brackets_number[-1]
                try: vote_target = int(vote_result)
                except ValueError: self.app.ui_handler.log_system(f"[警告] 无法解析 玩家 {player_id} 的投票目标编号 (中文方括号数字)，投票作废。"); return
            elif cn_random_choice:
                alive_players = [i for i, p in self.app.state.players.items() if p.exists and p.alive and i != player_id]
                if not alive_players: self.app.ui_handler.log_system(f"[警告] 玩家 {player_id} 选择随机投票，但没有有效的目标！"); return
                vote_target = random.choice(alive_players); vote_result = str(vote_target)
                self.app.ui_handler.log_system(f"玩家 {player_id} 选择了【随机】投票，系统选择了玩家 {vote_target}")
            elif cn_abstain_choice or cn_skip_choice:
                vote_target = "弃票"; vote_result = "弃票"
                self.app.ui_handler.log_system(f"玩家 {player_id} 选择了【弃票】")
                if player.identity == "女巫" and self.app.state.phase == "night":
                    self.app.ui_handler.log_system(f"女巫 {player_id} 选择本回合不使用药水")
                    self.app.state.night_votes[player_id] = "不使用药水"; save_night_vote(player_id, self.app.state.day, text_parsed); return
            elif direct_random_choice:
                alive_players = [i for i, p in self.app.state.players.items() if p.exists and p.alive and i != player_id]
                if not alive_players: self.app.ui_handler.log_system(f"[警告] 玩家 {player_id} 选择随机投票，但没有有效的目标！"); return
                vote_target = random.choice(alive_players); vote_result = str(vote_target)
                self.app.ui_handler.log_system(f"玩家 {player_id} 直接选择了随机投票，系统选择了玩家 {vote_target}")
            elif direct_abstain_choice or direct_skip_choice:
                vote_target = "弃票"; vote_result = "弃票"
                self.app.ui_handler.log_system(f"玩家 {player_id} 直接选择了弃票")
                if player.identity == "女巫" and self.app.state.phase == "night":
                    self.app.ui_handler.log_system(f"女巫 {player_id} 选择本回合不使用药水")
                    self.app.state.night_votes[player_id] = "不使用药水"; save_night_vote(player_id, self.app.state.day, text_parsed); return
            elif direct_player_mention:
                vote_result = direct_player_mention[-1]
                try: vote_target = int(vote_result); self.app.ui_handler.log_system(f"玩家 {player_id} 选择了不带括号的目标：玩家 {vote_target}")
                except ValueError: self.app.ui_handler.log_system(f"[警告] 无法解析 玩家 {player_id} 的直接玩家提及，投票作废。"); return
            elif direct_number:
                vote_result = direct_number[-1]
                try: vote_target = int(vote_result); self.app.ui_handler.log_system(f"玩家 {player_id} 选择了不带括号的目标：{vote_target}")
                except ValueError: self.app.ui_handler.log_system(f"[警告] 无法解析 玩家 {player_id} 的直接数字提及，投票作废。"); return
            else:
                self.app.ui_handler.log_system(f"[警告] 无法解析 玩家 {player_id} 的投票目标，投票作废。"); return

            # Process vote (remains similar, but simplified due to prior parsing)
            if self.app.state.phase == "day":
                self.app.state.day_votes[player_id] = vote_target
                save_daytime_vote(player_id, self.app.state.day, text_parsed)
            elif self.app.state.phase == "night":
                if player.identity == "狼人":
                    self.app.state.night_votes[player_id] = vote_target
                    save_night_vote(player_id, self.app.state.day, text_parsed)
                elif player.identity == "预言家":
                    # Seer check logic (remains similar)
                    check_target_id_str = vote_result # vote_result is already parsed to a string number or "弃票"/"随机"
                    if check_target_id_str in ["随机", "弃票", None] or not check_target_id_str.isdigit():
                        self.app.ui_handler.log_system(f"[警告] 预言家 {player_id} 查验目标无效: {check_target_id_str}， 本回合查验作废。")
                        self.app.ui_handler.log_system(f"[系统提示] 预言家当晚查验结果为：**无效**"); return
                    check_target_id = int(check_target_id_str)
                    if check_target_id not in self.app.state.players or not self.app.state.players[check_target_id].exists:
                        self.app.ui_handler.log_system(f"[警告] 预言家 {player_id} 查验目标不存在: 玩家 {check_target_id}， 查验作废。")
                        self.app.ui_handler.log_system(f"[系统提示] 预言家当晚查验结果为：**无效**"); return
                    checked_player = self.app.state.players[check_target_id]
                    checked_player_identity = checked_player.identity
                    append_check_record(self.app.state.day, player_id, check_target_id, checked_player_identity)
                    self.app.ui_handler.log_system(f"[查验结果] 预言家 玩家 {player_id} 查验 玩家 {check_target_id}， 身份：{checked_player_identity}")
                    self.app.ui_handler.log_system(f"[系统提示] 预言家当晚查验 玩家 {check_target_id}， 身份：**{checked_player_identity}**")
                elif player.identity == "女巫":
                    # Witch action logic (remains similar)
                    save_used = self.app.state.witch_save_used.get(player_id, False)
                    poison_used = self.app.state.witch_poison_used.get(player_id, False)
                    if vote_target in self.app.state.players and self.app.state.players[vote_target].exists:
                        wolf_target = self.app.state.wolf_kill_target
                        if (vote_target == wolf_target or (wolf_target == player_id and vote_target == player_id)) and not save_used:
                            self.app.state.witch_save_used[player_id] = True
                            log_msg = f"女巫 {player_id} 使用了救人药救了自己" if vote_target == player_id else f"女巫 {player_id} 使用了救人药救活了玩家 {vote_target}"
                            self.app.ui_handler.log_system(log_msg)
                            self.app.state.night_votes[player_id] = vote_target
                            self.app.state.witch_save_target = vote_target
                            if not self.app.state.players[vote_target].alive:
                                self.app.state.players[vote_target].alive = True
                                if vote_target in self.app.state.dead_today: self.app.state.dead_today.remove(vote_target)
                                self.app.state.current_day_summary["deaths"] = [(pid, cause) for pid, cause in self.app.state.current_day_summary["deaths"] if pid != vote_target]
                        elif self.app.state.players[vote_target].alive and not poison_used:
                            self.app.state.witch_poison_used[player_id] = True
                            self.app.ui_handler.log_system(f"女巫 {player_id} 使用了毒药毒死了玩家 {vote_target}")
                            self.app.state.night_votes[player_id] = vote_target
                            self.app.state.players[vote_target].alive = False
                            self.app.state.dead_today.append(vote_target)
                            self.app.state.current_day_summary["deaths"].append((vote_target, "夜晚死亡"))
                            self.app.lastword_buttons[vote_target].config(state=tk.NORMAL)
                            game_over, winner = self.app.state.check_game_over()
                            if game_over: self.app.game_logic_handler.end_game(winner)
                        elif save_used and (vote_target == wolf_target or (wolf_target == player_id and vote_target == player_id)):
                             self.app.ui_handler.log_system(f"[警告] 女巫 {player_id} 尝试救活玩家 {vote_target}，但救人药已使用过")
                        elif poison_used and self.app.state.players[vote_target].alive :
                             self.app.ui_handler.log_system(f"[警告] 女巫 {player_id} 尝试使用毒药，但毒药已使用过")
                        elif not self.app.state.players[vote_target].alive and vote_target != wolf_target :
                             self.app.ui_handler.log_system(f"[警告] 女巫 {player_id} 尝试对已死亡的玩家 {vote_target} 使用药水（非狼人目标）。")
                        else: # No valid action or target
                             self.app.ui_handler.log_system(f"女巫 {player_id} 本回合未使用药水或目标无效。")
                             self.app.state.night_votes[player_id] = "不使用药水" # Explicitly record no action
                    else: # vote_target is not a valid player (e.g. "弃票")
                        self.app.ui_handler.log_system(f"女巫 {player_id} 选择不使用药水。")
                        self.app.state.night_votes[player_id] = "不使用药水"
                    save_night_vote(player_id, self.app.state.day, text_parsed) # Save raw text for witch
                else: # Other roles (if any) that vote at night
                    self.app.state.night_votes[player_id] = vote_target
                    save_night_vote(player_id, self.app.state.day, text_parsed)
                    self.app.ui_handler.log_system(f"{player.identity} 玩家 {player_id} 夜晚投票选择了 玩家 {vote_target}")

            if self.app.tts_enabled:
                play_tts(text_parsed, player_id, self.app.tts_speed)

        self.model_handler.call_model(player.model, prompt, self.app.summary_text, tag=f"p{player_id}",
                                      callback=vote_callback, player_id=player_id)
    
    # Helper methods to construct parts of the prompt (can be called by role-specific modules via handler)
    def _get_history_info_formatted(self):
        history_info_formatted = "**【历史死亡信息】**\n"
        if self.app.state.history:
            for day_info in self.app.state.history:
                day = day_info.get("day", "?")
                deaths = day_info.get("deaths", [])
                if deaths:
                    death_str = ", ".join([f"玩家{pid}({cause})" for pid, cause in deaths])
                    history_info_formatted += f"**第{day}天**: 死亡: {death_str}\n"
                else:
                    history_info_formatted += f"**第{day}天**: 无死亡\n"
        current_day = self.app.state.day
        current_deaths = self.app.state.current_day_summary.get("deaths", [])
        if current_deaths:
            death_str = ", ".join([f"玩家{pid}({cause})" for pid, cause in current_deaths])
            history_info_formatted += f"**第{current_day}天(当天)**: 死亡: {death_str}\n"
        if not self.app.state.history and not current_deaths:
             history_info_formatted += "暂无死亡记录\n"
        return f"**【开始】【历史死亡信息】**\n{history_info_formatted}**【结束】【历史死亡信息】**\n"

    def _get_game_state_info(self):
        return (f"**【开始】【游戏状态】**\n"
                f"**初始狼人数量**: {self.app.state.initial_wolf_count}\n"
                f"**总玩家数量**: {self.app.state.player_count}\n"
                f"**当前天数**: {self.app.state.day}\n"
                f"**初始预言家数量**: {self.app.state.initial_seer_count}\n"
                f"**初始猎人数量**: {self.app.state.initial_hunter_count}\n"
                f"**初始女巫数量**: {self.app.state.initial_witch_count}\n"
                f"**存活玩家**: {[p.player_id for p in self.app.state.players.values() if p.exists and p.alive]}\n"
                f"**【结束】【游戏状态】**\n")

    def _get_extra_info(self, player_id, identity, game_state_info, teammates=None):
        if teammates is None: teammates = []
        extra_info = ((f"**【提示】你是谁：玩家 {player_id}，身份：{identity}。请牢记这一点！**\n") * 2 + (game_state_info) * 2)
        if identity == "狼人" and teammates:
            extra_info += ((f"**【队友信息】: 狼人队友：{teammates}**\n") * 2)
        return extra_info

    def _get_header(self, player_id, extra_info, history_info_formatted):
        return f"**【开始】【玩家{player_id}】**\n" + extra_info + history_info_formatted
        
    def _get_footer(self, player_id, extra_info):
        return extra_info + f"\n**【结束】【玩家{player_id}】**"

    def _read_day_speeches(self):
        """读取当前天数的所有白天玩家发言"""
        day_speeches = ""
        record_root = "record"
        day_folder = os.path.join(record_root, f"第{self.app.state.day}天", "白天玩家发言")
        if os.path.exists(day_folder):
            import re
            for filename in sorted(os.listdir(day_folder)):
                if filename.startswith("玩家") and filename.endswith("白天发言.txt"):
                    match = re.search(r'玩家(\d+)白天发言\.txt', filename)
                    if match:
                        p_id = int(match.group(1))
                        if self.app.state.players[p_id].alive and self.app.state.players[p_id].exists:
                            file_path = os.path.join(day_folder, filename)
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read().strip()
                                    if content:
                                        day_speeches += f"**玩家{p_id}**: {content}\n\n"
                            except Exception as e:
                                print(f"[警告] 读取玩家 {p_id} 白天发言失败: {e}")
        return day_speeches

    def _read_history_day_speeches(self):
        """读取历史天数的所有白天玩家发言"""
        history_speeches = ""
        record_root = "record"
        current_day = self.app.state.day

        # 从第0天到当前天数-1，读取所有历史发言
        for day in range(0, current_day):
            day_folder = os.path.join(record_root, f"第{day}天", "白天玩家发言")
            if os.path.exists(day_folder):
                import re
                day_speeches = ""
                for filename in sorted(os.listdir(day_folder)):
                    if filename.startswith("玩家") and filename.endswith("白天发言.txt"):
                        match = re.search(r'玩家(\d+)白天发言\.txt', filename)
                        if match:
                            p_id = int(match.group(1))
                            file_path = os.path.join(day_folder, filename)
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read().strip()
                                    if content:
                                        day_speeches += f"**玩家{p_id}**: {content}\n\n"
                            except Exception as e:
                                print(f"[警告] 读取玩家 {p_id} 历史白天发言失败: {e}")
                if day_speeches:
                    history_speeches += f"**第{day}天白天发言:**\n{day_speeches}\n"

        return history_speeches

    def _read_history_day_votes(self):
        """读取历史天数的所有白天玩家投票"""
        history_votes = ""
        record_root = "record"
        current_day = self.app.state.day

        # 从第0天到当前天数-1，读取所有历史投票
        for day in range(0, current_day):
            day_folder = os.path.join(record_root, f"第{day}天", "白天玩家投票")
            if os.path.exists(day_folder):
                import re
                day_votes = ""
                for filename in sorted(os.listdir(day_folder)):
                    if filename.startswith("玩家") and filename.endswith("白天投票.txt"):
                        match = re.search(r'玩家(\d+)白天投票\.txt', filename)
                        if match:
                            p_id = int(match.group(1))
                            file_path = os.path.join(day_folder, filename)
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read().strip()
                                    if content:
                                        day_votes += f"**玩家{p_id}投票**: {content}\n\n"
                            except Exception as e:
                                print(f"[警告] 读取玩家 {p_id} 历史白天投票失败: {e}")
                if day_votes:
                    history_votes += f"**第{day}天白天投票:**\n{day_votes}\n"

        return history_votes

    def _read_history_night_speeches(self):
        """读取历史天数的狼人夜晚发言（仅适用于狼人玩家）"""
        history_speeches = ""
        record_root = "record"
        current_day = self.app.state.day

        # 从第0天到当前天数-1，读取所有历史发言
        for day in range(0, current_day):
            day_folder = os.path.join(record_root, f"第{day}天", "夜晚玩家发言")
            if os.path.exists(day_folder):
                import re
                day_speeches = ""
                for filename in sorted(os.listdir(day_folder)):
                    if filename.startswith("玩家") and filename.endswith("夜晚发言.txt"):
                        match = re.search(r'玩家(\d+)夜晚发言\.txt', filename)
                        if match:
                            p_id = int(match.group(1))
                            if self.app.state.players[p_id].identity == "狼人":  # 仅读取狼人发言
                                file_path = os.path.join(day_folder, filename)
                                try:
                                    with open(file_path, "r", encoding="utf-8") as f:
                                        content = f.read().strip()
                                        if content:
                                            day_speeches += f"**狼人玩家{p_id}**: {content}\n\n"
                                except Exception as e:
                                    print(f"[警告] 读取玩家 {p_id} 历史夜晚发言失败: {e}")
                if day_speeches:
                    history_speeches += f"**第{day}天夜晚狼人发言:**\n{day_speeches}\n"

        return history_speeches

    def _read_history_night_votes(self, player_id_to_read=None): # Modified to accept player_id
        """读取特定玩家或所有狼人历史天数的夜晚投票"""
        history_votes = ""
        record_root = "record"
        current_day = self.app.state.day

        for day in range(0, current_day):
            day_folder = os.path.join(record_root, f"第{day}天", "夜晚玩家投票")
            if os.path.exists(day_folder):
                day_votes_str = ""
                files_to_read = []
                if player_id_to_read: # For specific player (seer, witch)
                    filename = f"玩家{player_id_to_read}夜晚投票.txt"
                    if os.path.exists(os.path.join(day_folder, filename)):
                        files_to_read.append(filename)
                else: # For werewolves, read all files in the directory
                    files_to_read = sorted(os.listdir(day_folder))

                for filename in files_to_read:
                    if filename.startswith("玩家") and filename.endswith("夜晚投票.txt"):
                        match = re.search(r'玩家(\d+)夜晚投票\.txt', filename)
                        if match:
                            p_id = int(match.group(1))
                            # If reading for a specific player, or if no specific player (werewolf context, read all)
                            if player_id_to_read == p_id or (not player_id_to_read and self.app.state.players[p_id].identity == "狼人"):
                                file_path = os.path.join(day_folder, filename)
                                try:
                                    with open(file_path, "r", encoding="utf-8") as f:
                                        content = f.read().strip()
                                        if content:
                                            day_votes_str += f"**玩家{p_id}投票**: {content}\n\n"
                                except Exception as e:
                                    self.app.ui_handler.log_system(f"[警告] 读取玩家 {p_id} 历史夜晚投票失败: {e}")
                if day_votes_str:
                    history_votes += f"**第{day}天夜晚投票:**\n{day_votes_str}\n"
        return history_votes


    def _read_check_record(self):
        """读取 record/查验.txt 文件内容"""
        check_record_content = ""
        check_file = os.path.join("record", "查验.txt")
        if os.path.exists(check_file):
            try:
                with open(check_file, "r", encoding="utf-8") as f:
                    check_record_content = f.read()
            except Exception as e:
                self.app.ui_handler.log_system(f"[警告] 读取查验记录文件 record/查验.txt 失败: {e}") 
                return "[读取查验记录失败，请检查日志]"
        return check_record_content

    def _read_player_history_day_votes(self, player_id):
        """读取特定玩家历史天数的所有白天投票"""
        player_history_votes = ""
        record_root = "record"
        current_day = self.app.state.day

        for day in range(0, current_day):
            day_folder = os.path.join(record_root, f"第{day}天", "白天玩家投票")
            if os.path.exists(day_folder):
                player_file = os.path.join(day_folder, f"玩家{player_id}白天投票.txt")
                if os.path.exists(player_file):
                    try:
                        with open(player_file, "r", encoding="utf-8") as f:
                            content = f.read().strip()
                            if content:
                                player_history_votes += f"**第{day}天白天投票**: {content}\n\n"
                    except Exception as e:
                        self.app.ui_handler.log_system(f"[警告] 读取玩家 {player_id} 第{day}天白天投票失败: {e}") 

        return player_history_votes

    def _read_player_history_night_votes(self, player_id): # Wrapper for specific player
        """读取特定玩家历史天数的所有夜晚投票"""
        return self._read_history_night_votes(player_id_to_read=player_id)


    def parse_vote_result(self, player_id, vote_text):
        # 解析投票结果并更新游戏状态
        vote_target = self._parse_vote_text(vote_text) # This helper method needs to be defined or logic integrated
        if vote_target is None:
            return None  # 解析错误，没有有效投票

        # 记录投票
        if self.app.state.phase == "day":
            if self.app.state.day == 0: # Sheriff vote
                save_sheriff_vote(player_id, self.app.state.day, vote_text)
            else: # Regular day vote
                save_daytime_vote(player_id, self.app.state.day, vote_text)
            self.app.state.day_votes[player_id] = vote_target

            # 记录玩家的投票历史 (This seems to be missing from original, but good to have)
            # player_obj = self.app.state.players[player_id]
            # if not hasattr(player_obj, 'vote_history'): player_obj.vote_history = []
            # player_obj.vote_history.append(vote_text)
        else:  # night phase
            save_night_vote(player_id, self.app.state.day, vote_text) # General night vote save
            self.app.state.night_votes[player_id] = vote_target
        return vote_target # Return parsed target

    def _parse_vote_text(self, vote_text):
        """
        Parses the AI's vote text to extract the target player ID, "随机" (random), or "弃票" (abstain).
        Returns the integer player ID, or the string "random"/"abstain", or None if unparseable.
        """
        # Normalize and simplify common patterns
        text_parsed = vote_text.replace("号玩家", "").replace("号", "").strip()

        player_brackets_match = re.search(r'\[玩家?(\d+)\]', text_parsed)
        if player_brackets_match: return int(player_brackets_match.group(1))
        
        brackets_number_match = re.search(r'\[(\d+)\]', text_parsed)
        if brackets_number_match: return int(brackets_number_match.group(1))

        chinese_player_brackets_match = re.search(r'【玩家?(\d+)】', text_parsed)
        if chinese_player_brackets_match: return int(chinese_player_brackets_match.group(1))

        chinese_brackets_number_match = re.search(r'【(\d+)】', text_parsed)
        if chinese_brackets_number_match: return int(chinese_brackets_number_match.group(1))

        if re.search(r'\[随机\]|【随机】|随机', text_parsed, re.IGNORECASE): return "random"
        if re.search(r'\[弃票\]|【弃票】|弃票|不使用|不用|跳过', text_parsed, re.IGNORECASE): return "abstain" # Treat "不使用" etc. as abstain for voting

        # Direct number mention, ensure it's not part of a larger number or word
        direct_player_mention = re.search(r'玩家\s*(\d+)', text_parsed)
        if direct_player_mention: return int(direct_player_mention.group(1))
        
        # Try to find a standalone number, preferring numbers mentioned with "玩家"
        # This regex tries to find numbers that are likely player IDs.
        # It avoids numbers in dates, or large numbers.
        potential_ids = re.findall(r'\b([1-9]|10)\b', text_parsed) # Assuming max 10 players
        if potential_ids:
            # If multiple numbers, this heuristic might not be perfect.
            # Consider context if needed, e.g. "我投给 3 号", "我觉得 5 号是狼人"
            # For now, taking the last mentioned valid ID.
            for p_id_str in reversed(potential_ids):
                try:
                    p_id = int(p_id_str)
                    if 1 <= p_id <= self.app.state.player_count : # Check if it's a valid player ID
                        # Check if this number is preceded by words indicating a vote for it
                        # This is a simple heuristic. More sophisticated NLP could be used.
                        if re.search(f"(投给|选|目标是).*?{p_id}", text_parsed) or \
                           re.search(f"{p_id}.*?(是目标|当选)", text_parsed):
                            return p_id
                        # If no strong indicator, but it's the only number, consider it.
                        if len(potential_ids) == 1:
                            return p_id
                except ValueError:
                    continue
        return None # Unparseable


    def _read_sheriff_speeches(self):
        """读取当前天数的所有警长竞选发言"""
        sheriff_speeches = ""
        record_root = "record"
        day_folder = os.path.join(record_root, f"第{self.app.state.day}天", "警长竞选", "竞选发言")
        if os.path.exists(day_folder):
            import re
            for filename in sorted(os.listdir(day_folder)):
                if filename.startswith("玩家") and filename.endswith("竞选发言.txt"):
                    match = re.search(r'玩家(\d+)竞选发言\.txt', filename)
                    if match:
                        p_id = int(match.group(1))
                        if self.app.state.players[p_id].alive and self.app.state.players[p_id].exists:
                            file_path = os.path.join(day_folder, filename)
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    content = f.read().strip()
                                    if content:
                                        sheriff_speeches += f"**玩家{p_id}**: {content}\n\n"
                            except Exception as e:
                                self.app.ui_handler.log_system(f"[警告] 读取玩家 {p_id} 警长竞选发言失败: {e}") 
        return sheriff_speeches

    def _read_player_sheriff_vote(self, player_id):
        """读取特定玩家的警长竞选投票"""
        player_sheriff_vote = ""
        record_root = "record"
        day_folder = os.path.join(record_root, f"第{self.app.state.day}天", "警长竞选", "竞选投票")
        if os.path.exists(day_folder):
            player_file = os.path.join(day_folder, f"玩家{player_id}竞选投票.txt")
            if os.path.exists(player_file):
                try:
                    with open(player_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            player_sheriff_vote = f"**警长竞选投票**: {content}\n\n"
                except Exception as e:
                    self.app.ui_handler.log_system(f"[警告] 读取玩家 {player_id} 警长竞选投票失败: {e}") 
        return player_sheriff_vote
