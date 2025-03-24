from record import save_daytime_speech, save_night_speech, save_sheriff_speech, save_last_words_record
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
        
    def reset_sheriff_speak_count(self):
        """重置警长发言计数，用于天数切换时调用"""
        self.sheriff_speak_count = {}
        self.app.log_system("已重置警长发言计数")

    def player_speak(self, player_id):
        player = self.app.state.players[player_id]
        
        # 只有两种情况会阻止玩家发言：
        # 1. 玩家不存在
        # 2. 活着的玩家在夜晚试图发言（除了狼人和预言家）
        if not player.exists:
            self.app.log_system(f"玩家 {player_id} 不存在，无法发言。")
            return
        
        # 检查是否是遗言发言
        is_last_words = not player.alive
        
        # 如果是活着的玩家在夜晚发言，检查身份
        if not is_last_words and self.app.state.phase == "night":
            if player.identity not in ["狼人", "预言家"]:
                self.app.log_system(f"玩家 {player_id} 在夜晚无法发言（身份：{player.identity}）。")
                return

        # 准备阶段提示信息
        if is_last_words:
            self.app.log_system(f"玩家 {player_id} 准备进行遗言发言...")
            
            # 如果是警长，添加警徽移交提示
            if player_id == self.app.state.sheriff_id:
                self.app.log_system(f"警长 {player_id} 可以在遗言中选择移交或销毁警徽")
                
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
        common_prefix = "【注意】请务必将你的发言控制在300字以内，以免耽误其他玩家的发言时间。\n【重要】你正在玩狼人杀游戏，白天发言的所有内容会被所有玩家看到！不要在白天发言中透露不想让其他玩家知道的信息，即使用括号()或其他方式标注，这些内容也会被所有人看到！\n"
        common_suffix = "\n提醒】请保持发言简洁明了，限于300字以内。\n【再次强调】白天的所有发言都是公开的，所有玩家都能看到！不要试图使用括号或任何标记方式隐藏信息！"

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
                    sheriff_guidance = (
                        "\n【警长提示】作为警长，你现在需要决定发言顺序！\n"
                        "【警长提示】你的发言顺序将直接影响到所有玩家的信息获取和判断，关乎这场游戏的胜负走向！\n"
                        "【警长提示】你要清晰你的目的！根据目的，合理安排发言顺序！\n"
                        "【警长提示】请结合自己的身份，确定好现在的白天发言顺序。\n"
                        "【警长提示】除此之外，你还要告诉大家为什么这么安排。\n"
                    )
                elif self.sheriff_speak_count[player_id] == 2:
                    sheriff_guidance = (
                        "\n【警长提示】现在是正常的发言阶段！\n"
                        "【警长提示】作为警长，你的发言具有更高的权威性和影响力。\n"
                        "【警长提示】请认真思考你的身份和立场，发表自己的见解。\n"
                        "【警长提示】你可以结合之前玩家的发言，进行分析和推理。\n"
                    )
                elif self.sheriff_speak_count[player_id] >= 3:
                    sheriff_guidance = (
                        "\n【警长提示】请对今天所有人的发言进行总结！\n"
                        "【警长提示】这是你今天最后的发言机会，请充分利用！\n"
                        "【警长提示】分析各位玩家的发言逻辑和可信度，提出你的判断。\n"
                        "【警长提示】为大家提供一个有价值的信息框架，帮助投票决策。\n"
                        "【警长提示】你的总结将极大影响今天的投票结果，请慎重！\n"
                    )
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
                
                # 如果是警长，添加警徽移交提示
                if player_id == self.app.state.sheriff_id:
                    role_tip += (
                        "\n【警长提示】作为警长，你可以在遗言中选择将警徽传递给其他玩家或销毁警徽。\n"
                        "- 传递警徽：在遗言中使用[警徽给X]或【警徽给X】格式（X为玩家编号）\n"
                        "- 销毁警徽：在遗言中使用[销毁警徽]或【销毁警徽】\n"
                        "如果不做选择，警徽将自动销毁。\n"
                    )
                
                # 读取玩家自己所有的白天投票记录，而不仅仅是前一天的
                player_day_votes = self._read_player_history_day_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                history_votes = self._read_history_day_votes()
                
                # 添加警长历史信息
                sheriff_info = ""
                if self.app.state.sheriff_id is not None:
                    sheriff_info = f"**【当前警长】**: 玩家{self.app.state.sheriff_id}\n\n"
                if self.app.state.sheriff_history:
                    sheriff_info += "**【警长历史】**:\n"
                    for sheriff_id, action in self.app.state.sheriff_history:
                        sheriff_info += f"玩家{sheriff_id}：{action}警徽\n"
                
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          (f"**【警长信息】**\n{sheriff_info}\n" if sheriff_info else "") +
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
                
                # 如果是警长，添加警徽移交提示
                if player_id == self.app.state.sheriff_id:
                    role_tip += (
                        "\n【警长提示】作为警长，你可以在遗言中选择将警徽传递给其他玩家或销毁警徽。\n"
                        "- 传递警徽：在遗言中使用[警徽给X]或【警徽给X】格式（X为玩家编号）\n"
                        "- 销毁警徽：在遗言中使用[销毁警徽]或【销毁警徽】\n"
                        "如果不做选择，警徽将自动销毁。\n"
                    )
                
                # 读取玩家自己所有的白天和夜晚投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                player_night_votes = self._read_player_history_night_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                history_night_speeches = self._read_history_night_speeches()
                
                # 添加警长历史信息
                sheriff_info = ""
                if self.app.state.sheriff_id is not None:
                    sheriff_info = f"**【当前警长】**: 玩家{self.app.state.sheriff_id}\n\n"
                if self.app.state.sheriff_history:
                    sheriff_info += "**【警长历史】**:\n"
                    for sheriff_id, action in self.app.state.sheriff_history:
                        sheriff_info += f"玩家{sheriff_id}：{action}警徽\n"
                
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚投票记录】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史夜晚狼人发言】**\n{history_night_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          (f"**【警长信息】**\n{sheriff_info}\n" if sheriff_info else "") +
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
                
                # 如果是警长，添加警徽移交提示
                if player_id == self.app.state.sheriff_id:
                    role_tip += (
                        "\n【警长提示】作为警长，你可以在遗言中选择将警徽传递给其他玩家或销毁警徽。\n"
                        "- 传递警徽：在遗言中使用[警徽给X]或【警徽给X】格式（X为玩家编号）\n"
                        "- 销毁警徽：在遗言中使用[销毁警徽]或【销毁警徽】\n"
                        "如果不做选择，警徽将自动销毁。\n"
                    )
                
                # 读取玩家自己所有的白天和夜晚投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                player_night_votes = self._read_player_history_night_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                check_record_content = self._read_check_record()
                check_info = f"**【当前查验信息 record/查验.txt 内容如下】**:\n{check_record_content}\n" \
                             f"**【查验信息结束】**\n"
                
                # 添加警长历史信息
                sheriff_info = ""
                if self.app.state.sheriff_id is not None:
                    sheriff_info = f"**【当前警长】**: 玩家{self.app.state.sheriff_id}\n\n"
                if self.app.state.sheriff_history:
                    sheriff_info += "**【警长历史】**:\n"
                    for sheriff_id, action in self.app.state.sheriff_history:
                        sheriff_info += f"玩家{sheriff_id}：{action}警徽\n"
                
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【你的历史夜晚投票记录(查验)】**\n{player_night_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          check_info +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          (f"**【警长信息】**\n{sheriff_info}\n" if sheriff_info else "") +
                          role_tip + footer + common_suffix)

            elif player.identity == "猎人":
                start_line = f"玩家 {player_id} 开始发表遗言并准备带走一名玩家...\n"
                role_tip = (
                    "【猎人提示】作为猎人，你拥有死后带走一名玩家的能力！\n"
                    "**重要：作为猎人，你可以在死亡时带走一名玩家。请在遗言的同时选择你想带走的玩家！**\n"
                    "结合已知信息，分析局势，找出最可疑的目标。\n"
                    "重点关注发言逻辑漏洞和行为异常的玩家。\n"
                    "如果确定了狼人身份，请优先带走狼人。\n"
                    "若局势不明朗，可做出保守选择或做出战略性带人。\n"
                    "**在遗言结束后，请像投票一样用[玩家编号]格式指定你要带走的人，或者输入[随机]或[弃票]。**\n"
                    "⚠️ 请务必将你的遗言控制在300字以内！"
                )
                
                # 如果是警长，添加警徽移交提示
                if player_id == self.app.state.sheriff_id:
                    role_tip += (
                        "\n【警长提示】作为警长，你可以在遗言中选择将警徽传递给其他玩家或销毁警徽。\n"
                        "- 传递警徽：在遗言中使用[警徽给X]或【警徽给X】格式（X为玩家编号）\n"
                        "- 销毁警徽：在遗言中使用[销毁警徽]或【销毁警徽】\n"
                        "如果不做选择，警徽将自动销毁。\n"
                    )
                
                # 读取玩家自己所有的白天投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                history_votes = self._read_history_day_votes()
                
                # 添加警长历史信息
                sheriff_info = ""
                if self.app.state.sheriff_id is not None:
                    sheriff_info = f"**【当前警长】**: 玩家{self.app.state.sheriff_id}\n\n"
                if self.app.state.sheriff_history:
                    sheriff_info += "**【警长历史】**:\n"
                    for sheriff_id, action in self.app.state.sheriff_history:
                        sheriff_info += f"玩家{sheriff_id}：{action}警徽\n"
                
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                        role_tip + "\n" +
                        f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                        f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                        f"**【历史白天发言】**\n{history_speeches}\n" +
                        f"**【历史遗言记录】**\n{last_words}\n" +
                        (f"**【警长信息】**\n{sheriff_info}\n" if sheriff_info else "") +
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
                
                # 如果是警长，添加警徽移交提示
                if player_id == self.app.state.sheriff_id:
                    role_tip += (
                        "\n【警长提示】作为警长，你可以在遗言中选择将警徽传递给其他玩家或销毁警徽。\n"
                        "- 传递警徽：在遗言中使用[警徽给X]或【警徽给X】格式（X为玩家编号）\n"
                        "- 销毁警徽：在遗言中使用[销毁警徽]或【销毁警徽】\n"
                        "如果不做选择，警徽将自动销毁。\n"
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
                
                # 添加警长历史信息
                sheriff_info = ""
                if self.app.state.sheriff_id is not None:
                    sheriff_info = f"**【当前警长】**: 玩家{self.app.state.sheriff_id}\n\n"
                if self.app.state.sheriff_history:
                    sheriff_info += "**【警长历史】**:\n"
                    for sheriff_id, action in self.app.state.sheriff_history:
                        sheriff_info += f"玩家{sheriff_id}：{action}警徽\n"
                
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                        role_tip + "\n" +
                        drug_status +
                        f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                        f"**【你的历史夜晚药水使用记录】**\n{player_night_votes}\n" +
                        f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                        f"**【历史白天发言】**\n{history_speeches}\n" +
                        f"**【历史遗言记录】**\n{last_words}\n" +
                        (f"**【警长信息】**\n{sheriff_info}\n" if sheriff_info else "") +
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
            if self.app.state.day == 0:  # 第0天是警长竞选阶段
                sheriff_speeches = self._read_sheriff_speeches()
                # 添加警长竞选阶段的特殊提示
                phase_indicator = "**【当前阶段】**\n警长竞选阶段\n"
                # 添加警长竞选阶段的特殊提示
                if player.identity == "平民":
                    role_tip = "**【角色提示】**\n你是一个平民，现在是警长竞选阶段。你需要通过发言来竞选警长。警长在白天投票时拥有1.5票的投票权。\n"
                elif player.identity == "狼人":
                    role_tip = "**【角色提示】**\n你是一个狼人，现在是警长竞选阶段。你需要通过发言来竞选警长。警长在白天投票时拥有1.5票的投票权。\n"
                elif player.identity == "预言家":
                    role_tip = "**【角色提示】**\n你是一个预言家，现在是警长竞选阶段。你需要通过发言来竞选警长。警长在白天投票时拥有1.5票的投票权。\n"
                elif player.identity == "猎人":
                    role_tip = "**【角色提示】**\n你是一个猎人，现在是警长竞选阶段。你需要通过发言来竞选警长。警长在白天投票时拥有1.5票的投票权。\n"
                elif player.identity == "女巫":
                    role_tip = "**【角色提示】**\n你是一个女巫，现在是警长竞选阶段。你需要通过发言来竞选警长。警长在白天投票时拥有1.5票的投票权。\n"
            else:
                phase_indicator = "**【当前阶段】**\n白天发言阶段\n"
                if self.app.state.sheriff_id is not None:
                    sheriff_speeches = f"**【当前警长】**: 玩家{self.app.state.sheriff_id}\n\n"
            
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

                # 获取存活玩家列表
                alive_players = [i for i, p in self.app.state.players.items() if p.exists and p.alive and i != player_id]

                # 读取玩家自己所有的白天投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                history_votes = self._read_history_day_votes()
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n"
                          + (f"**【你的警长竞选投票】**\n{player_sheriff_vote}\n" if player_sheriff_vote else "") +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n"
                          + (f"**【警长竞选发言】**\n{sheriff_speeches}\n" if sheriff_speeches else "") +
                          f"**【历史白天发言】**\n{history_speeches}\n"
                          + f"**【历史遗言记录】**\n{last_words}\n"
                          + role_tip + footer + common_suffix +
                          f"\n**【游戏状态】**\n"
                          f"当前天数：{self.app.state.day}\n"
                          f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
                          f"你的身份：{player.identity}\n"
                          f"**【游戏状态】**\n"
                          f"当前天数：{self.app.state.day}\n"
                          f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
                          f"你的身份：{player.identity}\n"
                          f"请发表你的发言（300字以内）：")

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

                # 获取存活玩家列表
                alive_players = [i for i, p in self.app.state.players.items() if p.exists and p.alive and i != player_id]

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
                          role_tip + footer + common_suffix +
                          f"\n**【游戏状态】**\n"
                          f"当前天数：{self.app.state.day}\n"
                          f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
                          f"你的身份：{player.identity}\n"
                          f"**【游戏状态】**\n"
                          f"当前天数：{self.app.state.day}\n"
                          f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
                          f"你的身份：{player.identity}\n"
                          f"请发表你的发言（300字以内）：")

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

                # 获取存活玩家列表
                alive_players = [i for i, p in self.app.state.players.items() if p.exists and p.alive and i != player_id]

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
                          (f"**【警长竞选发言】**\n{sheriff_speeches}\n" if sheriff_speeches else "") +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          check_info +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix +
                          f"\n**【游戏状态】**\n"
                          f"当前天数：{self.app.state.day}\n"
                          f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
                          f"你的身份：{player.identity}\n"
                          f"**【游戏状态】**\n"
                          f"当前天数：{self.app.state.day}\n"
                          f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
                          f"你的身份：{player.identity}\n"
                          f"请发表你的发言（300字以内）：")

            elif player.identity == "猎人":
                role_tip = (
                    "【猎人提示】作为猎人，你可以在遗言中选择带走一名玩家！\n"
                    "使用以下任意格式：\n"
                    "[开枪X]或【开枪X】（X为玩家编号）\n"
                    "- [带走X]或【带走X】\n"
                    "- 直接说开枪X或带走X\n"
                    "如果不做选择，将不会带走任何玩家。\n"
                )
                # 在第一天时插入 day1_notice
                role_tip += day1_notice
                
                # 如果是警长竞选阶段，添加警长竞选提示
                role_tip += sheriff_notice
                
                # 获取警长特定提示
                sheriff_guidance = get_sheriff_guidance(player_id)
                
                # 在角色提示词前添加警长特定提示
                role_tip = sheriff_guidance + role_tip

                # 获取存活玩家列表
                alive_players = [i for i, p in self.app.state.players.items() if p.exists and p.alive and i != player_id]

                # 读取玩家自己所有的白天投票记录
                player_day_votes = self._read_player_history_day_votes(player_id)
                daytime_speeches = self._read_day_speeches()
                history_speeches = self._read_history_day_speeches()
                history_votes = self._read_history_day_votes()
                prompt = (start_line + common_prefix + phase_indicator + header_footer +
                          role_tip + "\n" +
                          f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                          f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                          (f"**【警长竞选发言】**\n{sheriff_speeches}\n" if sheriff_speeches else "") +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix +
                          f"\n**【游戏状态】**\n"
                          f"当前天数：{self.app.state.day}\n"
                          f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
                          f"你的身份：{player.identity}\n"
                          f"**【游戏状态】**\n"
                          f"当前天数：{self.app.state.day}\n"
                          f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
                          f"你的身份：{player.identity}\n"
                          f"请发表你的发言（300字以内）：")

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

                # 获取存活玩家列表
                alive_players = [i for i, p in self.app.state.players.items() if p.exists and p.alive and i != player_id]

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
                          (f"**【警长竞选发言】**\n{sheriff_speeches}\n" if sheriff_speeches else "") +
                          f"**【历史白天发言】**\n{history_speeches}\n" +
                          f"**【历史遗言记录】**\n{last_words}\n" +
                          role_tip + footer + common_suffix +
                          f"\n**【游戏状态】**\n"
                          f"当前天数：{self.app.state.day}\n"
                          f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
                          f"你的身份：{player.identity}\n"
                          f"**【游戏状态】**\n"
                          f"当前天数：{self.app.state.day}\n"
                          f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
                          f"你的身份：{player.identity}\n"
                          f"请发表你的发言（300字以内）：")

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
            # 获取存活玩家列表
            alive_players = [i for i, p in self.app.state.players.items() if p.exists and p.alive and i != player_id]
            
            # 读取当前天数白天投票和所有历史投票
            player_day_votes = self._read_player_history_day_votes(player_id)
            player_night_votes = self._read_player_history_night_votes(player_id)
            teammates = [p.player_id for p in self.app.state.players.values() if p.identity == "狼人" and p.player_id != player_id]
            night_speeches_teammates = ""
            daytime_speeches = self._read_day_speeches()  # 获取白天发言
            history_speeches = self._read_history_day_speeches()
            history_night_speeches = self._read_history_night_speeches()
            
            # 获取当前狼人队友夜晚发言的逻辑 - 从文件中读取
            for p_id in teammates:
                # 确认队友玩家是存活的狼人
                teammate = self.app.state.players.get(p_id)
                if teammate and teammate.alive and teammate.identity == "狼人":
                    # 在record目录中查找当前夜晚该队友的发言
                    import os
                    teammate_speech = ""
                    night_speech_path = os.path.join("record", f"第{self.app.state.day}天", "夜晚玩家发言", f"玩家{p_id}夜晚发言.txt")
                    if os.path.exists(night_speech_path):
                        try:
                            with open(night_speech_path, "r", encoding="utf-8") as f:
                                teammate_speech = f.read().strip()
                                if teammate_speech:
                                    night_speeches_teammates += f"**队友玩家{p_id}**: {teammate_speech}\n\n"
                        except Exception as e:
                            self.app.log_system(f"[警告] 读取队友玩家 {p_id} 夜晚发言失败: {e}")
            
            # 如果没有找到任何队友发言，添加说明
            if not night_speeches_teammates:
                night_speeches_teammates = "目前没有队友发言记录。\n"
                
            prompt = (start_line + common_prefix + phase_indicator + header_footer +
                      night_role_tip + "\n" +
                      f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                      f"**【你的历史夜晚投票记录】**\n{player_night_votes}\n" +
                      f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                      f"**【今晚队友发言】**:\n{night_speeches_teammates}\n" +
                      f"**【历史白天发言】**\n{history_speeches}\n" +
                      f"**【历史夜晚狼人发言】**\n{history_night_speeches}\n" +
                      f"**【历史遗言记录】**\n{last_words}\n" +
                      night_role_tip + footer + common_suffix +
                      f"\n**【游戏状态】**\n"
                      f"当前天数：{self.app.state.day}\n"
                      f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
                      f"你的身份：{player.identity}\n"
                      f"**【游戏状态】**\n"
                      f"当前天数：{self.app.state.day}\n"
                      f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
                      f"你的身份：{player.identity}\n"
                      f"请发表你的发言（300字以内）：")
            self.app.log_system(f"狼人 {player_id} 开始夜晚发言...")

        def speech_callback(final_answer_text):
            text_parsed = final_answer_text.replace("\\n", "\n")
            
            # 保存发言到文件
            if self.app.state.phase == "day":
                save_daytime_speech(player_id, self.app.state.day, text_parsed)
            else:
                save_night_speech(player_id, self.app.state.day, text_parsed)
            
            # 在游戏摘要中显示发言
            self.app.summary_text.insert(tk.END, f"玩家 {player_id} 的发言：\n", f"p{player_id}")
            self.app.summary_text.insert(tk.END, f"{text_parsed}\n\n", f"p{player_id}")
            self.app.summary_text.see(tk.END)
            
            # 根据 TTS 开关状态播放语音
            if self.app.tts_enabled:
                play_tts(text_parsed, player_id, self.app.tts_speed)

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
                                self.app.log_system(f"[警告] 读取玩家 {p_id} 历史白天发言失败: {e}")
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
                                self.app.log_system(f"[警告] 读取玩家 {p_id} 历史白天投票失败: {e}")
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
                                    self.app.log_system(f"[警告] 读取玩家 {p_id} 历史夜晚发言失败: {e}")
                if day_speeches:
                    history_speeches += f"**第{day}天夜晚狼人发言:**\n{day_speeches}\n"
        
        return history_speeches
    
    def _read_history_night_votes(self):
        """读取历史天数的狼人夜晚投票（仅适用于狼人玩家）"""
        history_votes = ""
        record_root = "record"
        current_day = self.app.state.day
        
        # 从第0天到当前天数-1，读取所有历史投票
        for day in range(0, current_day):
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
        
        # 从第0天到当前天数-1，读取所有历史投票
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
                        self.app.log_system(f"[警告] 读取玩家 {player_id} 第{day}天白天投票失败: {e}")
        
        return player_history_votes

    # 新增读取玩家自己所有历史夜晚投票的方法
    def _read_player_history_night_votes(self, player_id):
        """读取特定玩家历史天数的所有夜晚投票"""
        player_history_votes = ""
        record_root = "record"
        current_day = self.app.state.day
        
        # 从第0天到当前天数-1，读取所有历史投票
        for day in range(0, current_day):
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
        # 读取特定玩家的警长投票记录
        try:
            voting_content = ""
            day_vote_reasoning = get_day_vote_reasoning_player(player_id, 0)
            if day_vote_reasoning:
                voting_content += f"玩家 {player_id} 的警长投票结果: {day_vote_reasoning}\n"
            return voting_content
        except Exception as e:
            self.app.log_system(f"读取警长投票记录时出错: {e}")
            return "没有警长投票记录。\n"

    def _read_last_words(self):
        # 读取所有历史遗言记录
        try:
            last_words_content = ""
            if os.path.exists("record/遗言"):
                for filename in os.listdir("record/遗言"):
                    if filename.endswith(".txt"):
                        player_id = filename.split("_")[0]
                        day = filename.split("_")[1].split(".")[0]
                        with open(f"record/遗言/{filename}", "r", encoding="utf-8") as f:
                            content = f.read().strip()
                            last_words_content += f"【玩家{player_id}】第{day}天遗言:\n{content}\n\n"
            return last_words_content if last_words_content else "没有历史遗言记录。\n"
        except Exception as e:
            self.app.log_system(f"读取遗言记录时出错: {e}")
            return "读取遗言记录时出错。\n"
            
    def prepare_last_words(self, player_id):
        """准备玩家遗言"""
        player = self.app.state.players[player_id]
        
        # 检查玩家是否存在且已死亡
        if not player.exists or player.alive:
            self.app.log_system(f"[错误] 玩家 {player_id} 不存在或未死亡，无法发表遗言")
            return
        
        # 记录玩家身份信息
        identity_info = f"你的身份是：{player.identity}"
        
        # 构建历史死亡信息
        death_history = "【历史死亡玩家】\n"
        for day, summary in enumerate(self.app.state.history):
            if summary.get("deaths"):
                death_history += f"第{day}天：\n"
                for pid, cause in summary.get("deaths", []):
                    death_history += f"玩家{pid}（{self.app.state.players[pid].identity}）{cause}\n"
        
        # 添加今天死亡的玩家信息
        if self.app.state.current_day_summary.get("deaths"):
            death_history += f"第{self.app.state.day}天：\n"
            for pid, cause in self.app.state.current_day_summary.get("deaths", []):
                if pid != player_id:  # 不包括当前玩家自己
                    death_history += f"玩家{pid}（{self.app.state.players[pid].identity}）{cause}\n"
        
        # 构建当前游戏状态信息
        game_state_info = "【当前游戏状态】\n"
        alive_players = [i for i, p in self.app.state.players.items() if p.exists and p.alive and i != player_id]
        game_state_info += f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
        
        # 根据身份提供不同的提示
        identity_tip = ""
        
        # 检查是否是警长
        is_sheriff = player_id == self.app.state.sheriff_id
        sheriff_tip = ""
        if is_sheriff:
            sheriff_tip = (
                "【警长提示】你是当前的警长。在遗言中，你可以选择将警徽传递给其他玩家或销毁警徽。\n"
                "- 传递警徽：在遗言中使用[警徽给X]或【警徽给X】格式（X为玩家编号），或直接说'警徽给X'\n"
                "- 销毁警徽：在遗言中使用[销毁警徽]或【销毁警徽】，或直接说'销毁警徽'\n"
                "如果不做选择，警徽将自动销毁。\n"
                )

        
        # 通用遗言提示
        last_words_tip = (
            "【遗言提示】这是你在游戏中的最后发言机会，请充分利用这个机会！\n"
            "你可以揭示自己的身份，分享你对局势的看法，或者为同阵营的玩家提供建议。\n"
            "请保持发言简洁明了，控制在300字以内。\n"
            "⚠️ 请务必将你的发言控制在300字以内！"
        )
        
        # 根据不同身份提供特定提示
        if player.identity == "平民":
            identity_tip = (
                "【平民提示】作为平民，你的遗言可以帮助其他平民找出狼人！\n"
                "分享你的怀疑对象和推理过程，这对存活的平民非常有价值。\n"
                "如果你有关于某些玩家身份的确定信息，请务必在遗言中说明。\n"
            )
        elif player.identity == "狼人":
            identity_tip = (
                "【狼人提示】作为狼人，你的遗言可以帮助其他狼人！\n"
                "你可以尝试误导好人，或者为其他狼人提供信息。\n"
                "但请注意，不要过于明显地暴露身份。\n"
            )
        elif player.identity == "预言家":
            identity_tip = (
                "【预言家提示】作为预言家，你的遗言可以分享你的查验信息！\n"
                "你可以告诉其他玩家你查验过的玩家身份，这对好人阵营很有帮助。\n"
                "但请注意，不要过于明显地暴露身份。\n"
            )
        elif player.identity == "猎人":
            identity_tip = (
                "【猎人提示】作为猎人，你可以在遗言中选择带走一名玩家！\n"
                "使用以下任意格式：\n"
                "[开枪X]或【开枪X】（X为玩家编号）\n"
                "- [带走X]或【带走X】\n"
                "- 直接说开枪X或带走X\n"
                "如果不做选择，将不会带走任何玩家。\n"
            )
        elif player.identity == "女巫":
            identity_tip = (
                "【女巫提示】作为女巫，你的遗言可以帮助其他好人！\n"
                "你可以分享你对局势的看法，或者为其他玩家提供建议。\n"
                "但请注意，不要过于明显地暴露身份。\n"
            )
        
        # 检查是否是警长，如果是，添加警长提示
        if player_id == self.app.state.sheriff_id:
            sheriff_tip = (
                "\n【警长提示】作为警长，你可以在遗言中选择将警徽传递给其他玩家或销毁警徽。\n"
                "请在遗言中使用以下格式之一：\n"
                "- [警徽给X] 或 【警徽给X】（X为玩家编号）\n"
                "- [销毁警徽] 或 【销毁警徽】\n"
                "如果不做选择，警徽将自动销毁。\n"
            )
            # 将警长提示添加到身份提示中
            identity_tip += sheriff_tip
        
        # 读取玩家的投票历史
        player_day_votes = self._read_player_history_day_votes(player_id)
        player_night_votes = self._read_player_history_night_votes(player_id)
        
        # 读取当前天数的所有玩家发言
        daytime_speeches = self._read_day_speeches()
        
        # 读取历史天数的所有玩家发言
        history_speeches = self._read_history_day_speeches()
        
        # 读取历史天数的所有玩家投票
        history_votes = self._read_history_day_votes()
        
        # 读取历史遗言
        last_words = self._read_last_words()
        
        # 警长历史记录
        sheriff_history = "【警长历史记录】\n"
        for sheriff_id, action in self.app.state.sheriff_history:
            sheriff_history += f"玩家{sheriff_id}：{action}警徽\n"
        if not self.app.state.sheriff_history:
            sheriff_history += "无警长记录\n"
        
        # 构建完整的提示信息
        prompt = (
            f"玩家 {player_id} 开始发表遗言...\n\n"
            f"【当前阶段：遗言阶段】\n"
            f"{identity_info}\n\n"
            f"{death_history}\n"
            f"{game_state_info}\n"
            f"{sheriff_history}\n"
            f"{sheriff_tip if is_sheriff else ''}"
            f"{identity_tip}\n"
            f"{last_words_tip}\n\n"
            f"**【你的历史白天投票记录】**\n{player_day_votes}\n"
            f"**【你的历史夜晚投票记录】**\n{player_night_votes}\n"
            f"**【今日其他玩家发言】**\n{daytime_speeches}\n"
            f"**【历史白天发言】**\n{history_speeches}\n"
            f"**【历史白天投票】**\n{history_votes}\n"
            f"**【历史遗言记录】**\n{last_words}\n"
            f"{last_words_tip}\n"
            f"**【游戏状态】**\n"
            f"当前天数：{self.app.state.day}\n"
            f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
            f"你的身份：{player.identity}\n"
            f"**【游戏状态】**\n"
            f"当前天数：{self.app.state.day}\n"
            f"存活玩家：{', '.join([str(p_id) for p_id in alive_players])}\n"
            f"你的身份：{player.identity}\n"
            f"请发表你的遗言（300字以内）："
        )
        
        self.app.log_system(f"玩家 {player_id} 开始发表遗言...")
        
        def last_words_callback(final_answer_text):
            text_parsed = final_answer_text.replace("\\n", "\n")
            
            # 检查是否是警长
            if is_sheriff:
                # 检查警徽传递
                sheriff_transfer = re.search(r'\[警徽给(?:玩家)?(\d+)\]|【警徽给(?:玩家)?(\d+)】|警徽给(?:玩家)?(\d+)', text_parsed)
                if sheriff_transfer:
                    target_id = int(sheriff_transfer.group(1) or sheriff_transfer.group(2) or sheriff_transfer.group(3))
                    if target_id in self.app.state.players and self.app.state.players[target_id].exists and self.app.state.players[target_id].alive:
                        self.app.state.sheriff_id = target_id
                        self.app.log_system(f"警长 {player_id} 将警徽传递给了玩家 {target_id}")
                        self.app.summary_text.insert(tk.END, f"警长 {player_id} 将警徽传递给了玩家 {target_id}\n", f"p{player_id}")
                        self.app.summary_text.see(tk.END)
                        # 更新UI中的警长标签显示
                        self.app.ui_handler.update_sheriff_labels()
                    else:
                        self.app.log_system(f"警长 {player_id} 尝试将警徽传递给无效的玩家 {target_id}，警徽将被销毁")
                
                # 检查警徽销毁
                sheriff_destroy = re.search(r'\[销毁警徽\]|【销毁警徽】|销毁警徽', text_parsed)
                if sheriff_destroy:
                    self.app.state.sheriff_id = None
                    self.app.log_system(f"警长 {player_id} 销毁了警徽")
                    self.app.summary_text.insert(tk.END, f"警长 {player_id} 销毁了警徽\n", f"p{player_id}")
                    self.app.summary_text.see(tk.END)
                    # 更新UI中的警长标签显示
                    self.app.ui_handler.update_sheriff_labels()
            
            # 检查是否是猎人
            if player.identity == "猎人":
                # 检查开枪带走
                hunter_shot = re.search(r'\[开枪(?:玩家)?(\d+)\]|【开枪(?:玩家)?(\d+)】|开枪(?:玩家)?(\d+)|\[带走(?:玩家)?(\d+)\]|【带走(?:玩家)?(\d+)】|带走(?:玩家)?(\d+)', text_parsed)
                if hunter_shot:
                    target_player_id = int(hunter_shot.group(1) or hunter_shot.group(2) or hunter_shot.group(3) or 
                                          hunter_shot.group(4) or hunter_shot.group(5) or hunter_shot.group(6))
                    
                    target_player = self.app.state.players.get(target_player_id)
                    if target_player and target_player.exists and target_player.alive:
                        # 开枪击杀目标
                        target_player.alive = False
                        target_player.death_reason = "被猎人开枪击杀"
                        target_player.death_day = self.app.state.day
                        
                        # 更新死亡记录
                        self.app.state.dead_today.append(target_player_id)
                        self.app.state.current_day_summary["deaths"].append((target_player_id, "被猎人带走"))
                        
                        # 更新UI显示死亡状态
                        self.app.ui_handler.update_player_status()
                        
                        # 记录开枪击杀
                        self.app.log_system(f"猎人 {player_id} 开枪击杀了玩家 {target_player_id}！")
                        self.app.summary_text.insert(tk.END, f"猎人玩家 {player_id} 开枪击杀了玩家 {target_player_id}！\n", f"p{player_id}")
                        self.app.summary_text.see(tk.END)
                        
                        # 启用遗言按钮
                        self.app.lastword_buttons[target_player_id].config(state=tk.NORMAL)
                        
                        # 检查游戏是否结束
                        game_over, winner = self.app.state.check_game_over()
                        if game_over:
                            self.app.game_logic_handler.end_game(winner)
                    else:
                        self.app.log_system(f"[警告] 猎人 {player_id} 选择的开枪目标 {target_player_id} 不存在或已死亡。")
                else:
                    self.app.log_system(f"猎人 {player_id} 没有选择开枪目标。")
            
            # 保存遗言记录
            save_last_words_record(player_id, self.app.state.day, player.death_reason or "未知原因", text_parsed)
            
            # 根据 TTS 开关状态播放语音
            if self.app.tts_enabled:
                play_tts(text_parsed, player_id, self.app.tts_speed)
        
        self.model_handler.call_model(player.model, prompt, self.app.summary_text, tag=f"p{player_id}",
                                      callback=last_words_callback, player_id=player_id)
