#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import queue
import threading
import tkinter as tk
import configparser
import datetime
from typing import Optional, Callable, Dict, Any
from openai import OpenAI

def log_to_file(player_id: int, prompt: Optional[str] = None, output: Optional[str] = None) -> None:
    """将指定玩家的 prompt 和输出写入日志文件，附带时间戳，只记录 1~10 号玩家日志"""
    if player_id < 1 or player_id > 10:
        return  # 只记录 1~10 号玩家日志
    log_folder = "log"
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    filename = os.path.join(log_folder, f"player{player_id}.log")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}]\n")
        if prompt:
            f.write(f"Prompt: {prompt}\n")
        if output:
            f.write(f"Output: {output}\n")
        f.write("\n")

def ask_hunyuan_streaming(
    prompt: str,
    text_widget: tk.Text,
    tag: str = "system",
    callback: Optional[Callable[[str], None]] = None,
    player_id: Optional[int] = None,
    extra_body: Optional[Dict[str, Any]] = None
) -> None:
    """
    使用混元大模型以流式方式生成内容，实时更新 text_widget。

    - 显示所有返回内容到 text_widget；
    - 通过 extra_body 自定义参数，默认传入 {"enable_enhancement": True}；
    - 固定使用模型 "hunyuan-turbo"。
    """
    if extra_body is None:
        extra_body = {"enable_enhancement": True}

    ui_queue = queue.Queue()
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config.get('hunyuan', 'api_key', fallback=os.environ.get("HUNYUAN_API_KEY", ""))
    base_url = config.get('hunyuan', 'base_url', fallback="https://api.hunyuan.cloud.tencent.com/v1")
    # 固定选择模型为 hunyuan-turbo
    model = "hunyuan-turbo"

    if not api_key:
        ui_queue.put("\n[错误] 未在 config.ini 或环境变量中找到 HUNYUAN_API_KEY 配置。\n")
    
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    
    final_answer_text = ""

    def stream_output():
        nonlocal final_answer_text
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                extra_body=extra_body,
                stream=True
            )
            for chunk in response:
                # 混元接口与 OpenAI 接口兼容，支持 delta 输出
                reasoning_chunk = getattr(chunk.choices[0].delta, "reasoning_content", None)
                answer_chunk = getattr(chunk.choices[0].delta, "content", None)
                if reasoning_chunk:
                    ui_queue.put(reasoning_chunk)
                if answer_chunk:
                    ui_queue.put(answer_chunk)
                    final_answer_text += answer_chunk
            ui_queue.put("\n")
        except Exception as e:
            error_msg = f"\n[错误] 混元生成失败: {type(e).__name__}: {str(e)}\n"
            ui_queue.put(error_msg)
            final_answer_text = error_msg
        if callback:
            text_widget.after(200, lambda: callback(final_answer_text))
        if player_id is not None:
            log_to_file(player_id, output=final_answer_text)

    def update_text():
        while not ui_queue.empty():
            chunk_text = ui_queue.get()
            # 将转义的换行符替换为实际换行
            chunk_text = chunk_text.replace("\\n", "\n")
            text_widget.insert(tk.END, chunk_text, tag)
            text_widget.see(tk.END)
        text_widget.after(100, update_text)

    if player_id is not None:
        log_to_file(player_id, prompt=prompt)
    threading.Thread(target=stream_output, daemon=True).start()
    text_widget.after(100, update_text)
