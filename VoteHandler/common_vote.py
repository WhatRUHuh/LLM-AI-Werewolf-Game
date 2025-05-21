# VoteHandler/common_vote.py
import os

def generate_daytime_vote_prompt(handler, player, **prompt_params):
    """
    Generates prompt for daytime voting, including sheriff election.
    This is used by most roles during the day.
    """
    header = prompt_params.get("header", "")
    footer = prompt_params.get("footer", "")
    common_prefix = prompt_params.get("common_prefix", "")
    common_suffix = prompt_params.get("common_suffix", "")
    last_words_content = prompt_params.get("last_words_content", "") # Changed from last_words to last_words_content

    player_day_votes = handler._read_player_history_day_votes(player.player_id)
    daytime_speeches = handler._read_day_speeches() # Current day's speeches
    history_speeches = handler._read_history_day_speeches() # All historical day speeches
    
    # Determine phase and set phase-specific parameters
    if handler.app.state.day == 0:  # 第0天是警长竞选阶段
        phase_indicator = "【当前阶段：警长竞选投票阶段】\n"
        start_line = f"玩家 {player.player_id} 开始警长竞选投票...\n"
    else:
        phase_indicator = "【当前阶段：白天投票阶段】\n"
        start_line = f"玩家 {player.player_id} 开始投票...\n"

    # 获取警长竞选提示
    sheriff_vote_notice = ""
    if handler.app.state.day == 0:  # 第0天是警长竞选阶段
        sheriff_vote_notice = (
            "\n【警长竞选投票提示】现在是警长竞选投票阶段，请投票选出你认为最适合担任警长的玩家！"
            "得票最多的玩家将成为警长。请考虑每位玩家的竞选发言，并做出你的选择。\n"
        )

    # 获取警长竞选发言 (only relevant for day 0)
    sheriff_campaign_speeches = ""
    if handler.app.state.day == 0:
        sheriff_campaign_speeches = handler._read_sheriff_speeches()

    # 获取玩家自己的警长竞选投票 (only relevant if sheriff is already elected, i.e. day > 0)
    # This seems a bit mixed up in the original logic, as sheriff vote happens on day 0.
    # For day 0, there's no "player_sheriff_vote" yet.
    # For day > 0, sheriff_vote_notice and sheriff_campaign_speeches are not relevant.
    player_sheriff_vote_history = ""
    if handler.app.state.day > 0 and handler.app.state.sheriff_id is not None: # If sheriff is elected
         player_sheriff_vote_history = handler._read_player_sheriff_vote(player.player_id)


    # Default role_tip for common players (villagers)
    if handler.app.state.day == 0: # Sheriff election phase
        role_tip = (f"【提示-{player.identity}】作为{player.identity}，请结合所有玩家的竞选发言，"
                   f"选出你认为最适合担任警长的玩家，并务必说明理由。请注意隐藏身份，确保投票内容控制在300字以内！")
        role_tip += sheriff_vote_notice
    else: # Normal daytime voting
        role_tip = (f"【提示-{player.identity}】作为{player.identity}，请结合所有已知信息（历史死亡、游戏状态、前一日投票总结、其他玩家发言及遗言记录），"
                    "做出你认为最合理的投票选择，并务必说明理由。请注意隐藏身份，确保投票内容控制在300字以内！")
        # Specific additions for roles if necessary (though this is "common_vote")
        if player.identity == "猎人":
             role_tip += "\n记住你死亡时可以带走一名玩家。"
        elif player.identity == "女巫":
            save_used = handler.app.state.witch_save_used.get(player.player_id, False)
            poison_used = handler.app.state.witch_poison_used.get(player.player_id, False)
            drug_status = f"**【女巫药水状态】**\n救人药：{'已使用' if save_used else '未使用'}\n毒药：{'已使用' if poison_used else '未使用'}\n"
            role_tip = drug_status + role_tip + "\n记住你可以在关键时刻使用药水。"


    alive_players_str = ', '.join([str(p.player_id) for p in handler.app.state.players.values() if p.exists and p.alive])
    current_game_status_repeated = (
        f"**【游戏状态】**\n"
        f"当前天数：{handler.app.state.day}\n"
        f"存活玩家：{alive_players_str}\n"
        f"你的身份：{player.identity}\n"
    ) * 2
    
    prompt = (start_line + common_prefix + phase_indicator + header +
              role_tip + "\n" +
              f"**【你的历史白天投票记录】**\n{player_day_votes}\n" +
              (f"**【你的警长竞选投票记录】**\n{player_sheriff_vote_history}\n" if player_sheriff_vote_history else "") +
              f"**【今日其他玩家发言】**:\n{daytime_speeches}\n" +
              (f"**【警长竞选发言】**\n{sheriff_campaign_speeches}\n" if handler.app.state.day == 0 and sheriff_campaign_speeches else "") +
              f"**【历史白天发言】**\n{history_speeches}\n" +
              f"**【历史遗言记录】**:\n{last_words_content}\n" +
              role_tip + footer + common_suffix + current_game_status_repeated +
              "请发表你的投票（300字以内）：")
              
    return prompt
