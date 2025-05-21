# SpeechHandler/witch_speech.py
import os

def generate_witch_speech_prompt(handler, player, is_last_words, phase_indicator, start_line, **prompt_params):
    """
    Generates speech prompt for a Witch.
    """
    header = prompt_params.get("header", "")
    footer = prompt_params.get("footer", "")
    common_prefix = prompt_params.get("common_prefix", "")
    common_suffix = prompt_params.get("common_suffix", "")
    last_words_content = prompt_params.get("last_words_content", "")
    get_sheriff_guidance_func = prompt_params.get("get_sheriff_guidance_func", lambda x: "")

    player_day_votes = handler._read_player_history_day_votes(player.player_id)
    # Witch "votes" (uses potions) at night
    player_night_votes = handler._read_player_history_night_votes(player.player_id) 
    daytime_speeches = handler._read_day_speeches()
    history_speeches = handler._read_history_day_speeches()

    # Witch specific: Potion status
    save_used = handler.app.state.witch_save_used.get(player.player_id, False)
    poison_used = handler.app.state.witch_poison_used.get(player.player_id, False)
    drug_status = f"**【女巫药水状态】**\n救人药：{'已使用' if save_used else '未使用'}\n毒药：{'已使用' if poison_used else '未使用'}\n"

    alive_players_str = ', '.join([str(p.player_id) for p in handler.app.state.players.values() if p.exists and p.alive])
    current_game_status_repeated = (
        f"**【游戏状态】**\n"
        f"当前天数：{handler.app.state.day}\n"
        f"存活玩家：{alive_players_str}\n"
        f"你的身份：{player.identity}\n"
        f"{drug_status}" # Include potion status for witch
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
            "【提示-女巫】作为女巫，这是你最后的机会！\n"
            "在遗言中尝试传递你所知道的信息，特别是夜晚观察到的情况。\n"
            "如果你已经使用过解药或毒药，可以提示其他玩家你的行动。\n"
            "分析场上局势，给予其他好人建议，帮助他们找出狼人。\n"
            "如果你知道某些玩家的身份，可以在遗言中暗示或直接指出。\n"
            "尽量避免暴露其他身份不明的好人，以免对方被狼人针对。\n"
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
                  drug_status + # Witch specific
                  f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                  f"**【你的历史夜晚药水使用记录】**\n{player_night_votes}\n" +
                  f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                  f"**【历史白天发言】**\n{history_speeches}\n" +
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
            role_tip = "**【角色提示】**\n你是一个女巫，现在是警长竞选阶段。你需要通过发言来竞选警长。警长在白天投票时拥有1.5票的投票权。\n"
            sheriff_speeches_info = handler._read_sheriff_speeches()
        else: # Normal day speech
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
            if handler.app.state.sheriff_id is not None:
                 player_sheriff_vote_info = handler._read_player_sheriff_vote(player.player_id)

        role_tip += day1_notice
        role_tip += sheriff_notice
        sheriff_guidance = get_sheriff_guidance_func(player.player_id)
        role_tip = sheriff_guidance + role_tip

        prompt = (start_line + common_prefix + phase_indicator + header +
                  role_tip + "\n" +
                  drug_status + # Witch specific
                  f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
                  f"**【你的历史夜晚药水使用记录】**\n{player_night_votes}\n" +
                  (f"**【你的警长竞选投票】**\n{player_sheriff_vote_info}\n" if player_sheriff_vote_info else "") +
                  f"**【今日其他玩家发言】**\n{daytime_speeches}\n" +
                  (f"**【警长竞选发言】**\n{sheriff_speeches_info}\n" if sheriff_speeches_info else "") +
                  (f"**【警长信息】**\n{sheriff_info}\n" if handler.app.state.day > 0 and sheriff_info else "") +
                  f"**【历史白天发言】**\n{history_speeches}\n" +
                  f"**【历史遗言记录】**\n{last_words_content}\n" +
                  role_tip + footer + common_suffix + current_game_status_repeated +
                  "请发表你的发言（300字以内）：")
                  
    return prompt
