# VoteHandler/seer_vote.py
import os

def generate_seer_night_check_prompt(handler, player, **prompt_params):
    """
    Generates prompt for Seer night check.
    """
    header = prompt_params.get("header", "")
    footer = prompt_params.get("footer", "")
    # Seer's check is a targeted action, not a free-form text, so prefix/suffix are more directive.
    common_prefix = (
        "你是预言家，现在是夜晚查验阶段。请选择一名玩家进行查验以得知其身份。\n"
        "返回格式应为 [玩家编号]（例如 [1]）。\n"
        "【注意】请务必将你的选择控制在300字以内！\n"
    )
    common_suffix = (
        "\n【提醒】请保持选择简洁明了，限于300字以内。\n"
        "返回格式应为 [玩家编号]（例如 [1]）。"
    )
    last_words_content = prompt_params.get("last_words_content", "")

    phase_indicator = "【当前阶段：夜晚查验阶段 - 预言家请选择查验目标】\n"
    start_line = f"玩家 {player.player_id} (预言家) 开始夜晚查验...\n"

    player_day_votes = handler._read_player_history_day_votes(player.player_id)
    # Seer's "night votes" are their previous checks
    player_night_checks_history = handler._read_player_history_night_votes(player.player_id) 
    daytime_speeches = handler._read_day_speeches() # Today's day speeches
    history_speeches = handler._read_history_day_speeches() # All historical day speeches
    
    check_record_content = handler._read_check_record() # All previous checks by any seer
    check_info = f"**【所有历史查验信息 record/查验.txt 内容如下】**:\n{check_record_content}\n**【查验信息结束】**\n"

    alive_players_str = ', '.join([str(p.player_id) for p in handler.app.state.players.values() if p.exists and p.alive])
    # Seers can check anyone alive, including themselves (though usually not strategic)
    valid_targets = [p.player_id for p in handler.app.state.players.values() if p.exists and p.alive]
    valid_targets_str = ', '.join(map(str, valid_targets))

    current_game_status_repeated = (
        f"**【游戏状态】**\n"
        f"当前天数：{handler.app.state.day}\n"
        f"存活玩家：{alive_players_str}\n"
        f"你的身份：{player.identity}\n"
        f"今晚可查验目标：{valid_targets_str}\n"
    ) * 2
        
    role_tip = ("【提示-夜晚预言家】作为预言家，现在是夜晚查验阶段，请结合所有已知信息（当日白天投票总结、其他玩家发言、你过往的查验信息及遗言记录），"
                "做出你认为最合理的查验选择，并务必简单说明理由。请注意保持隐晦，确保查验内容控制在300字以内！")

    prompt = (start_line + common_prefix + phase_indicator + header +
              role_tip + "\n" +
              f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
              f"**【你的历史夜晚查验记录】**\n{player_night_checks_history}\n" +
              f"**【今日其他玩家白天发言】**\n{daytime_speeches}\n" +
              f"**【历史白天发言】**\n{history_speeches}\n" +
              check_info + # All seer checks
              f"**【历史遗言记录】**\n{last_words_content}\n" +
              role_tip + footer + common_suffix + current_game_status_repeated +
              f"请从以下有效目标中选择查验对象：{valid_targets_str}。请发表你的选择（300字以内）：")
              
    return prompt
