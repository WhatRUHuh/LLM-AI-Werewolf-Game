# SpeechHandler/seer_speech.py
import os

def generate_seer_speech_prompt(handler, player, is_last_words, phase_indicator, start_line, **prompt_params):
    """
    Generates speech prompt for a Seer.
    """
    header = prompt_params.get("header", "")
    footer = prompt_params.get("footer", "")
    common_prefix = prompt_params.get("common_prefix", "")
    common_suffix = prompt_params.get("common_suffix", "")
    last_words_content = prompt_params.get("last_words_content", "")
    get_sheriff_guidance_func = prompt_params.get("get_sheriff_guidance_func", lambda x: "")

    player_day_votes = handler._read_player_history_day_votes(player.player_id)
    # Seers "vote" (check) at night, this is their action record
    player_night_votes = handler._read_player_history_night_votes(player.player_id) 
    daytime_speeches = handler._read_day_speeches()
    history_speeches = handler._read_history_day_speeches()
    
    check_record_content = handler._read_check_record() # Specific to Seer
    check_info = f"**【当前查验信息 record/查验.txt 内容如下】**:\n{check_record_content}\n**【查验信息结束】**\n"

    alive_players_str = ', '.join([str(p.player_id) for p in handler.app.state.players.values() if p.exists and p.alive])
    current_game_status_repeated = (
        f"**【游戏状态】**\n"
        f"当前天数：{handler.app.state.day}\n"
        f"存活玩家：{alive_players_str}\n"
        f"你的身份：{player.identity}\n"
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
            "【提示-预言家】作为预言家，这是你最后留下关键信息的机会！\n"
            "清晰表达查验结果，但要谨慎措辞，防止狼人利用。\n"
            "根据查验信息和发言表现推理玩家身份，排除狼人。\n"
            "巧妙利用金水身份争取信任，巩固地位。\n"
            "若身份暴露，可考虑悍跳扰乱狼人节奏。\n"
            "观察其他玩家反应，判断真假预言家。\n"
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
                  f"**【你的历史夜晚投票记录(查验)】**\n{player_night_votes}\n" +
                  f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                  f"**【历史白天发言】**\n{history_speeches}\n" +
                  check_info + # Seer specific
                  f"**【历史遗言记录】**\n{last_words_content}\n" +
                  (f"**【警长信息】**\n{sheriff_info}\n" if sheriff_info else "") +
                  role_tip + footer + common_suffix + current_game_status_repeated +
                  "请发表你的遗言（300字以内）：")
    else: # Alive and speaking (daytime)
        day1_notice = ""
        if handler.app.state.day == 1:
            day1_notice = (
                "\n【注意-第一天白天】现在这是第一天游戏刚开始，现在是游戏的第一个阶段，"
                "现在没有人被投票放逐，没有人被狼人杀死，没人被预言家查明身份。\n"
            )

        sheriff_notice = ""
        sheriff_speeches_info = ""
        player_sheriff_vote_info = ""

        if handler.app.state.day == 0: # Sheriff election
            sheriff_notice = (
                "\n【警长竞选提示】现在是警长竞选阶段，请发表你的竞选演讲，表明你是否想要成为警长！"
                "你可以阐述你的理由、策略以及为何你适合担任警长。"
                "即使你不想竞选，也请说明你的考虑。这个发言所有人都会看到！\n"
            )
            role_tip = "**【角色提示】**\n你是一个预言家，现在是警长竞选阶段。你需要通过发言来竞选警长。警长在白天投票时拥有1.5票的投票权。\n"
            sheriff_speeches_info = handler._read_sheriff_speeches()
        else: # Normal day speech
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
            if handler.app.state.sheriff_id is not None:
                 player_sheriff_vote_info = handler._read_player_sheriff_vote(player.player_id)

        role_tip += day1_notice
        role_tip += sheriff_notice
        sheriff_guidance = get_sheriff_guidance_func(player.player_id)
        role_tip = sheriff_guidance + role_tip

        prompt = (start_line + common_prefix + phase_indicator + header +
                  role_tip + "\n" +
                  f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                  f"**【你的历史夜晚投票记录(查验)】**\n{player_night_votes}\n" +
                  (f"**【你的警长竞选投票】**\n{player_sheriff_vote_info}\n" if player_sheriff_vote_info else "") +
                  f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                  (f"**【警长竞选发言】**\n{sheriff_speeches_info}\n" if sheriff_speeches_info else "") +
                  (f"**【警长信息】**\n{sheriff_info}\n" if handler.app.state.day > 0 and sheriff_info else "") +
                  f"**【历史白天发言】**\n{history_speeches}\n" +
                  check_info + # Seer specific
                  f"**【历史遗言记录】**\n{last_words_content}\n" +
                  role_tip + footer + common_suffix + current_game_status_repeated +
                  "请发表你的发言（300字以内）：")
                  
    return prompt
