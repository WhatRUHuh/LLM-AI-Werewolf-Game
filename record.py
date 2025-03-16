# record.py
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

def create_record_folder():
    """创建记录文件夹 'record'（若不存在），同时创建查验.txt 文件"""
    if not os.path.exists("record"):
        os.makedirs("record")
    # 创建查验.txt 文件（如果不存在）
    check_file = os.path.join("record", "查验.txt")
    if not os.path.exists(check_file):
        with open(check_file, "w", encoding="utf-8") as f:
            f.write("**【查验记录】**\n") #  ✨✨✨  修改查验.txt 初始内容， 加上标题！ ✨✨✨
            # f.write("**查验信息初始内容**\n") #  ❌❌❌  旧的初始内容， 删除! ❌❌❌

def create_day_record_folder(day):
    """
    为指定天数创建文件夹结构：
      record/第{day}天/白天玩家发言
      record/第{day}天/白天玩家投票
      record/第{day}天/夜晚玩家发言
      record/第{day}天/夜晚玩家投票
    """
    record_folder = "record"
    day_folder = os.path.join(record_folder, f"第{day}天")
    for subfolder in ("白天玩家发言", "白天玩家投票", "夜晚玩家发言", "夜晚玩家投票"):
        folder = os.path.join(day_folder, subfolder)
        if not os.path.exists(folder):
            os.makedirs(folder)

def save_daytime_speech(player_id, day, text):
    """
    保存玩家当天白天发言到文本文件中，
    文件名格式：record/第{day}天/白天玩家发言/玩家{player_id}白天发言.txt
    """
    record_folder = "record"
    day_folder = os.path.join(record_folder, f"第{day}天")
    speech_folder = os.path.join(day_folder, "白天玩家发言")
    if not os.path.exists(speech_folder):
        os.makedirs(speech_folder)
    file_path = os.path.join(speech_folder, f"玩家{player_id}白天发言.txt")
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"玩家{player_id} 第{day}天白天发言：\n")
            f.write(text)

def save_daytime_vote(player_id, day, text):
    """
    保存玩家当天白天投票记录到文本文件中，
    文件名格式：record/第{day}天/白天玩家投票/玩家{player_id}白天投票.txt
    """
    record_folder = "record"
    day_folder = os.path.join(record_folder, f"第{day}天")
    vote_folder = os.path.join(day_folder, "白天玩家投票")
    if not os.path.exists(vote_folder):
        os.makedirs(vote_folder)
    file_path = os.path.join(vote_folder, f"玩家{player_id}白天投票.txt")
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"玩家{player_id} 第{day}天白天投票：\n")
            f.write(text)

def save_night_speech(player_id, day, text):
    """
    保存玩家当天夜晚发言到文本文件中，
    文件名格式：record/第{day}天/夜晚玩家发言/玩家{player_id}夜晚发言.txt
    """
    record_folder = "record"
    day_folder = os.path.join(record_folder, f"第{day}天")
    night_speech_folder = os.path.join(day_folder, "夜晚玩家发言")
    if not os.path.exists(night_speech_folder):
        os.makedirs(night_speech_folder)
    file_path = os.path.join(night_speech_folder, f"玩家{player_id}夜晚发言.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"玩家{player_id} 第{day}天夜晚发言：\n")
        f.write(text)

def save_night_vote(player_id, day, text):
    """
    保存玩家当天夜晚投票记录到文本文件中，
    文件名格式：record/第{day}天/夜晚玩家投票/玩家{player_id}夜晚投票.txt
    """
    record_folder = "record"
    day_folder = os.path.join(record_folder, f"第{day}天")
    night_vote_folder = os.path.join(day_folder, "夜晚玩家投票")
    if not os.path.exists(night_vote_folder):
        os.makedirs(night_vote_folder)
    file_path = os.path.join(night_vote_folder, f"玩家{player_id}夜晚投票.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"玩家{player_id} 第{day}天夜晚投票：\n")
        f.write(text)

def save_last_words_record(player_id, day, death_reason, last_words):
    """
    在 record 文件夹下记录遗言信息，
    文件为 record/遗言.txt，记录玩家死亡天数、死亡原因及遗言内容
    """
    record_folder = "record"
    file_path = os.path.join(record_folder, "遗言.txt")
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"玩家{player_id} 第{day}天死亡，原因：{death_reason}\n")
        f.write("遗言：\n")
        f.write(last_words + "\n")
        f.write("-" * 40 + "\n")

def append_check_record(day, seer_player_id, checked_player_id, checked_player_identity): #  ✨✨✨  NEW:  追加查验记录函数！ ✨✨✨
    """
    追加预言家查验记录到 record/查验.txt 文件
    记录格式:  第{day}天 预言家 玩家{seer_player_id} 查验了 玩家{checked_player_id}，身份是 {checked_player_identity}
    """
    check_file = os.path.join("record", "查验.txt")
    with open(check_file, "a", encoding="utf-8") as f: #  用 "a" (append) 模式打开文件，  追加写入
        f.write(f"第{day}天 预言家 玩家{seer_player_id} 查验了 玩家{checked_player_id}，身份是 {checked_player_identity}\n") #  记录查验信息
        # f.write("-" * 20 + "\n") #  可以加分隔线， 方便查看 (可选)
