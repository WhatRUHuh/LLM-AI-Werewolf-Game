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

def ask_sparkmax_streaming(prompt, text_widget, tag="system", callback=None, player_id=None):
    """
    使用 星火 模型（SparkMax）以流式方式生成内容，实时更新 text_widget  
      - 显示所有返回内容（包括思考过程）到 text_widget  
      - 仅将 "=== Final Answer ===" 之后的内容传递给回调函数并存入日志文件（即不记录中间的思考过程）
    """
    ui_queue = queue.Queue()
    # 从 config.ini 中读取 [sparkmax] 下的配置
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config.get('sparkmax', 'api_key', fallback="")
    service_id = config.get('sparkmax', 'service_id', fallback="")
    api_base = config.get('sparkmax', 'api_base', fallback="http://maas-api.cn-huabei-1.xf-yun.com/v1")
    if not api_key or not service_id:
        ui_queue.put("\n[错误] 未在 config.ini 中找到 [sparkmax] 的完整配置。\n")
    client = OpenAI(api_key=api_key, base_url=api_base)
    
    final_answer_text = ""
    final_answer_started = False

    def stream_output():
        nonlocal final_answer_text, final_answer_started
        try:
            response = client.chat.completions.create(
                model=service_id,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                temperature=0.7,
                max_tokens=4096,
                extra_headers={"lora_id": "0"},
                stream_options={"include_usage": True}
            )
            for chunk in response:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    ui_queue.put(delta.reasoning_content)
                if hasattr(delta, 'content') and delta.content:
                    if not final_answer_started:
                        final_answer_started = True
                        final_marker = "\n\n \n"
                        ui_queue.put(final_marker)
                    ui_queue.put(delta.content)
                    final_answer_text += delta.content
            ui_queue.put("\n")
        except Exception as e:
            error_msg = f"\n[错误] SparkMax 生成失败: {type(e).__name__}: {str(e)}\n"
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
