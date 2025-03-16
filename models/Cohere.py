#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
os.environ["HTTP_PROXY"] = "http://127.0.0.1:10808"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10808"

import queue
import threading
import tkinter as tk
import configparser
import cohere

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

def ask_cohere_streaming(prompt, text_widget, tag="system", callback=None, player_id=None):
    """
    使用 Cohere 的 Command 模型以流式方式生成内容，实时更新 text_widget
      - 流式返回每个文本片段实时显示
      - 生成完成后，将最终生成的文本传递给回调函数，并写入日志文件
    """
    ui_queue = queue.Queue()
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config.get('cohere', 'api_key', fallback="")
    model = config.get('cohere', 'model', fallback="command-r-plus-08-2024")
    if not api_key:
        ui_queue.put("\n[错误] 未在 config.ini 中找到 [cohere] 的 api_key 配置。\n")
    co = cohere.ClientV2(api_key)
    
    final_answer_text = ""

    def stream_output():
        nonlocal final_answer_text
        try:
            # 使用流式接口
            response = co.chat_stream(
                model=model,
                messages=[{"role": "user", "content": prompt}],
            )
            for chunk in response:
                # 判断类型是否为内容片段
                if chunk.type == "content-delta":
                    text = chunk.delta.message.content.text
                    if text:
                        ui_queue.put(text)
                        final_answer_text += text
            ui_queue.put("\n")
        except Exception as e:
            error_msg = f"\n[错误] Cohere 生成失败: {type(e).__name__}: {str(e)}\n"
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
