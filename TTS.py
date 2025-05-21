# TTS.py
# 语音合成和播放功能模块

import asyncio
import edge_tts
import os
import tempfile
import uuid
from datetime import datetime
import time

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

async def play_edge_tts(text, voice, rate="+0%", max_retries=3):
    """
    使用 edge-tts 将文本转换为语音并保存到临时文件
    
    Args:
        text: 要转换的文本
        voice: 使用的语音
        rate: 语速
        max_retries: 最大重试次数
    """
    for attempt in range(max_retries):
        try:
            # 生成唯一的临时文件名
            temp_filename = f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.mp3"
            output_file = os.path.join(tempfile.gettempdir(), temp_filename)
            
            # 确保临时文件不存在
            if os.path.exists(output_file):
                os.remove(output_file)
            
            # 创建通信对象
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            
            # 写入音频数据
            async with asyncio.timeout(30):  # 设置30秒超时
                with open(output_file, "wb") as f:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            f.write(chunk["data"])
                
                print(f"语音已保存到 {output_file}")
                
                # 使用系统默认播放器播放音频
                try:
                    if os.name == 'nt':  # Windows
                        os.system(f'start {output_file}')
                    elif os.name == 'posix':  # Linux/Mac
                        os.system(f'xdg-open {output_file}')
                    return True
                except Exception as e:
                    print(f"播放音频失败: {str(e)}")
                    return False
                    
        except asyncio.TimeoutError:
            print(f"TTS请求超时 (尝试 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # 等待2秒后重试
            continue
        except Exception as e:
            print(f"TTS错误: {str(e)} (尝试 {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)  # 等待2秒后重试
            continue
    
    print("所有TTS重试都失败了")
    return False

def init_tts_config():
    # 初始化 TTS 配置 (目前无需配置)
    pass

def play_tts(text, player_id, rate="+0%"):
    """
    播放 TTS 语音
    """
    if not text or not player_id:
        print("无效的TTS参数")
        return False
        
    if player_id in TTS_VOICES:
        voice = TTS_VOICES[player_id]
        try:
            return asyncio.run(play_edge_tts(text, voice, rate=rate))
        except Exception as e:
            print(f"TTS执行错误: {str(e)}")
            return False
    else:
        print(f"玩家 {player_id} 没有配置 TTS 音色")
        return False
