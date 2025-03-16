#!/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser
import os
import google.generativeai as genai

def init_config():
    """
    读取配置文件 'config.ini' 并设置 Gemini 的 API key 与代理。
    """
    config = configparser.ConfigParser()
    config.read('config.ini')
    api_key = config.get('Gemini', 'api_key', fallback="")
    if not api_key:
        print("警告：未在 config.ini 中找到 [Gemini] api_key 配置，可能导致 Gemini 调用失败。")
    genai.configure(api_key=api_key)
    os.environ["HTTP_PROXY"] = "http://127.0.0.1:10808"
    os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10808"
    # 读取 TTS 启用配置，默认为 True
    tts_enabled = config.getboolean('Game', 'tts_enabled', fallback=True)
    return tts_enabled
