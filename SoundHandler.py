# SoundHandler.py
# 游戏音效管理模块

import os
import pygame

class SoundHandler:
    def __init__(self):
        # 初始化pygame的混音器
        pygame.mixer.init()
        
        # 音效字典
        self.sounds = {}
        
        # 加载所有音效
        self.load_sounds()
        
        # 音效开关（默认开启）
        self.sound_enabled = True
        
    def load_sounds(self):
        """加载所有游戏音效"""
        # 狼叫声
        wolf_howl_path = os.path.join("source", "狼叫.wav")
        if os.path.exists(wolf_howl_path):
            self.sounds["wolf_howl"] = pygame.mixer.Sound(wolf_howl_path)
        else:
            print(f"警告：找不到音效文件 {wolf_howl_path}")
            
        # 可以在这里加载更多音效
        # self.sounds["seer"] = pygame.mixer.Sound(os.path.join("source", "预言家.wav"))
        # self.sounds["witch"] = pygame.mixer.Sound(os.path.join("source", "女巫.wav"))
        
    def play_sound(self, sound_name):
        """播放指定音效"""
        if not self.sound_enabled:
            return
            
        if sound_name in self.sounds:
            try:
                self.sounds[sound_name].play()
            except Exception as e:
                print(f"播放音效 {sound_name} 时出错: {e}")
        else:
            print(f"警告：找不到音效 {sound_name}")
            
    def play_wolf_howl(self):
        """播放狼叫声"""
        self.play_sound("wolf_howl")
        
    def toggle_sound(self):
        """切换音效开关"""
        self.sound_enabled = not self.sound_enabled
        return self.sound_enabled
        
    def set_volume(self, volume):
        """设置音量（0.0 到 1.0）"""
        for sound in self.sounds.values():
            sound.set_volume(volume) 