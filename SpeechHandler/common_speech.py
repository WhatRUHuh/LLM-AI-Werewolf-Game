# SpeechHandler/common_speech.py
import os

def generate_common_speech_prompt(handler, player, is_last_words, phase_indicator, start_line, **prompt_params):
    """
    Generates speech prompt for a Commoner (平民) or as a fallback.
    Uses **kwargs to capture all parameters passed from prompt_params.
    """
    # Extract necessary parameters from prompt_params, providing defaults if necessary
    header = prompt_params.get("header", "")
    footer = prompt_params.get("footer", "")
    common_prefix = prompt_params.get("common_prefix", "")
    common_suffix = prompt_params.get("common_suffix", "")
    history_info_formatted = prompt_params.get("history_info_formatted", "")
    game_state_info = prompt_params.get("game_state_info", "")
    last_words_content = prompt_params.get("last_words_content", "")
    get_sheriff_guidance_func = prompt_params.get("get_sheriff_guidance_func", lambda x: "")
    
    # Role-specific data (can be further refined)
    player_day_votes = handler._read_player_history_day_votes(player.player_id)
    daytime_speeches = handler._read_day_speeches() # Current day's speeches
    history_speeches = handler._read_history_day_speeches() # All historical day speeches
    # history_votes = handler._read_history_day_votes() # All historical day votes (full file content)
    
    sheriff_info = ""
    if handler.app.state.sheriff_id is not None:
        sheriff_info = f"**【当前警长】**: 玩家{handler.app.state.sheriff_id}\n\n"
    if handler.app.state.sheriff_history:
        sheriff_info += "**【警长历史】**:\n"
        for sid, action in handler.app.state.sheriff_history:
            sheriff_info += f"玩家{sid}：{action}警徽\n"

    alive_players_str = ', '.join([str(p.player_id) for p in handler.app.state.players.values() if p.exists and p.alive])
    current_game_status_repeated = (
        f"**【游戏状态】**\n"
        f"当前天数：{handler.app.state.day}\n"
        f"存活玩家：{alive_players_str}\n"
        f"你的身份：{player.identity}\n"
    ) * 2


    if is_last_words:
        role_tip = (
            "【提示-平民】作为平民，这是你最后的机会！\n"
            "结合已知信息，分析局势，找出最可疑的目标。\n"
            "重点关注发言逻辑漏洞和行为异常的玩家。\n"
            "尝试与可信角色（如预言家）建立联系，但注意不要暴露身份。\n"
            "如果局势不明朗，选择保守发言，避免让狼人得利。\n"
            "必要时可煽动其他玩家形成对特定目标的压力。\n"
            "⚠️ 请务必将你的遗言控制在300字以内！"
        )
        if player.player_id == handler.app.state.sheriff_id: # Check if the current player is the sheriff
            role_tip += (
                "\n【警长提示】作为警长，你可以在遗言中选择将警徽传递给其他玩家或销毁警徽。\n"
                "- 传递警徽：在遗言中使用[警徽给X]或【警徽给X】格式（X为玩家编号）\n"
                "- 销毁警徽：在遗言中使用[销毁警徽]或【销毁警徽】\n"
                "如果不做选择，警徽将自动销毁。\n"
            )
        
        prompt = (start_line + common_prefix + phase_indicator + header +
                  role_tip + "\n" +
                  f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                  f"**【今日其他玩家发言】**\n{daytime_speeches}\n" + # Current day's speeches
                  f"**【历史白天发言】**\n{history_speeches}\n" + # All historical day speeches
                  f"**【历史遗言记录】**\n{last_words_content}\n" +
                  (f"**【警长信息】**\n{sheriff_info}\n" if sheriff_info else "") +
                  role_tip + footer + common_suffix + current_game_status_repeated +
                  "请发表你的遗言（300字以内）：")
    else: # Not last words (i.e., alive and speaking)
        # Day speaking
        day1_notice = ""
        if handler.app.state.day == 1:
            day1_notice = (
                "\n【注意-第一天白天】现在这是第一天游戏刚开始，现在是游戏的第一个阶段，"
                "现在没有人被投票放逐，没有人被狼人杀死，没人被预言家查明身份。\n"
            )
        
        sheriff_notice = ""
        sheriff_speeches_info = "" # For警长竞选发言
        player_sheriff_vote_info = "" # For 你的警长竞选投票

        if handler.app.state.day == 0: # Sheriff election phase
            sheriff_notice = (
                "\n【警长竞选提示】现在是警长竞选阶段，请发表你的竞选演讲，表明你是否想要成为警长！"
                "你可以阐述你的理由、策略以及为何你适合担任警长。"
                "即使你不想竞选，也请说明你的考虑。这个发言所有人都会看到！\n"
            )
            role_tip = "**【角色提示】**\n你是一个平民，现在是警长竞选阶段。你需要通过发言来竞选警长。警长在白天投票时拥有1.5票的投票权。\n"
            sheriff_speeches_info = handler._read_sheriff_speeches() # Get sheriff campaign speeches
        else: # Normal day speech
            role_tip = (
                "【提示-平民】作为平民，首要任务是存活！\n"
                "结合已知信息，分析局势，找出最可疑的目标。\n"
                "重点关注发言逻辑漏洞和行为异常的玩家。\n"
                "尝试与可信角色（如预言家）建立联系，但注意不要暴露身份。\n"
                "如果局势不明朗，选择保守发言，避免成为狼人首刀目标。\n"
                "必要时可煽动其他玩家，形成对特定目标的压力。\n"
                "⚠️ 请务必将你的发言控制在300字以内！"
            )
            if handler.app.state.sheriff_id is not None: # If sheriff is elected
                 player_sheriff_vote_info = handler._read_player_sheriff_vote(player.player_id)


        role_tip += day1_notice
        role_tip += sheriff_notice
        
        sheriff_guidance = get_sheriff_guidance_func(player.player_id)
        role_tip = sheriff_guidance + role_tip

        prompt = (start_line + common_prefix + phase_indicator + header +
                  role_tip + "\n" +
                  f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                  (f"**【你的警长竞选投票】**\n{player_sheriff_vote_info}\n" if player_sheriff_vote_info else "") +
                  f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                  (f"**【警长竞选发言】**\n{sheriff_speeches_info}\n" if sheriff_speeches_info else "") +
                  (f"**【警长信息】**\n{sheriff_info}\n" if handler.app.state.day > 0 and sheriff_info else "") +
                  f"**【历史白天发言】**\n{history_speeches}\n" +
                  f"**【历史遗言记录】**\n{last_words_content}\n" +
                  role_tip + footer + common_suffix + current_game_status_repeated +
                  "请发表你的发言（300字以内）：")
                  
    return prompt

# Add similar functions for other roles or specific scenarios if needed.
# For example, a generic night speech prompt if a non-wolf/non-seer tries to speak at night
# (though current logic in SpeechHandler prevents this).
