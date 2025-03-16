#readrecord.py
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re

def get_last_words_content():
    """读取 record/遗言.txt 的全部内容（若存在）"""
    record_folder = "record"
    file_path = os.path.join(record_folder, "遗言.txt")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except:
            return ""
    return ""

def get_day_vote_reasoning_player(player_id, current_day):
    """
    返回指定玩家在指定天数 (current_day) 的白天投票理由.
    从 record/第{current_day}天/白天玩家投票/玩家{player_id}白天投票.txt 读取.
    如果文件不存在或读取失败，返回空字符串.
    """
    if current_day <= 0:  #  第0天或之前，没有记录
        return ""
    record_root = "record"
    day_folder = os.path.join(record_root, f"第{current_day}天", "白天玩家投票") #  day_folder  路径用 current_day
    file_name = f"玩家{player_id}白天投票.txt"
    file_path = os.path.join(day_folder, file_name)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    #  尝试找到理由部分，使用 "__理由是：__" 分隔符 (假设你的投票理由前面有这个分隔符)
                    reason_match = re.search(r'__理由是：__\s*(.*)', content, re.DOTALL) #  re.DOTALL 匹配换行符
                    if reason_match:
                        return reason_match.group(1).strip() #  提取理由部分
                    else:
                        return content #  如果没有分隔符，返回全部内容 (兼容旧格式)
                return ""  #  文件内容为空，返回空字符串
        except Exception as e:  #  更具体的异常处理
            print(f"[警告] 读取白天投票理由失败 (玩家{player_id}, 第{current_day}天): {e}") #  打印更详细的错误信息
            return ""  #  读取失败，返回空字符串
    return ""  #  文件不存在，返回空字符串


def get_night_vote_reasoning_player(player_id, current_day):
    """
    返回指定玩家在指定天数 (current_day) 的夜晚投票理由.
    从 record/第{current_day}天/夜晚玩家投票/玩家{player_id}夜晚投票.txt 读取.
    如果文件不存在或读取失败，返回空字符串.
    """
    if current_day <= 0: #  第0天或之前，没有记录
        return ""
    record_root = "record"
    day_folder = os.path.join(record_root, f"第{current_day}天", "夜晚玩家投票") #  day_folder  路径用 current_day
    file_name = f"玩家{player_id}夜晚投票.txt"
    file_path = os.path.join(day_folder, file_name)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    #  尝试找到理由部分，使用 "__理由是：__" 分隔符 (假设你的投票理由前面有这个分隔符)
                    reason_match = re.search(r'__理由是：__\s*(.*)', content, re.DOTALL) #  re.DOTALL 匹配换行符
                    if reason_match:
                        return reason_match.group(1).strip() #  提取理由部分
                    else:
                        return content #  如果没有分隔符，返回全部内容 (兼容旧格式)
                return ""  #  文件内容为空，返回空字符串
        except Exception as e: #  更具体的异常处理
            print(f"[警告] 读取夜晚投票理由失败 (玩家{player_id}, 第{current_day}天): {e}") #  打印更详细的错误信息
            return "" #  读取失败，返回空字符串
    return "" #  文件不存在，返回空字符串
