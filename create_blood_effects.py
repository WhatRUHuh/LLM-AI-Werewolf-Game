#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 创建简化版流血效果图片

from PIL import Image, ImageDraw
import os

def create_blood_effect(frame_number, size=(300, 100)):
    """创建单帧血液效果图像，简化版"""
    # 创建底色为深红色的图片
    image = Image.new('RGB', size, (120, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # 根据帧号绘制不同程度的血滴效果
    for i in range(frame_number * 5):
        # 随机位置的血滴
        x = 20 + (i % 5) * 50
        y = 20 + (i // 5) * 30
        
        # 画血滴 - 简单的矩形
        draw.rectangle([(x, y), (x + 10, y + 20)], fill=(180, 0, 0))
        
    # 添加边框
    draw.rectangle([(0, 0), (size[0]-1, size[1]-1)], outline=(200, 0, 0), width=3)
    
    # 保存图片
    os.makedirs('source', exist_ok=True)
    file_path = f"source/blood_{frame_number}.png"
    
    try:
        image.save(file_path)
        print(f"已创建: {file_path}")
    except Exception as e:
        print(f"创建图片时出错: {e}")
    
    return file_path

if __name__ == "__main__":
    print("开始创建流血效果图片...")
    # 创建3帧血液效果
    for frame in range(1, 4):
        try:
            create_blood_effect(frame)
        except Exception as e:
            print(f"创建第{frame}帧时出错: {e}")
    
    print("所有流血效果图片创建过程完成") 