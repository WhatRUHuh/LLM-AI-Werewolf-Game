import asyncio
import edge_tts
import os

async def test_edge_tts(text, output_file="test_audio.mp3"):
    """
    使用 edge-tts 将文本转换为语音并保存到文件。

    Args:
        text: 要转换的文本 (字符串).
        output_file: 输出音频文件名 (字符串, 默认为 "test_audio.mp3").
    """
    try:
        voice = "zh-CN-XiaoxiaoNeural" # 选择中文语音 (晓晓, 女声, 神经风格)
        communicate = edge_tts.Communicate(text, voice)
        with open(output_file, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
        print(f"语音已保存到 {output_file}")
        os.startfile(output_file) # 尝试自动播放音频文件 (Windows only)
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    test_text = "你好，这是一段使用 edge-tts 库进行语音合成的测试。"
    asyncio.run(test_edge_tts(test_text))
    print("请检查生成的 test_audio.mp3 文件，听取语音效果。")


# zh-CN-XiaoxiaoNeural               Female    News, Novel            Warm
# zh-CN-XiaoyiNeural                 Female    Cartoon, Novel         Lively
# zh-CN-YunjianNeural                Male      Sports, Novel          Passion
# zh-CN-YunxiNeural                  Male      Novel                  Lively, Sunshine
# zh-CN-YunxiaNeural                 Male      Cartoon, Novel         Cute
# zh-CN-YunyangNeural                Male      News                   Professional, Reliable
# zh-CN-liaoning-XiaobeiNeural       Female    Dialect                Humorous
# zh-CN-shaanxi-XiaoniNeural         Female    Dialect                Bright
# zh-HK-HiuGaaiNeural                Female    General                Friendly, Positive
# zh-HK-HiuMaanNeural                Female    General                Friendly, Positive
# zh-HK-WanLungNeural                Male      General                Friendly, Positive
# zh-TW-HsiaoChenNeural              Female    General                Friendly, Positive
# zh-TW-HsiaoYuNeural                Female    General                Friendly, Positive
# zh-TW-YunJheNeural                 Male      General                Friendly, Positive
# zu-ZA-ThandoNeural                 Female    General                Friendly, Positive
# zu-ZA-ThembaNeural                 Male      General                Friendly, Positive