#!/usr/bin/env python
#log.py
# -*- coding: utf-8 -*-

import os

def log_to_file(player_id, prompt=None, output=None):
    """
    将指定玩家的 prompt 和输出写入日志文件
    日志文件存放在 log 文件夹下，文件名为 player{player_id}.log
    """
    if player_id < 1 or player_id > 10:
        return  # 只记录1~10号玩家日志
    log_folder = "log"
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    filename = os.path.join(log_folder, f"player{player_id}.log")
    with open(filename, "a", encoding="utf-8") as f:
        if prompt:
            f.write(f"Prompt: {prompt}\n")
        if output:
            f.write(f"Output: {output}\n")
        f.write("\n")
