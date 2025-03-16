import tkinter as tk
from record import save_daytime_vote, save_night_vote, append_check_record
import re
import random
from readrecord import (get_last_words_content, get_day_vote_reasoning_player, get_night_vote_reasoning_player)
import os
from TTS import play_tts  # 导入 TTS 模块

class VoteHandler:
    def __init__(self, app):
        self.app = app
        self.model_handler = app.model_handler  # 获取 ModelHandler 实例

    def player_vote(self, player_id):
        player = self.app.state.players[player_id]
        # 特殊处理：确保女巫在夜晚可以投票
        if player.identity == "女巫" and self.app.state.phase == "night":
            # 不做其他额外检查，直接继续
            pass
        elif not (player.exists and player.alive):
            self.app.log_system(f"玩家 {player_id} 不存在或已死亡，无法投票。")
            return

        # 构造历史死亡信息
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
        else:
            history_info_formatted += "暂无死亡记录\n"
        history_info_formatted = f"**【开始】【历史死亡信息】**\n{history_info_formatted}**【结束】【历史死亡信息】**\n"

        # 定义游戏状态信息块（原格式）
        game_state_info = f"**【开始】【游戏状态】**\n" \
                          f"**初始狼人数量**: {self.app.state.initial_wolf_count}\n" \
                          f"**总玩家数量**: {self.app.state.player_count}\n" \
                          f"**当前天数**: {self.app.state.day}\n" \
                          f"**初始预言家数量**: {self.app.state.initial_seer_count}\n" \
                          f"**初始猎人数量**: {self.app.state.initial_hunter_count}\n" \
                          f"**初始女巫数量**: {self.app.state.initial_witch_count}\n" \
                          f"**存活玩家**: {[p.player_id for p in self.app.state.players.values() if p.exists and p.alive]}\n" \
                          f"**【结束】【游戏状态】**\n"

        # 新增 extra_info：包含两遍身份提示与两遍游戏状态信息
        extra_info = ((f"**【提示】你是谁：玩家 {player_id}，身份：{player.identity}。请牢记这一点！**\n") * 2 +
                      (game_state_info) * 2)
        if player.identity == "狼人":
            teammates = [p.player_id for p in self.app.state.players.values() if p.identity == "狼人" and p.player_id != player_id]
            extra_info += ((f"**【队友信息】: 狼人队友：{teammates}**\n") * 2)
        header_footer = f"**【开始】【玩家{player_id}】**\n" + extra_info + history_info_formatted
        footer = extra_info + f"\n**【结束】【玩家{player_id}】**"
        last_words = get_last_words_content()

        # 公共限制提示：控制投票内容在300字以内，并直接写入三句新提示信息
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

        # 在 prompt 最前面添加"玩家X开始投票..."或"玩家X开始夜晚投票..."
        if self.app.state.phase == "day":
            phase_indicator = "【当前阶段：白天投票阶段】\n"
            start_line = f"玩家 {player_id} 开始投票...\n"
            if player.identity == "平民":
                role_tip = ("【提示-平民】作为平民，请结合所有已知信息（历史死亡、游戏状态、前一日投票总结、其他玩家发言及遗言记录），"
                            "做出你认为最合理的投票选择，并务必说明理由。请注意隐藏身份，确保投票内容控制在300字以内！")
                # 读取玩家自己所有的白天投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                daytime_speeches = self._read_day_speeches()  # 获取白天发言
                history_speeches = self._read_history_day_speeches()
                history_votes = self._read_history_day_votes()
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【今日其他玩家发言】**:\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**:\n{last_words}\n" +
                          role_tip + footer + common_suffix)
            elif player.identity == "狼人":
                role_tip = ("【提示-狼人】作为狼人，请结合所有已知信息（历史死亡、游戏状态、前一日投票总结、其他玩家发言及遗言记录），"
                            "做出你的投票选择。注意隐藏身份、迷惑好人，同时务必说明理由，确保投票内容控制在300字以内！")
                # 读取玩家自己所有的白天和夜晚投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                player_night_votes = self._read_player_history_night_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                history_night_speeches = self._read_history_night_speeches()
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚投票记录】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**:\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史夜晚狼人发言】**\n{history_night_speeches}\n" +
                          f"**【历史遗言记录】**:\n{last_words}\n" +
                          f"**【队友信息】: 狼人队友：{teammates}**\n" +
                          role_tip + footer + common_suffix)
            elif player.identity == "预言家":
                role_tip = ("【提示-预言家】作为预言家，请结合所有已知信息（历史死亡、游戏状态、前一日投票总结、其他玩家发言、查验信息及遗言记录），"
                            "做出你认为最合理的投票选择，并务必说明理由。请注意保持隐晦，确保投票内容控制在300字以内！")
                # 读取玩家自己所有的白天和夜晚投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                player_night_votes = self._read_player_history_night_votes(player_id)
                day_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                check_record_content = self._read_check_record()
                check_info = f"**【当前查验信息 record/查验.txt 内容如下】**:\n{check_record_content}\n" \
                             f"**【查验信息结束】**\n"
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚投票记录(查验)】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**:\n{day_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          check_info + "\n" +
                          f"**【历史遗言记录】**:\n{last_words}\n" +
                          role_tip + footer + common_suffix)
            
            elif player.identity == "猎人":
                role_tip = ("【提示-猎人】作为猎人，请结合所有已知信息（历史死亡、游戏状态、前一日投票总结、其他玩家发言及遗言记录），"
                            "做出你认为最合理的投票选择，并务必说明理由。记住你死亡时可以带走一名玩家，确保投票内容控制在300字以内！")
                # 读取玩家自己所有的白天投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【今日其他玩家发言】**:\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**:\n{last_words}\n" +
                          role_tip + footer + common_suffix)
            
            elif player.identity == "女巫":
                # 读取女巫的药水使用状态
                save_used = self.app.state.witch_save_used.get(player_id, False)
                poison_used = self.app.state.witch_poison_used.get(player_id, False)
                drug_status = f"**【女巫药水状态】**\n救人药：{'已使用' if save_used else '未使用'}\n毒药：{'已使用' if poison_used else '未使用'}\n"
                
                role_tip = ("【提示-女巫】作为女巫，请结合所有已知信息（历史死亡、游戏状态、前一日投票总结、其他玩家发言及遗言记录），"
                            "做出你认为最合理的投票选择，并务必说明理由。请注意隐藏身份，确保投票内容控制在300字以内！")
                
                # 读取玩家自己所有的白天投票记录和夜间使用药水记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                player_night_votes = self._read_player_history_night_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          drug_status +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚药水使用记录】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**:\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**:\n{last_words}\n" +
                          role_tip + footer + common_suffix)

            self.app.log_system(f"玩家 {player_id} 准备进行白天投票...")

        else:  # 夜晚阶段
            phase_indicator = "【当前阶段：夜晚查验/投票阶段】\n"
            start_line = f"玩家 {player_id} 开始夜晚投票...\n"
            if player.identity == "狼人":  # 狼人夜晚投票
                role_tip = ("【提示-夜晚狼人】作为狼人，现在是夜晚，请结合所有已知信息（当日白天投票总结、其他玩家发言及遗言记录），"
                            "做出你的投票选择，目标仅限非狼人。务必说明理由，并确保投票内容控制在300字以内！")
                # 读取玩家自己所有的白天和夜晚投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                player_night_votes = self._read_player_history_night_votes(player_id)
                daytime_speeches = self._read_day_speeches()  # 获取白天发言
                history_speeches = self._read_history_day_speeches()
                history_night_speeches = self._read_history_night_speeches()
                teammates = [p.player_id for p in self.app.state.players.values() if p.identity == "狼人" and p.player_id != player_id]
                night_speeches_teammates = ""
                for p_id in teammates:
                    if self.app.state.players[p_id].speech_history and self.app.state.players[p_id].speech_history[-1]:
                        night_speeches_teammates += f"**队友玩家{p_id}**: {self.app.state.players[p_id].speech_history[-1]}\n\n"
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚投票记录】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【今晚队友发言】**\n{night_speeches_teammates}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史夜晚狼人发言】**\n{history_night_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix)
            elif player.identity == "预言家":  # 预言家夜晚查验
                role_tip = ("【提示-夜晚预言家】作为预言家，现在是夜晚查验阶段，请结合所有已知信息（今日白天投票总结、其他玩家发言、查验信息及遗言记录），"
                            "做出你认为最合理的查验选择，并务必说明理由。请注意保持隐晦，确保查验内容控制在300字以内！")
                # 读取玩家自己所有的白天和夜晚投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                player_night_votes = self._read_player_history_night_votes(player_id)
                day_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                check_record_content = self._read_check_record()
                check_info = f"**【当前查验信息 record/查验.txt 内容如下】**:\n{check_record_content}\n" \
                             f"**【查验信息结束】**\n"
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚投票记录(查验)】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**\n{day_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          check_info + "\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix)
            elif player.identity == "女巫":  # 女巫夜晚使用药水
                # 读取女巫的药水使用状态
                save_used = self.app.state.witch_save_used.get(player_id, False)
                poison_used = self.app.state.witch_poison_used.get(player_id, False)
                
                # 获取狼人今晚计划杀死的目标
                wolf_target = self.app.state.wolf_kill_target
                wolf_target_info = ""
                if wolf_target:
                    # 如果狼人目标是女巫自己，特别提示自救
                    if wolf_target == player_id:
                        wolf_target_info = f"**【狼人今晚的击杀目标】**: 你自己（玩家 {player_id}）被狼人选为击杀目标\n"
                        # 如果两种药都用过了，就不需要提示可以救人
                        if not save_used:
                            wolf_target_info += f"你可以输入 [玩家{player_id}] 使用救人药救自己\n"
                        if not poison_used:
                            wolf_target_info += f"你可以输入 [其他玩家编号] 使用毒药毒死该玩家\n"
                        wolf_target_info += "如果不想使用任何药水，请输入 [弃票] 或 [不使用]\n"
                    else:
                        wolf_target_info = f"**【狼人今晚的击杀目标】**: 玩家 {wolf_target}\n"
                        # 如果两种药都用过了，就不需要提示可以救人
                        if not save_used:
                            wolf_target_info += f"你可以输入 [玩家{wolf_target}] 使用救人药救活玩家 {wolf_target}\n"
                        if not poison_used:
                            wolf_target_info += f"你可以输入 [其他玩家编号] 使用毒药毒死该玩家\n"
                        wolf_target_info += "如果不想使用任何药水，请输入 [弃票] 或 [不使用]\n"
                else:
                    wolf_target_info = "**【狼人今晚的击杀情况】**: 狼人还没有确定击杀目标或还没有投票\n"
                    if not poison_used:
                        wolf_target_info += "你可以输入 [玩家编号] 使用毒药毒死该玩家\n"
                    wolf_target_info += "如果不想使用任何药水，请输入 [弃票] 或 [不使用]\n"
                
                # 构建女巫的提示
                if not save_used and not poison_used:
                    role_tip = ("【提示-夜晚女巫】作为女巫，现在是夜晚阶段，你可以使用救人药或毒药！\n"
                               f"{wolf_target_info if wolf_target_info else ''}"
                               "- 如果选择被狼人杀死的人，将使用救人药将其救活（一局游戏只能用一次）\n"
                               "- 如果选择其他存活的人，将使用毒药将其毒死（一局游戏只能用一次）")
                elif not save_used:
                    role_tip = ("【提示-夜晚女巫】作为女巫，现在是夜晚阶段，你已经用掉了毒药，但仍可以使用救人药！\n"
                               f"{wolf_target_info if wolf_target_info else ''}"
                               "如果选择被狼人杀死的人，将使用救人药将其救活（一局游戏只能用一次）")
                elif not poison_used:
                    role_tip = ("【提示-夜晚女巫】作为女巫，现在是夜晚阶段，你已经用掉了救人药，但仍可以使用毒药！\n"
                               "如果选择存活的人，将使用毒药将其毒死（一局游戏只能用一次）")
                
                # 构建药水状态信息
                drug_status = f"**【女巫药水状态】**\n救人药：{'已使用' if save_used else '未使用'}\n毒药：{'已使用' if poison_used else '未使用'}\n"
                
                # 读取玩家自己所有的白天和夜晚投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                player_night_votes = self._read_player_history_night_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          drug_status +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚药水使用记录】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix)
            else:  # 其他角色如猎人等
                # 通用的夜晚投票提示
                role_tip = (f"【提示-夜晚{player.identity}】作为{player.identity}，现在是夜晚阶段，"
                           "请结合所有已知信息，做出你的投票选择，并务必说明理由。请确保投票内容控制在300字以内！")
                
                # 读取玩家自己所有的白天投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                player_night_votes = self._read_player_history_night_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚投票记录】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix)

            self.app.log_system(f"{player.identity} 玩家 {player_id} 准备进行夜晚投票/查验...")

        def vote_callback(final_answer_text):
            text_parsed = final_answer_text.replace("\\n", "\n")
            vote_result = None

            # 添加对"[玩家X]"格式的支持
            player_brackets = re.findall(r'\[玩家(\d+)\]', text_parsed)
            brackets_number = re.findall(r'\[(\d+)\]', text_parsed)
            
            if player_brackets:
                # 优先使用"[玩家X]"格式
                vote_result = player_brackets[-1]
                try:
                    vote_target = int(vote_result)
                except ValueError:
                    self.app.log_system(f"[警告] 无法解析 玩家 {player_id} 的投票目标编号 (方括号玩家数字)，投票作废。")
                    return
            elif brackets_number:
                vote_result = brackets_number[-1]
                try:
                    vote_target = int(vote_result)
                except ValueError:
                    self.app.log_system(f"[警告] 无法解析 玩家 {player_id} 的投票目标编号 (方括号数字)，投票作废。")
                    return
            # 这里是随机/弃票逻辑
            else:
                random_choice = re.search(r'[\[\(]?随机[\]\)]?', text_parsed, re.IGNORECASE)
                abstain_choice = re.search(r'[\[\(]?弃票[\]\)]?', text_parsed, re.IGNORECASE)
                skip_choice = re.search(r'[\[\(]?跳过[\]\)]?|[\[\(]?不使用[\]\)]?|[\[\(]?不用[\]\)]?', text_parsed, re.IGNORECASE)
                
                if random_choice:
                    # 随机选择一个存活的玩家
                    alive_players = [i for i, p in self.app.state.players.items() 
                                     if p.exists and p.alive and i != player_id]
                    if not alive_players:
                        self.app.log_system(f"[警告] 玩家 {player_id} 选择随机投票，但没有有效的目标！")
                        return
                        
                    vote_target = random.choice(alive_players)
                    vote_result = str(vote_target)
                    
                elif abstain_choice or skip_choice: # 增加"跳过"等选项
                    vote_target = "弃票"
                    vote_result = "弃票"

                    # 女巫特殊处理：允许弃票表示不使用药水
                    if player.identity == "女巫" and self.app.state.phase == "night":
                        self.app.log_system(f"女巫 {player_id} 选择本回合不使用药水")
                        self.app.state.night_votes[player_id] = "不使用药水"
                        save_night_vote(player_id, self.app.state.day, text_parsed)
                        return
                else:
                    self.app.log_system(f"[警告] 无法解析 玩家 {player_id} 的投票目标，投票作废。")
                    return
            
            # 统一处理投票逻辑
            if self.app.state.phase == "day":
                self.app.state.day_votes[player_id] = vote_target
                save_daytime_vote(player_id, self.app.state.day, text_parsed)
            elif self.app.state.phase == "night":
                if player.identity == "狼人":
                    self.app.state.night_votes[player_id] = vote_target
                    save_night_vote(player_id, self.app.state.day, text_parsed)
                elif player.identity == "预言家":
                    check_target_id_str = vote_result
                    if check_target_id_str in ["随机", "弃票", None]:
                        self.app.log_system(f"[警告] 预言家 {player_id} 查验目标无效: {check_target_id_str}， 本回合查验作废。")
                        self.app.log_system(f"[系统提示] 预言家当晚查验结果为：**无效**")
                        return
                    try:
                        check_target_id = int(check_target_id_str)
                    except ValueError:
                        self.app.log_system(f"[警告] 预言家 {player_id} 查验目标ID无效: {check_target_id_str}， 查验作废。")
                        self.app.log_system(f"[系统提示] 预言家当晚查验结果为：**无效**")
                        return
                    if check_target_id not in self.app.state.players or not self.app.state.players[check_target_id].exists:
                        self.app.log_system(f"[警告] 预言家 {player_id} 查验目标不存在: 玩家 {check_target_id}， 查验作废。")
                        self.app.log_system(f"[系统提示] 预言家当晚查验结果为：**无效**")
                        return

                    checked_player = self.app.state.players[check_target_id]
                    checked_player_identity = checked_player.identity

                    append_check_record(self.app.state.day, player_id, check_target_id, checked_player_identity)
                    self.app.log_system(f"[查验结果] 预言家 玩家 {player_id} 查验 玩家 {check_target_id}， 身份：{checked_player_identity}")
                    self.app.log_system(f"[系统提示] 预言家当晚查验 玩家 {check_target_id}， 身份：**{checked_player_identity}**")
                    self.app.summary_text.insert(tk.END, f" [查验] 玩家 {player_id} 查验了 玩家{check_target_id} 身份为{checked_player_identity}\n", f"p{player_id}")
                    self.app.summary_text.see(tk.END)
                elif player.identity == "女巫":
                    # 女巫的投票目标已经存储在vote_target中
                    # 立即处理女巫的药水效果，不等待夜晚投票结算
                    
                    # 初始化女巫的药水状态（如果还没有）
                    if player_id not in self.app.state.witch_save_used:
                        self.app.state.witch_save_used[player_id] = False
                    if player_id not in self.app.state.witch_poison_used:
                        self.app.state.witch_poison_used[player_id] = False
                        
                    save_used = self.app.state.witch_save_used.get(player_id, False)
                    poison_used = self.app.state.witch_poison_used.get(player_id, False)
                    
                    # 检查投票目标是否有效
                    if vote_target in self.app.state.players and self.app.state.players[vote_target].exists:
                        # 如果目标是当晚狼人击杀的人，则视为使用救人药
                        wolf_target = self.app.state.wolf_kill_target
                        
                        # 女巫自救或救别人的情况
                        if (vote_target == wolf_target or (wolf_target == player_id and vote_target == player_id)) and not save_used:
                            # 使用救人药
                            self.app.state.witch_save_used[player_id] = True
                            
                            # 区分自救和救别人的情况
                            if vote_target == player_id and wolf_target == player_id:
                                self.app.log_system(f"女巫 {player_id} 使用了救人药救了自己")
                                self.app.summary_text.insert(tk.END, f"女巫 {player_id} 使用了救人药救了自己！\n", f"p{player_id}")
                            else:
                                self.app.log_system(f"女巫 {player_id} 使用了救人药救活了玩家 {vote_target}")
                                self.app.summary_text.insert(tk.END, f"女巫 {player_id} 使用了救人药救活了玩家 {vote_target}！\n", f"p{player_id}")
                            
                            self.app.summary_text.see(tk.END)
                            self.app.state.night_votes[player_id] = vote_target
                            
                            # 标记这个目标已被女巫救活，在finalize_night_voting中不会被狼人杀死
                            self.app.state.witch_save_target = vote_target
                            
                            # 确保被救玩家的生存状态为活着，移除死亡列表中的记录
                            # 防止玩家被狼人或其他方式标记为死亡后，无法被正确救活
                            if not self.app.state.players[vote_target].alive:
                                self.app.state.players[vote_target].alive = True
                                
                                # 如果已经在当天死亡列表中，移除它
                                if vote_target in self.app.state.dead_today:
                                    self.app.state.dead_today.remove(vote_target)
                                
                                # 从当天死亡摘要中移除
                                deaths_to_remove = []
                                for i, (pid, cause) in enumerate(self.app.state.current_day_summary["deaths"]):
                                    if pid == vote_target:
                                        deaths_to_remove.append(i)
                                
                                # 从后往前删除，避免索引变化
                                for idx in sorted(deaths_to_remove, reverse=True):
                                    self.app.state.current_day_summary["deaths"].pop(idx)
                            
                            # 如果目标是活人且不是狼人击杀的目标，则视为使用毒药
                            elif self.app.state.players[vote_target].alive and not poison_used:
                                # 使用毒药
                                self.app.state.witch_poison_used[player_id] = True
                                self.app.log_system(f"女巫 {player_id} 使用了毒药毒死了玩家 {vote_target}")
                                self.app.summary_text.insert(tk.END, f"女巫 {player_id} 使用了毒药毒死了玩家 {vote_target}！\n", f"p{player_id}")
                                self.app.summary_text.see(tk.END)
                                self.app.state.night_votes[player_id] = vote_target
                                
                                # 立即标记毒死的玩家
                                self.app.state.players[vote_target].alive = False
                                self.app.state.dead_today.append(vote_target)
                                self.app.state.current_day_summary["deaths"].append((vote_target, "夜晚死亡"))
                                
                                # 启用遗言按钮
                                self.app.lastword_buttons[vote_target].config(state=tk.NORMAL)
                                
                                # 检查游戏是否结束
                                game_over, winner = self.app.state.check_game_over()
                                if game_over:
                                    self.app.game_logic_handler.end_game(winner)
                            else:
                                if vote_target == wolf_target and save_used:
                                    self.app.log_system(f"[警告] 女巫 {player_id} 尝试救活玩家 {vote_target}，但救人药已使用过")
                                elif not self.app.state.players[vote_target].alive:
                                    self.app.log_system(f"[警告] 女巫 {player_id} 尝试对已死亡的玩家 {vote_target} 使用药水")
                                elif poison_used:
                                    self.app.log_system(f"[警告] 女巫 {player_id} 尝试使用毒药，但毒药已使用过")
                    else:
                        self.app.log_system(f"[警告] 女巫 {player_id} 选择的目标 {vote_target} 不存在或无效")
                    
                    # 保存女巫的投票记录
                    save_night_vote(player_id, self.app.state.day, text_parsed)
                else:
                    # 其他角色的夜晚投票
                    self.app.state.night_votes[player_id] = vote_target
                    save_night_vote(player_id, self.app.state.day, text_parsed)
                    self.app.log_system(f"{player.identity} 玩家 {player_id} 夜晚投票选择了 玩家 {vote_target}")

            # 根据 TTS 开关状态播放语音
            if self.app.tts_enabled:
                play_tts(text_parsed, player_id)

        self.model_handler.call_model(player.model, prompt, self.app.summary_text, tag=f"p{player_id}",
                                      callback=vote_callback, player_id=player_id)

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
        
        # 从第1天到当前天数-1，读取所有历史发言
        for day in range(1, current_day):
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
        
        # 从第1天到当前天数-1，读取所有历史投票
        for day in range(1, current_day):
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
        
        # 从第1天到当前天数-1，读取所有历史发言
        for day in range(1, current_day):
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
    
    def _read_history_night_votes(self):
        """读取历史天数的狼人夜晚投票（仅适用于狼人玩家）"""
        history_votes = ""
        record_root = "record"
        current_day = self.app.state.day
        
        # 从第1天到当前天数-1，读取所有历史投票
        for day in range(1, current_day):
            day_folder = os.path.join(record_root, f"第{day}天", "夜晚玩家投票")
            if os.path.exists(day_folder):
                import re
                day_votes = ""
                for filename in sorted(os.listdir(day_folder)):
                    if filename.startswith("玩家") and filename.endswith("夜晚投票.txt"):
                        match = re.search(r'玩家(\d+)夜晚投票\.txt', filename)
                        if match:
                            p_id = int(match.group(1))
                            if self.app.state.players[p_id].identity == "狼人":  # 仅读取狼人投票
                                file_path = os.path.join(day_folder, filename)
                                try:
                                    with open(file_path, "r", encoding="utf-8") as f:
                                        content = f.read().strip()
                                        if content:
                                            day_votes += f"**狼人玩家{p_id}投票**: {content}\n\n"
                                except Exception as e:
                                    print(f"[警告] 读取玩家 {p_id} 历史夜晚投票失败: {e}")
                if day_votes:
                    history_votes += f"**第{day}天夜晚投票:**\n{day_votes}\n"
        
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
                self.app.log_system(f"[警告] 读取查验记录文件 record/查验.txt 失败: {e}")
                return "[读取查验记录失败，请检查日志]"
        return check_record_content

    # 新增读取玩家自己所有历史白天投票的方法
    def _read_player_history_day_votes(self, player_id):
        """读取特定玩家历史天数的所有白天投票"""
        player_history_votes = ""
        record_root = "record"
        current_day = self.app.state.day
        
        # 从第1天到当前天数-1，读取所有历史投票
        for day in range(1, current_day):
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
                        self.app.log_system(f"[警告] 读取玩家 {player_id} 第{day}天白天投票失败: {e}")
        
        return player_history_votes

    # 新增读取玩家自己所有历史夜晚投票的方法
    def _read_player_history_night_votes(self, player_id):
        """读取特定玩家历史天数的所有夜晚投票"""
        player_history_votes = ""
        record_root = "record"
        current_day = self.app.state.day
        
        # 从第1天到当前天数-1，读取所有历史投票
        for day in range(1, current_day):
            day_folder = os.path.join(record_root, f"第{day}天", "夜晚玩家投票")
            if os.path.exists(day_folder):
                player_file = os.path.join(day_folder, f"玩家{player_id}夜晚投票.txt")
                if os.path.exists(player_file):
                    try:
                        with open(player_file, "r", encoding="utf-8") as f:
                            content = f.read().strip()
                            if content:
                                player_history_votes += f"**第{day}天夜晚投票**: {content}\n\n"
                    except Exception as e:
                        self.app.log_system(f"[警告] 读取玩家 {player_id} 第{day}天夜晚投票失败: {e}")
        
        return player_history_votes
