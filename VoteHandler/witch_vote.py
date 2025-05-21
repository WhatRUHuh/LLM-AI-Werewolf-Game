# VoteHandler/witch_vote.py
import os

def generate_witch_night_action_prompt(handler, player, **prompt_params):
    """
    Generates prompt for Witch night action (save/poison).
    """
    header = prompt_params.get("header", "")
    footer = prompt_params.get("footer", "")
    common_prefix = prompt_params.get("common_prefix", "") # Will be adapted for witch
    common_suffix = prompt_params.get("common_suffix", "") # Will be adapted for witch
    last_words_content = prompt_params.get("last_words_content", "")

    phase_indicator = "【当前阶段：夜晚行动阶段 - 女巫请选择是否使用药水及目标】\n"
    start_line = f"玩家 {player.player_id} (女巫) 开始夜晚行动...\n"

    # Witch specific prefix/suffix
    witch_prefix = (
        "你是女巫，现在是夜晚行动阶段。你可以选择使用救人药或毒药（如果尚未使用）。\n"
        "返回格式应为 [玩家编号]（例如 [1]），或返回 [弃票] (或 [不使用]) 表示不使用药水。\n"
        "【注意】请务必将你的选择控制在300字以内！\n"
    )
    witch_suffix = (
        "\n【提醒】请保持选择简洁明了，限于300字以内。\n"
        "返回格式：[玩家编号] 或 [弃票]/[不使用]。"
    )

    player_day_votes = handler._read_player_history_day_votes(player.player_id)
    # Witch's "night votes" are their potion usage records
    player_night_potion_history = handler._read_player_history_night_votes(player.player_id) 
    daytime_speeches = handler._read_day_speeches() # Today's day speeches
    history_speeches = handler._read_history_day_speeches() # All historical day speeches

    # Witch specific: Potion status & Wolf target info
    save_used = handler.app.state.witch_save_used.get(player.player_id, False)
    poison_used = handler.app.state.witch_poison_used.get(player.player_id, False)
    drug_status = f"**【女巫药水状态】**\n救人药：{'已使用' if save_used else '未使用'}\n毒药：{'已使用' if poison_used else '未使用'}\n"

    wolf_target_id = handler.app.state.wolf_kill_target # This is the player ID the wolves targeted
    wolf_target_info = ""
    if wolf_target_id is not None:
        wolf_target_info = f"**【狼人今晚的击杀目标】**: 玩家 {wolf_target_id}\n"
        if not save_used:
            wolf_target_info += f"你可以输入 [{wolf_target_id}] 使用救人药救活玩家 {wolf_target_id}。\n"
    else:
        wolf_target_info = "**【狼人今晚的击杀情况】**: 狼人还没有确定击杀目标或投票无效。\n"
    
    if not poison_used:
        wolf_target_info += "你可以输入其他存活的 [玩家编号] 来使用毒药。\n"
    wolf_target_info += "如果不想使用任何药水，请输入 [弃票] 或 [不使用]。\n"


    alive_players_str = ', '.join([str(p.player_id) for p in handler.app.state.players.values() if p.exists and p.alive])
    # Valid targets for poison are all other alive players
    valid_poison_targets = [p.player_id for p in handler.app.state.players.values() if p.exists and p.alive and p.player_id != player.player_id]
    valid_poison_targets_str = ', '.join(map(str, valid_poison_targets))


    current_game_status_repeated = (
        f"**【游戏状态】**\n"
        f"当前天数：{handler.app.state.day}\n"
        f"存活玩家：{alive_players_str}\n"
        f"你的身份：{player.identity}\n"
        f"{drug_status}"
        f"今晚可下毒目标（若用毒药）：{valid_poison_targets_str if not poison_used else '毒药已使用'}\n"
    ) * 2
        
    role_tip = ("【提示-夜晚女巫】作为女巫，仔细判断局势！\n"
                f"{wolf_target_info}"
                "- 救人药：选择狼人当晚击杀的目标可救活（一局仅一次）。\n"
                "- 毒药：选择任一存活玩家可毒杀（一局仅一次）。\n"
                "谨慎使用你的药水，它们非常宝贵。")

    prompt = (start_line + witch_prefix + phase_indicator + header +
              role_tip + "\n" +
              drug_status +
              f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
              f"**【你的历史夜晚药水使用记录】**\n{player_night_potion_history}\n" +
              f"**【今日其他玩家白天发言】**\n{daytime_speeches}\n" +
              f"**【历史白天发言】**\n{history_speeches}\n" +
              f"**【历史遗言记录】**\n{last_words_content}\n" +
              role_tip + footer + witch_suffix + current_game_status_repeated +
              f"请选择你的行动（300字以内）：")
              
    return prompt
