# TTS.py
# 语音合成和播放功能模块

import asyncio
import edge_tts
import os

# TTS 音色配置
TTS_VOICES = {
    1: "zh-CN-XiaoxiaoNeural",
    2: "zh-CN-XiaoyiNeural",
    3: "zh-CN-YunjianNeural",
    4: "zh-CN-YunxiNeural",
    5: "zh-CN-YunxiaNeural",
    6: "zh-CN-YunyangNeural",
    7: "zh-CN-liaoning-XiaobeiNeural",
    8: "zh-CN-shaanxi-XiaoniNeural",
    9: "zh-HK-HiuGaaiNeural",
    10: "zh-TW-HsiaoChenNeural",
}

async def play_edge_tts(text, voice, output_file="temp_audio.mp3", rate="+0%"):
    """
    使用 edge-tts 将文本转换为语音并保存到文件。

    Args:
        text: 要转换的文本 (字符串).
        voice: 使用的音色 (字符串).
        output_file: 输出音频文件名 (字符串, 默认为 "temp_audio.mp3").
        rate: 语音速度 (字符串, 默认为 "+0%").
    """
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        with open(output_file, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
        print(f"语音已保存到 {output_file}")
        os.startfile(output_file) # 尝试自动播放音频文件 (Windows only)
    except edge_tts.exceptions.HTTPStatusError as e:
        if "503" in str(e):
            print(f"语音服务暂时不可用(503错误)，请稍后再试: {e}")
        else:
            print(f"语音服务错误: {e}")
    except edge_tts.exceptions.ConnectionError as e:
        print(f"网络连接错误，无法连接到语音服务: {e}")
    except Exception as e:
        print(f"发生错误: {e}")

def init_tts_config():
    # 初始化 TTS 配置 (目前无需配置)
    pass

def play_tts(text, player_id, rate="+0%"):
    # 播放 TTS 语音
    if player_id in TTS_VOICES:
        voice = TTS_VOICES[player_id]
        asyncio.run(play_edge_tts(text, voice, rate=rate))
    else:
        print(f"玩家 {player_id} 没有配置 TTS 音色")
