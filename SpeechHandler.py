from record import save_daytime_speech, save_night_speech, save_sheriff_speech
from readrecord import (get_last_words_content, get_day_vote_reasoning_player, get_night_vote_reasoning_player)
import os
import re
from TTS import play_tts  # 导入 TTS 模块
import tkinter as tk

class SpeechHandler:
    def __init__(self, app):
        self.app = app
        self.model_handler = app.model_handler  # 获取 ModelHandler 实例
        self.sheriff_speak_count = {}  # 跟踪每个警长的发言次数

    def player_speak(self, player_id):
        player = self.app.state.players[player_id]
        
        # 只有两种情况会阻止玩家发言：
        # 1. 玩家不存在
        # 2. 活着的玩家在夜晚试图发言（除了狼人和预言家）
        if not player.exists:
            self.app.log_system(f"玩家 {player_id} 不存在，无法发言。")
            return
            
        # 如果是死亡玩家，则视为遗言阶段，允许发言
        is_last_words = not player.alive
        
        # 如果是夜晚，且玩家仍然活着，但不是狼人，则阻止发言
        if self.app.state.phase == "night" and player.alive and player.identity != "狼人":
            self.app.log_system(f"玩家 {player_id} 不是狼人，无法在夜晚发言。")
            return

        # 准备阶段提示信息
        if is_last_words:
            self.app.log_system(f"玩家 {player_id} 准备进行遗言发言...")
        elif self.app.state.phase == "day":
            # 白天发言准备提示
            identity_display = player.identity if player.identity != "空" else "玩家"
            if self.app.state.day == 0:
                self.app.log_system(f"{identity_display} {player_id} 准备进行警长竞选发言...")
            else:
                self.app.log_system(f"{identity_display} {player_id} 准备进行白天发言...")
        else:
            # 夜晚发言准备提示
            self.app.log_system(f"狼人 {player_id} 准备进行夜晚发言...")

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
            history_info_formatted += "暂无历史死亡记录\n"
            
        # 添加当天的死亡信息
        current_day = self.app.state.day
        current_deaths = self.app.state.current_day_summary.get("deaths", [])
        if current_deaths:
            death_str = ", ".join([f"玩家{pid}({cause})" for pid, cause in current_deaths])
            history_info_formatted += f"**第{current_day}天(当天)**: 死亡: {death_str}\n"
            
        history_info_formatted = f"**【开始】【历史死亡信息】**\n{history_info_formatted}**【结束】【历史死亡信息】**\n"

        # 定义游戏状态信息块
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

        # 公共限制提示：控制发言在300字以内
        common_prefix = "【注意】请务必将你的发言控制在300字以内，以免耽误其他玩家的发言时间。\n"
        common_suffix = "\n【提醒】请保持发言简洁明了，限于300字以内。"

        # 获取当前警长的提示（适用于所有角色）
        def get_sheriff_guidance(player_id):
            sheriff_guidance = ""
            if self.app.state.sheriff_id == player_id:
                # 初始化或增加警长发言计数
                if player_id not in self.sheriff_speak_count:
                    self.sheriff_speak_count[player_id] = 0
                self.sheriff_speak_count[player_id] += 1
                
                # 根据发言次数添加不同提示
                if self.sheriff_speak_count[player_id] == 1:
                    sheriff_guidance = "\n【警长提示】作为警长，你现在需要决定发言顺序！\n"
                elif self.sheriff_speak_count[player_id] == 2:
                    sheriff_guidance = "\n【警长提示】现在是正常的发言阶段！\n"
                elif self.sheriff_speak_count[player_id] >= 3:
                    sheriff_guidance = "\n【警长提示】请对今天所有人的发言进行总结！\n"
            return sheriff_guidance

        # 遗言阶段（死亡玩家）
        if is_last_words:
            phase_indicator = "【当前阶段：遗言发言阶段】\n"
            # 在 prompt 最前面添加"玩家X开始遗言..."
            start_line = f"玩家 {player_id} 开始遗言...\n"
            
            if player.identity == "平民":
                role_tip = (
                    "【提示-平民】作为平民，这是你最后的机会！\n"
                    "结合已知信息，分析局势，找出最可疑的目标。\n"
                    "重点关注发言逻辑漏洞和行为异常的玩家。\n"
                    "尝试与可信角色（如预言家）建立联系，但注意不要暴露身份。\n"
                    "如果局势不明朗，选择保守发言，避免让狼人得利。\n"
                    "必要时可煽动其他玩家形成对特定目标的压力。\n"
                    "⚠️ 请务必将你的遗言控制在300字以内！"
                )
                # 读取玩家自己所有的白天投票记录，而不仅仅是前一天的
                player_day_votes = self._read_player_history_day_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                history_votes = self._read_history_day_votes()
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix)

            elif player.identity == "狼人":
                start_line = f"玩家 {player_id} 开始发表遗言...\n"
                role_tip = (
                    "【提示-狼人】作为狼人，这是你最后的机会！\n"
                    "隐藏你的狼人身份，伺机而动！\n"
                    "在遗言中制造混乱，避免暴露队友信息。\n"
                    "适当嫁祸好人，迷惑其他玩家，使他们怀疑错误目标。\n"
                    "利用反向思维暗示他人攻击可信好人。\n"
                    "若身份已暴露，试图虚假爆料，引导错误方向。\n"
                    "⚠️ 请务必将你的遗言控制在300字以内！"
                )
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
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史夜晚狼人发言】**\n{history_night_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          f"**【队友信息】狼人队友：{teammates}**\n" +
                          role_tip + footer + common_suffix)

            elif player.identity == "预言家":
                start_line = f"玩家 {player_id} 开始发表遗言...\n"
                role_tip = (
                    "【提示-预言家】作为预言家，这是你最后留下关键信息的机会！\n"
                    "清晰表达查验结果，但要谨慎措辞，防止狼人利用。\n"
                    "根据查验信息和发言表现推理玩家身份，排除狼人。\n"
                    "巧妙利用金水身份争取信任，巩固地位。\n"
                    "若身份暴露，可考虑悍跳扰乱狼人节奏。\n"
                    "观察其他玩家反应，判断真假预言家。\n"
                    "⚠️ 请务必将你的遗言控制在300字以内！"
                )
                # 读取玩家自己所有的白天和夜晚投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                player_night_votes = self._read_player_history_night_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                check_record_content = self._read_check_record()
                check_info = f"**【当前查验信息 record/查验.txt 内容如下】**:\n{check_record_content}\n" \
                             f"**【查验信息结束】**\n"
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚投票记录(查验)】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          check_info +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix)

            elif player.identity == "猎人":
                start_line = f"玩家 {player_id} 开始发表遗言并准备带走一名玩家...\n"
                role_tip = (
                    "【提示-猎人】作为猎人，你拥有死后带走一名玩家的能力！\n"
                    "**重要：作为猎人，你可以在死亡时带走一名玩家。请在遗言的同时选择你想带走的玩家！**\n"
                    "结合已知信息，分析局势，找出最可疑的目标。\n"
                    "重点关注发言逻辑漏洞和行为异常的玩家。\n"
                    "如果确定了狼人身份，请优先带走狼人。\n"
                    "若局势不明朗，可做出保守选择或做出战略性带人。\n"
                    "**在遗言结束后，请像投票一样用[玩家编号]格式指定你要带走的人，或者输入[随机]或[弃票]。**\n"
                    "⚠️ 请务必将你的遗言控制在300字以内！"
                )
                # 读取玩家自己所有的白天投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                history_votes = self._read_history_day_votes()
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                        role_tip + "\n" +
                        f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                        f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                        f"**【历史白天发言】**\n{history_speeches}\n" +
                        f"**【历史遗言记录】**\n{last_words}\n" +
                        role_tip + footer + common_suffix)

            elif player.identity == "女巫":
                start_line = f"玩家 {player_id} 开始发表遗言...\n"
                role_tip = (
                    "【提示-女巫】作为女巫，这是你最后的机会！\n"
                    "在遗言中尝试传递你所知道的信息，特别是夜晚观察到的情况。\n"
                    "如果你已经使用过解药或毒药，可以提示其他玩家你的行动。\n"
                    "分析场上局势，给予其他好人建议，帮助他们找出狼人。\n"
                    "如果你知道某些玩家的身份，可以在遗言中暗示或直接指出。\n"
                    "尽量避免暴露其他身份不明的好人，以免对方被狼人针对。\n"
                    "⚠️ 请务必将你的遗言控制在300字以内！"
                )
                
                # 读取女巫的药水使用状态
                save_used = self.app.state.witch_save_used.get(player_id, False)
                poison_used = self.app.state.witch_poison_used.get(player_id, False)
                drug_status = f"**【女巫药水状态】**\n救人药：{'已使用' if save_used else '未使用'}\n毒药：{'已使用' if poison_used else '未使用'}\n"
                
                # 读取玩家自己所有的白天投票记录和夜间投票记录
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

            # 日志记录开始遗言
            self.app.log_system(f"玩家 {player_id} 开始遗言发言...")

        # 如果不是遗言阶段，则按照正常的白天/夜晚阶段处理
        elif self.app.state.phase == "day":
            # 白天发言阶段（活着玩家）
            if self.app.state.day == 0:  # 第0天是警长竞选阶段
                phase_indicator = "【当前阶段：警长竞选发言阶段】\n"
                # 在 prompt 最前面添加"玩家X开始警长竞选发言..."
                start_line = f"玩家 {player_id} 开始警长竞选发言...\n"
            else:
                phase_indicator = "【当前阶段：白天发言阶段】\n"
                # 在 prompt 最前面添加"玩家X开始发言..."
                start_line = f"玩家 {player_id} 开始发言...\n"

            # 如果是第一天，则额外添加一段提示
            day1_notice = ""
            if self.app.state.day == 1:
                day1_notice = (
                    "\n【注意-第一天白天】现在这是第一天游戏刚开始，现在是游戏的第一个阶段，"
                    "现在没有人被投票放逐，没有人被狼人杀死，没人被预言家查明身份。\n"
                )

            # 警长竞选提示
            sheriff_notice = ""
            if self.app.state.day == 0:  # 第0天是警长竞选阶段
                sheriff_notice = (
                    "\n【警长竞选提示】现在是警长竞选阶段，请发表你的竞选演讲，表明你是否想要成为警长！"
                    "你可以阐述你的理由、策略以及为何你适合担任警长。"
                    "即使你不想竞选，也请说明你的考虑。这个发言所有人都会看到！\n"
                )
            
            # 获取警长竞选发言
            sheriff_speeches = ""
            if self.app.state.sheriff_id is not None:
                sheriff_speeches = f"**【当前警长】**: 玩家{self.app.state.sheriff_id}\n\n"
            
            if self.app.state.day == 0:  # 第0天是警长竞选阶段
                sheriff_speeches += self._read_sheriff_speeches()
                
            # 获取玩家自己的警长竞选投票
            player_sheriff_vote = ""
            if self.app.state.sheriff_id is not None:
                player_sheriff_vote = self._read_player_sheriff_vote(player_id)

            if player.identity == "平民":
                role_tip = (
                    "【提示-平民】作为平民，首要任务是存活！\n"
                    "结合已知信息，分析局势，找出最可疑的目标。\n"
                    "重点关注发言逻辑漏洞和行为异常的玩家。\n"
                    "尝试与可信角色（如预言家）建立联系，但注意不要暴露身份。\n"
                    "如果局势不明朗，选择保守发言，避免成为狼人首刀目标。\n"
                    "必要时可煽动其他玩家，形成对特定目标的压力。\n"
                    "⚠️ 请务必将你的发言控制在300字以内！"
                )
                # 在第一天时插入 day1_notice
                role_tip += day1_notice
                
                # 如果是警长竞选阶段，添加警长竞选提示
                role_tip += sheriff_notice
                
                # 获取警长特定提示
                sheriff_guidance = get_sheriff_guidance(player_id)
                
                # 在角色提示词前添加警长特定提示
                role_tip = sheriff_guidance + role_tip

                # 读取玩家自己所有的白天投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                history_votes = self._read_history_day_votes()
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          (f"**【你的警长竞选投票】**\n{player_sheriff_vote}\n" if player_sheriff_vote else "") +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          (f"**【警长竞选发言】**\n{sheriff_speeches}\n" if sheriff_speeches else "") +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix)

            elif player.identity == "狼人":
                role_tip = (
                    "【提示-狼人】隐藏你的狼人身份，伺机而动！\n"
                    "与同伴协同，制定战术，迷惑其他玩家。\n"
                    "尝试嫁祸好人，制造混乱，混淆视听。\n"
                    "利用反向思维，适时跳身份，扰乱预言家视线。\n"
                    "学会控制发言节奏，避免暴露过多信息。\n"
                    "若被怀疑，积极反驳，利用语言技巧摆脱嫌疑。\n"
                    "观察其他玩家表情和肢体语言，找出破绽。\n"
                    "⚠️ 请务必将你的发言控制在300字以内！"
                )
                # 在第一天时插入 day1_notice
                role_tip += day1_notice
                
                # 如果是警长竞选阶段，添加警长竞选提示
                role_tip += sheriff_notice
                
                # 获取警长特定提示
                sheriff_guidance = get_sheriff_guidance(player_id)
                
                # 在角色提示词前添加警长特定提示
                role_tip = sheriff_guidance + role_tip

                # 读取玩家自己所有的白天和夜晚投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                player_night_votes = self._read_player_history_night_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                history_votes = self._read_history_day_votes()
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚投票记录】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix)

            elif player.identity == "预言家":
                role_tip = (
                    "【提示-预言家】作为预言家，掌握重要信息，引领局势！\n"
                    "清晰表达查验结果，但注意避免过早暴露身份。\n"
                    "根据查验信息和发言表现推理玩家身份，排除狼人。\n"
                    "巧妙利用金水身份争取信任，巩固地位。\n"
                    "谨慎对待查杀，避免被狼人反噬。\n"
                    "如果身份暴露，考虑悍跳扰乱狼人节奏。\n"
                    "观察其他玩家反应，判断真假预言家。\n"
                    "⚠️ 请务必将你的发言控制在300字以内！"
                )
                # 在第一天时插入 day1_notice
                role_tip += day1_notice
                
                # 如果是警长竞选阶段，添加警长竞选提示
                role_tip += sheriff_notice
                
                # 获取警长特定提示
                sheriff_guidance = get_sheriff_guidance(player_id)
                
                # 在角色提示词前添加警长特定提示
                role_tip = sheriff_guidance + role_tip

                # 读取玩家自己所有的白天和夜晚投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                player_night_votes = self._read_player_history_night_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                check_record_content = self._read_check_record()
                check_info = f"**【当前查验信息 record/查验.txt 内容如下】**:\n{check_record_content}\n" \
                             f"**【查验信息结束】**\n"
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚投票记录(查验)】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          check_info +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix)

            elif player.identity == "猎人":
                role_tip = (
                    "【提示-猎人】作为猎人，你拥有死后带走一名玩家的能力！\n"
                    "**重要提示：如果你被淘汰，你可以选择带走一名玩家。**\n"
                    "结合已知信息，分析局势，找出最可疑的目标。\n"
                    "重点关注发言逻辑漏洞和行为异常的玩家。\n"
                    "如果局势不明朗，选择保守发言，避免成为狼人首刀目标。\n"
                    "建立与其他好人的信任关系，掩护可能的预言家。\n"
                    "⚠️ 请务必将你的发言控制在300字以内！"
                )
                # 在第一天时插入 day1_notice
                role_tip += day1_notice
                
                # 如果是警长竞选阶段，添加警长竞选提示
                role_tip += sheriff_notice
                
                # 获取警长特定提示
                sheriff_guidance = get_sheriff_guidance(player_id)
                
                # 在角色提示词前添加警长特定提示
                role_tip = sheriff_guidance + role_tip

                # 读取玩家自己所有的白天投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                history_votes = self._read_history_day_votes()
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix)

            elif player.identity == "女巫":
                role_tip = (
                    "【提示-女巫】作为女巫，你拥有救人和毒人的能力！\n"
                    "**重要提示：你在夜晚阶段可以通过投票按钮使用你的药水。**\n"
                    "- 救人药：点击投票选择当晚被狼人杀的人，可以将其救活（一局游戏只能用一次）\n"
                    "- 毒药：点击投票选择一名存活的人，可以将其毒死（一局游戏只能用一次）\n"
                    "结合已知信息，分析局势，找出最可疑的目标。\n"
                    "重点关注发言逻辑漏洞和行为异常的玩家。\n"
                    "如果局势不明朗，谨慎使用你的药，关键时刻才能发挥最大作用。\n"
                    "注意：只有你自己知道你救了谁或毒了谁，其他人不会得知。\n"
                    "⚠️ 请务必将你的发言控制在300字以内！"
                )
                # 在第一天时插入 day1_notice
                role_tip += day1_notice
                
                # 如果是警长竞选阶段，添加警长竞选提示
                role_tip += sheriff_notice
                
                # 获取警长特定提示
                sheriff_guidance = get_sheriff_guidance(player_id)
                
                # 在角色提示词前添加警长特定提示
                role_tip = sheriff_guidance + role_tip

                # 读取女巫的药水使用状态
                save_used = self.app.state.witch_save_used.get(player_id, False)
                poison_used = self.app.state.witch_poison_used.get(player_id, False)
                drug_status = f"**【女巫药水状态】**\n救人药：{'已使用' if save_used else '未使用'}\n毒药：{'已使用' if poison_used else '未使用'}\n"

                # 读取玩家自己所有的白天投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                # 读取玩家自己所有的夜晚投票记录（使用药水记录）
                player_night_votes = self._read_player_history_night_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                history_votes = self._read_history_day_votes()
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          drug_status +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚药水使用记录】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix)

            # 日志记录开始发言
            identity_display = player.identity if player.identity != "空" else "玩家"
            self.app.log_system(f"{identity_display} {player_id} 开始白天发言...")

        # 夜晚发言阶段（这里只考虑狼人发言；预言家夜晚发言由 VoteHandler 触发）
        else:  # 只有狼人在夜晚可以发言，且之前已经做过检查
            phase_indicator = "【当前阶段：夜晚发言阶段】\n"
            # 在 prompt 最前面添加"玩家X开始夜间发言..."
            start_line = f"玩家 {player_id} 开始夜间发言...\n"
            night_role_tip = (
                "【提示-夜晚狼人】作为狼人，现在是夜晚，你需要暗中传递策略信息！\n"
                "你需要与队友密切协作，共同分析局势并确定最佳击杀目标！\n"
                "请积极与队友沟通讨论，制定统一战略，你的发言仅供狼人参考，无需隐藏身份！\n"
                "注意：如果夜晚击杀得票数相同，则投票将无效，请务必提前协商好投票击杀对象！\n"
                "保持发言节奏紧凑，确保在300字以内，不暴露破绽。\n"
                "⚠️ 请务必将你的发言控制在300字以内！"
            )
            # 读取当前天数白天投票和所有历史投票
            player_day_votes = self._read_player_history_day_votes(player_id)
            player_night_votes = self._read_player_history_night_votes(player_id)
            teammates = [p.player_id for p in self.app.state.players.values() if p.identity == "狼人" and p.player_id != player_id]
            night_speeches_teammates = ""
            daytime_speeches = self._read_day_speeches()  # 获取白天发言
            history_speeches = self._read_history_day_speeches()
            history_night_speeches = self._read_history_night_speeches()
            for p_id in teammates:
                if self.app.state.players[p_id].speech_history and self.app.state.players[p_id].speech_history[-1]:
                    night_speeches_teammates += f"**队友玩家{p_id}**: {self.app.state.players[p_id].speech_history[-1]}\n\n"
            prompt = (start_line + common_prefix + phase_indicator + header_footer +
                      night_role_tip + "\n" +
                      f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                      f"**【你的历史夜晚投票记录】**\n{player_night_votes}\n" +
                      f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                      f"**【今晚队友发言】**:\n{night_speeches_teammates}\n" +
                      f"**【历史白天发言】**\n{history_speeches}\n" +
                      f"**【历史夜晚狼人发言】**\n{history_night_speeches}\n" +
                      f"**【历史遗言记录】**\n{last_words}\n" +
                      night_role_tip + footer + common_suffix)
            self.app.log_system(f"狼人 {player_id} 开始夜晚发言...")

        def speech_callback(final_answer_text):
            text_parsed = final_answer_text.replace("\\n", "\n")
            player.speech_history.append(text_parsed)
            if self.app.state.phase == "day":
                if self.app.state.day == 0:
                    save_sheriff_speech(player_id, self.app.state.day, text_parsed)
                else:
                    save_daytime_speech(player_id, self.app.state.day, text_parsed)
            else:
                save_night_speech(player_id, self.app.state.day, text_parsed)

            # 检查是否是猎人的遗言，如果是，处理带人逻辑
            if player.identity == "猎人" and not player.alive:
                # 用正则表达式匹配方括号中的数字，表示猎人要带走的玩家
                brackets_number = re.findall(r'\[(\d+)\]', text_parsed)
                
                # 也支持[随机]和[弃票]格式
                random_choice = re.findall(r'\[随机\]', text_parsed)
                abstain_choice = re.findall(r'\[弃票\]', text_parsed)
                
                target_player_id = None
                if brackets_number:
                    # 获取最后一个匹配的数字，即最终选择的玩家
                    target_id_str = brackets_number[-1]
                    try:
                        target_player_id = int(target_id_str)
                    except ValueError:
                        self.app.log_system(f"[警告] 无法解析猎人 {player_id} 的带人目标编号，带人作废。")
                elif random_choice:
                    # 从存活的非猎人玩家中随机选择一名
                    alive_players = [p_id for p_id, p in self.app.state.players.items() 
                                    if p.alive and p.exists and p_id != player_id]
                    if alive_players:
                        import random
                        target_player_id = random.choice(alive_players)
                        self.app.log_system(f"猎人 {player_id} 选择随机带人，系统选择了玩家 {target_player_id}")
                elif abstain_choice:
                    self.app.log_system(f"猎人 {player_id} 选择放弃带人")
                
                # 如果有有效的带人目标，执行带人逻辑
                if target_player_id is not None:
                    target_player = self.app.state.players.get(target_player_id)
                    if target_player and target_player.exists and target_player.alive:
                        # 将目标玩家标记为死亡
                        target_player.alive = False
                        self.app.state.dead_today.append(target_player_id)
                        self.app.state.current_day_summary["deaths"].append((target_player_id, "被猎人带走死亡"))
                        
                        # 更新UI，启用目标玩家的遗言按钮
                        self.app.ui_handler.app.lastword_buttons[target_player_id].config(state=tk.NORMAL)
                        
                        # 记录猎人带人
                        self.app.log_system(f"猎人 {player_id} 带走了玩家 {target_player_id}！")
                        self.app.summary_text.insert(tk.END, f"猎人玩家 {player_id} 带走了玩家 {target_player_id}！\n", f"p{player_id}")
                        self.app.summary_text.see(tk.END)
                        
                        # 刷新按钮状态，确保死亡玩家的遗言按钮可用
                        self.app.game_logic_handler.update_buttons_for_phase(self.app.state.phase)
                        
                        # 检查游戏是否结束
                        game_over, winner = self.app.state.check_game_over()
                        if game_over:
                            self.app.game_logic_handler.end_game(winner)
                    else:
                        self.app.log_system(f"[警告] 猎人 {player_id} 选择的带人目标 {target_player_id} 不存在或已死亡，带人作废。")

            # 根据 TTS 开关状态播放语音
            if self.app.tts_enabled:
                play_tts(text_parsed, player_id)

        self.model_handler.call_model(player.model, prompt, self.app.summary_text, tag=f"p{player_id}",
                                      callback=speech_callback, player_id=player_id)

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
                                self.app.log_system(f"[警告] 读取玩家 {p_id} 白天发言失败: {e}")
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
                                self.app.log_system(f"[警告] 读取玩家 {p_id} 历史白天发言失败: {e}")
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
                                self.app.log_system(f"[警告] 读取玩家 {p_id} 历史白天投票失败: {e}")
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
                                    self.app.log_system(f"[警告] 读取玩家 {p_id} 历史夜晚发言失败: {e}")
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
                                    self.app.log_system(f"[警告] 读取玩家 {p_id} 历史夜晚投票失败: {e}")
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
                                self.app.log_system(f"[警告] 读取玩家 {p_id} 警长竞选发言失败: {e}")
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
                    self.app.log_system(f"[警告] 读取玩家 {player_id} 警长竞选投票失败: {e}")
        return player_sheriff_vote
