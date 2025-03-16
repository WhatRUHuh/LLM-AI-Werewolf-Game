#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
import os
import queue
import threading
import tkinter as tk
import google.generativeai as genai

def init_gemini():
    """初始化 Gemini 配置：读取 config.ini 中的 api_key 并设置代理"""
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config.get('Gemini', 'api_key', fallback="")
    if not api_key:
        print("警告：未在 config.ini 中找到 [Gemini] api_key 配置，可能导致 Gemini 调用失败。")
    genai.configure(api_key=api_key)
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:10808"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10808"

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

def ask_gemini_streaming(prompt, text_widget, tag="system", callback=None, player_id=None):
    """
    使用 Gemini 2.0 Flash 模型以流式方式生成内容，实时更新 text_widget
      - 插入时附带指定 tag（用于颜色、字体显示）
      - 生成完成后调用回调函数 callback(完整文本)
      - 如果 player_id 被指定，则同时将 prompt 和输出写入对应日志文件
    """
    ui_queue = queue.Queue()

    def stream_output():
        full_text = ""
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt, stream=True)
            for chunk in response:
                full_text += chunk.text
                ui_queue.put(chunk.text)
            ui_queue.put("\n")
        except Exception as e:
            error_msg = f"\n[错误] Gemini 生成失败: {type(e).__name__}: {str(e)}\n"
            ui_queue.put(error_msg)
            full_text = error_msg
        if callback:
            text_widget.after(200, lambda: callback(full_text))
        if player_id is not None:
            log_to_file(player_id, output=full_text)

    def update_text():
        while not ui_queue.empty():
            chunk_text = ui_queue.get()
            chunk_text = chunk_text.replace("\\n", "\n")
            text_widget.insert(tk.END, chunk_text, tag)
            text_widget.see(tk.END)
        text_widget.after(100, update_text)

    if player_id is not None:
        log_to_file(player_id, prompt=prompt)
    threading.Thread(target=stream_output, daemon=True).start()
    text_widget.after(100, update_text)
