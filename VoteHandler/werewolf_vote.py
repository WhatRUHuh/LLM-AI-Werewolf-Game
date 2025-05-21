# VoteHandler/werewolf_vote.py
import os

def generate_werewolf_night_vote_prompt(handler, player, **prompt_params):
    """
    Generates prompt for Werewolf night voting (kill).
    """
    header = prompt_params.get("header", "")
    footer = prompt_params.get("footer", "")
    common_prefix = prompt_params.get("common_prefix", "") # Night-specific prefix might be needed
    common_suffix = prompt_params.get("common_suffix", "") # Night-specific suffix might be needed
    last_words_content = prompt_params.get("last_words_content", "")

    phase_indicator = "【当前阶段：夜晚投票阶段 - 狼人请选择击杀目标】\n"
    start_line = f"玩家 {player.player_id} (狼人) 开始夜晚投票...\n"

    # Night-specific prefix/suffix for werewolves
    night_common_prefix = (
        "你们是狼人阵营，需要合力击杀一名好人阵营的玩家。\n"
        "投票给已死亡或不存在的玩家将视为空票。\n"
        "返回格式应为 [玩家编号]（例如 [1]），或返回 随机 或 弃票 分别代表随机投票或弃票。\n"
        "如果夜晚击杀票数相同，则投票无效，请务必提前协商好投票击杀对象！\n"
        "【注意】请务必将你的投票控制在300字以内！\n"
    )
    night_common_suffix = (
        "\n【提醒】请保持投票内容简洁明了，限于300字以内。\n"
        "如果夜晚击杀票数相同，则投票无效！"
    )

    player_day_votes = handler._read_player_history_day_votes(player.player_id)
    # For werewolves, their "night votes" are kill targets.
    player_night_kill_history = handler._read_player_history_night_votes(player.player_id) 
    daytime_speeches = handler._read_day_speeches() # Today's day speeches
    history_speeches = handler._read_history_day_speeches() # All historical day speeches
    history_night_speeches = handler._read_history_night_speeches() # Werewolf team's historical night speeches

    teammates = [p.player_id for p in handler.app.state.players.values() if p.identity == "狼人" and p.player_id != player.player_id]
    
    # Get teammates' night speeches from the current night
    current_night_teammate_speeches = ""
    for p_id in teammates:
        teammate_player = handler.app.state.players.get(p_id)
        if teammate_player and teammate_player.alive and teammate_player.identity == "狼人":
            night_speech_path = os.path.join("record", f"第{handler.app.state.day}天", "夜晚玩家发言", f"玩家{p_id}夜晚发言.txt")
            if os.path.exists(night_speech_path):
                try:
                    with open(night_speech_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            current_night_teammate_speeches += f"**队友玩家{p_id}今晚发言**: {content}\n\n"
                except Exception as e:
                    handler.app.ui_handler.log_system(f"[警告] 读取队友玩家 {p_id} 夜晚发言失败: {e}")
    if not current_night_teammate_speeches:
        current_night_teammate_speeches = "目前没有队友今晚的发言记录。\n"

    alive_players_str = ', '.join([str(p.player_id) for p in handler.app.state.players.values() if p.exists and p.alive])
    # Filter out fellow werewolves from the list of valid targets
    valid_targets = [p.player_id for p in handler.app.state.players.values() if p.exists and p.alive and p.identity != "狼人"]
    valid_targets_str = ', '.join(map(str, valid_targets))

    current_game_status_repeated = (
        f"**【游戏状态】**\n"
        f"当前天数：{handler.app.state.day}\n"
        f"存活玩家：{alive_players_str}\n"
        f"你的身份：{player.identity}\n"
        f"狼人队友：{teammates}\n"
        f"今晚有效击杀目标（非狼人）：{valid_targets_str}\n"
    ) * 2
    
    role_tip = ("【提示-夜晚狼人】作为狼人，现在是夜晚，请结合所有已知信息（当日白天投票总结、其他玩家发言及遗言记录、队友发言），"
                "做出你的投票选择，目标仅限非狼人。务必说明理由，并确保投票内容控制在300字以内！")

    prompt = (start_line + night_common_prefix + phase_indicator + header +
              role_tip + "\n" +
              f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
              f"**【你的历史夜晚击杀投票记录】**\n{player_night_kill_history}\n" +
              f"**【今日其他玩家白天发言】**\n{daytime_speeches}\n" +
              f"**【今晚队友发言】**\n{current_night_teammate_speeches}\n" +
              f"**【历史白天发言】**\n{history_speeches}\n" +
              f"**【历史夜晚狼人发言】**\n{history_night_speeches}\n" + # Historical night speeches of the team
              f"**【历史遗言记录】**\n{last_words_content}\n" +
              role_tip + footer + night_common_suffix + current_game_status_repeated +
              f"请从以下有效目标中选择击杀对象：{valid_targets_str}。请发表你的投票（300字以内）：")
              
    return prompt
