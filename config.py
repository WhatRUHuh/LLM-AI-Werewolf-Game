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
    config.read('config.ini', encoding='utf-8')

    api_key = config.get('Gemini', 'api_key', fallback="")
    if not api_key:
        print("警告：未在 config.ini 中找到 [Gemini] api_key 配置，可能导致 Gemini 调用失败。")
    genai.configure(api_key=api_key)

    # 读取代理配置
    http_proxy = config.get('Proxy', 'HTTP_PROXY', fallback="")
    https_proxy = config.get('Proxy', 'HTTPS_PROXY', fallback="")

    # 读取 TTS 启用配置，默认为 True
    tts_enabled = config.getboolean('Game', 'tts_enabled', fallback=True)

    # 返回一个包含所有配置的字典
    return {
        "tts_enabled": tts_enabled,
        "http_proxy": http_proxy,
        "https_proxy": https_proxy
    }
