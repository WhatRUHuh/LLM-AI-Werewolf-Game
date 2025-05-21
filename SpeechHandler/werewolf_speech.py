# SpeechHandler/werewolf_speech.py
import os

def generate_werewolf_speech_prompt(handler, player, is_last_words, phase_indicator, start_line, **prompt_params):
    """
    Generates speech prompt for a Werewolf.
    """
    header = prompt_params.get("header", "")
    footer = prompt_params.get("footer", "")
    common_prefix = prompt_params.get("common_prefix", "")
    common_suffix = prompt_params.get("common_suffix", "")
    last_words_content = prompt_params.get("last_words_content", "")
    get_sheriff_guidance_func = prompt_params.get("get_sheriff_guidance_func", lambda x: "")

    player_day_votes = handler._read_player_history_day_votes(player.player_id)
    player_night_votes = handler._read_player_history_night_votes(player.player_id) # Werewolves vote at night
    daytime_speeches = handler._read_day_speeches()
    history_speeches = handler._read_history_day_speeches()
    history_night_speeches = handler._read_history_night_speeches() # Werewolves see their own night speech

    teammates = [p.player_id for p in handler.app.state.players.values() if p.identity == "狼人" and p.player_id != player.player_id]
    alive_players_str = ', '.join([str(p.player_id) for p in handler.app.state.players.values() if p.exists and p.alive])
    
    current_game_status_repeated = (
        f"**【游戏状态】**\n"
        f"当前天数：{handler.app.state.day}\n"
        f"存活玩家：{alive_players_str}\n"
        f"你的身份：{player.identity}\n"
        f"狼人队友：{teammates}\n" 
    ) * 2

    sheriff_info = ""
    if handler.app.state.sheriff_id is not None:
        sheriff_info = f"**【当前警长】**: 玩家{handler.app.state.sheriff_id}\n\n"
    if handler.app.state.sheriff_history:
        sheriff_info += "**【警长历史】**:\n"
        for sid, action in handler.app.state.sheriff_history:
            sheriff_info += f"玩家{sid}：{action}警徽\n"

    if is_last_words:
        role_tip = (
            "【提示-狼人】作为狼人，这是你最后的机会！\n"
            "隐藏你的狼人身份，伺机而动！\n"
            "在遗言中制造混乱，避免暴露队友信息。\n"
            "适当嫁祸好人，迷惑其他玩家，使他们怀疑错误目标。\n"
            "利用反向思维暗示他人攻击可信好人。\n"
            "若身份已暴露，试图虚假爆料，引导错误方向。\n"
            "⚠️ 请务必将你的遗言控制在300字以内！"
        )
        if player.player_id == handler.app.state.sheriff_id:
            role_tip += (
                "\n【警长提示】作为警长，你可以在遗言中选择将警徽传递给其他玩家或销毁警徽。\n"
                "- 传递警徽：在遗言中使用[警徽给X]或【警徽给X】格式（X为玩家编号）\n"
                "- 销毁警徽：在遗言中使用[销毁警徽]或【销毁警徽】\n"
                "如果不做选择，警徽将自动销毁。\n"
            )
        
        prompt = (start_line + common_prefix + phase_indicator + header +
                  role_tip + "\n" +
                  f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                  f"**【你的历史夜晚投票记录】**\n{player_night_votes}\n" +
                  f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                  f"**【历史白天发言】**\n{history_speeches}\n" +
                  f"**【历史夜晚狼人发言】**\n{history_night_speeches}\n" + # Relevant for werewolves
                  f"**【历史遗言记录】**\n{last_words_content}\n" +
                  (f"**【警长信息】**\n{sheriff_info}\n" if sheriff_info else "") +
                  # f"**【队友信息】狼人队友：{teammates}**\n" + # Already in header/extra_info for werewolves
                  role_tip + footer + common_suffix + current_game_status_repeated +
                  "请发表你的遗言（300字以内）：")
    else: # Alive and speaking
        day1_notice = ""
        if handler.app.state.day == 1:
            day1_notice = (
                "\n【注意-第一天白天】现在这是第一天游戏刚开始，现在是游戏的第一个阶段，"
                "现在没有人被投票放逐，没有人被狼人杀死，没人被预言家查明身份。\n"
            )
        
        sheriff_notice = ""
        sheriff_speeches_info = ""
        player_sheriff_vote_info = ""

        if handler.app.state.phase == "day":
            if handler.app.state.day == 0: # Sheriff election
                sheriff_notice = (
                    "\n【警长竞选提示】现在是警长竞选阶段，请发表你的竞选演讲，表明你是否想要成为警长！"
                    "你可以阐述你的理由、策略以及为何你适合担任警长。"
                    "即使你不想竞选，也请说明你的考虑。这个发言所有人都会看到！\n"
                )
                role_tip = "**【角色提示】**\n你是一个狼人，现在是警长竞选阶段。你需要通过发言来竞选警长。警长在白天投票时拥有1.5票的投票权。\n"
                sheriff_speeches_info = handler._read_sheriff_speeches()
            else: # Normal day speech
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
                if handler.app.state.sheriff_id is not None:
                     player_sheriff_vote_info = handler._read_player_sheriff_vote(player.player_id)
            
            role_tip += day1_notice
            role_tip += sheriff_notice
            sheriff_guidance = get_sheriff_guidance_func(player.player_id)
            role_tip = sheriff_guidance + role_tip

            prompt = (start_line + common_prefix + phase_indicator + header +
                      role_tip + "\n" +
                      f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                      f"**【你的历史夜晚投票记录】**\n{player_night_votes}\n" +
                      (f"**【你的警长竞选投票】**\n{player_sheriff_vote_info}\n" if player_sheriff_vote_info else "") +
                      f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                      (f"**【警长竞选发言】**\n{sheriff_speeches_info}\n" if sheriff_speeches_info else "") +
                      (f"**【警长信息】**\n{sheriff_info}\n" if handler.app.state.day > 0 and sheriff_info else "") +
                      f"**【历史白天发言】**\n{history_speeches}\n" +
                      f"**【历史夜晚狼人发言】**\n{history_night_speeches}\n" +
                      f"**【历史遗言记录】**\n{last_words_content}\n" +
                      # f"**【队友信息】狼人队友：{teammates}**\n" + # Already in header/extra_info
                      role_tip + footer + common_suffix + current_game_status_repeated +
                      "请发表你的发言（300字以内）：")
        else: # Night (Werewolf specific night speech)
            night_role_tip = (
                "【提示-夜晚狼人】作为狼人，现在是夜晚，你需要暗中传递策略信息！\n"
                "你需要与队友密切协作，共同分析局势并确定最佳击杀目标！\n"
                "请积极与队友沟通讨论，制定统一战略，你的发言仅供狼人参考，无需隐藏身份！\n"
                "注意：如果夜晚击杀得票数相同，则投票将无效，请务必提前协商好投票击杀对象！\n"
                "保持发言节奏紧凑，确保在300字以内，不暴露破绽。\n"
                "⚠️ 请务必将你的发言控制在300字以内！"
            )
            
            night_speeches_teammates = ""
            for p_id in teammates:
                teammate_player = handler.app.state.players.get(p_id)
                if teammate_player and teammate_player.alive and teammate_player.identity == "狼人":
                    night_speech_path = os.path.join("record", f"第{handler.app.state.day}天", "夜晚玩家发言", f"玩家{p_id}夜晚发言.txt")
                    if os.path.exists(night_speech_path):
                        try:
                            with open(night_speech_path, "r", encoding="utf-8") as f:
                                content = f.read().strip()
                                if content:
                                    night_speeches_teammates += f"**队友玩家{p_id}**: {content}\n\n"
                        except Exception as e:
                            handler.app.ui_handler.log_system(f"[警告] 读取队友玩家 {p_id} 夜晚发言失败: {e}")
            if not night_speeches_teammates:
                night_speeches_teammates = "目前没有队友发言记录。\n"

            prompt = (start_line + common_prefix + phase_indicator + header + # common_prefix for night might be too restrictive, but keeping for now
                      night_role_tip + "\n" +
                      f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                      f"**【你的历史夜晚投票记录】**\n{player_night_votes}\n" +
                      f"**【今日其他玩家发言】**\n{daytime_speeches}\n" + # Day speeches from today
                      f"**【今晚队友发言】**:\n{night_speeches_teammates}\n" +
                      f"**【历史白天发言】**\n{history_speeches}\n" +
                      f"**【历史夜晚狼人发言】**\n{history_night_speeches}\n" + # Historical night speeches
                      f"**【历史遗言记录】**\n{last_words_content}\n" +
                      # f"**【队友信息】狼人队友：{teammates}**\n" + # Already in header/extra_info
                      night_role_tip + footer + common_suffix + current_game_status_repeated +
                      "请发表你的发言（300字以内）：")
                      
    return prompt
