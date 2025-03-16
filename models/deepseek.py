#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import queue
import threading
import tkinter as tk
import configparser
from openai import OpenAI

def log_to_file(player_id, prompt=None, output=None):
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

def ask_deepseek_streaming(prompt, text_widget, tag="system", callback=None, player_id=None):
    """
    使用 DeepSeek 模型以流式方式生成内容，实时更新 text_widget  
      - 显示所有返回内容（包括思考过程）到 text_widget  
      - 仅将 "=== Final Answer ===" 之后的内容传递给回调函数（并存入日志文件），即不保存思考过程
    """
    ui_queue = queue.Queue()
    # 从 config.ini 中读取 modelscope 的 api_key
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config.get('modelscope', 'api_key', fallback="")
    if not api_key:
        ui_queue.put("\n[错误] 未在 config.ini 中找到 [modelscope] 的 api_key 配置。\n")
    
    # 初始化 DeepSeek client
    client = OpenAI(
        base_url='https://api-inference.modelscope.cn/v1/',
        api_key=api_key,
    )
    
    final_answer_text = ""
    final_answer_started = False

    def stream_output():
        nonlocal final_answer_text, final_answer_started
        full_text = ""
        try:
            response = client.chat.completions.create(
                model='deepseek-ai/DeepSeek-R1',
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a helpful assistant.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                stream=True
            )
            for chunk in response:
                reasoning_chunk = chunk.choices[0].delta.reasoning_content
                answer_chunk = chunk.choices[0].delta.content
                if reasoning_chunk:
                    full_text += reasoning_chunk
                    ui_queue.put(reasoning_chunk)
                if answer_chunk:
                    if not final_answer_started:
                        final_answer_started = True
                        final_marker = "\n\n === Final Answer ===\n"
                        full_text += final_marker
                        ui_queue.put(final_marker)
                    full_text += answer_chunk
                    ui_queue.put(answer_chunk)
                    if final_answer_started:
                        final_answer_text += answer_chunk
            ui_queue.put("\n")
        except Exception as e:
            error_msg = f"\n[错误] DeepSeek 生成失败: {type(e).__name__}: {str(e)}\n"
            ui_queue.put(error_msg)
            full_text = error_msg
        if callback:
            text_widget.after(200, lambda: callback(final_answer_text))
        if player_id is not None:
            log_to_file(player_id, output=final_answer_text)

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
