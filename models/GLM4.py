#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import queue
import threading
import tkinter as tk
import configparser
from zhipuai import ZhipuAI

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

def ask_glm4_streaming(prompt, text_widget, tag="system", callback=None, player_id=None):
    """
    使用 GLM-4 模型以流式方式生成内容，实时更新 text_widget  
      - 将所有返回内容实时写入到 text_widget  
      - 在生成完成后，将最终生成的文本传递给回调函数，并写入日志文件
    """
    ui_queue = queue.Queue()
    # 从 config.ini 中读取 [glm4] 下的 api_key
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config.get('glm4', 'api_key', fallback="")
    if not api_key:
        ui_queue.put("\n[错误] 未在 config.ini 中找到 [glm4] 的 api_key 配置。\n")
    
    client = ZhipuAI(api_key=api_key)
    
    final_answer_text = ""
    
    def stream_output():
        nonlocal final_answer_text
        try:
            response = client.chat.completions.create(
                model="glm-4-plus",
                messages=[
                    {"role": "system", "content": "你是一个乐于回答各种问题的小助手，你的任务是提供专业、准确、有洞察力的建议。"},
                    {"role": "user", "content": prompt}
                ],
                stream=True,
            )
            for chunk in response:
                # GLM-4 的流式返回在 delta 中只有 content 字段
                content = chunk.choices[0].delta.content
                if content:
                    final_answer_text += content
                    ui_queue.put(content)
            ui_queue.put("\n")
        except Exception as e:
            error_msg = f"\n[错误] GLM-4 生成失败: {type(e).__name__}: {str(e)}\n"
            ui_queue.put(error_msg)
            final_answer_text = error_msg
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
