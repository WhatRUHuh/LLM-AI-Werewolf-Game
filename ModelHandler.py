from models.gemini import ask_gemini_streaming
from models.deepseek import ask_deepseek_streaming
from models.GLM4 import ask_glm4_streaming
from models.SparkMax import ask_sparkmax_streaming
from models.Cohere import ask_cohere_streaming
from models.Mistral import ask_mistral_streaming
from models.QWQ import ask_qwq_streaming
from models.hunyuan import ask_hunyuan_streaming
from models.Ollama import ask_ollama_streaming # 导入新的 Ollama 流式函数




class ModelHandler:
    def __init__(self, app):
        self.app = app

    def call_model(self, model_name, prompt, text_widget, tag, callback, player_id):
        # 假设 SpeechHandler 和 VoteHandler 会传递必要的参数，如角色、历史记录等。
        # 目前，这些参数没有从 ModelHandler.call_model 显式传递给每个 ask_..._streaming 函数。
        # ask_ollama_streaming 函数期望接收这些参数，因此可能需要进一步调整
        # SpeechHandler/VoteHandler 调用 ModelHandler.call_model 的方式，或 call_model 传递这些参数的方式。
        # 对于此占位符实现，如果这些额外参数不可用，我们将传递 None 或默认值。
        
        # 检索 ask_ollama_streaming 所需的玩家和游戏状态详细信息
        player = self.app.state.players.get(player_id)
        role = player.identity if player else "Unknown"
        # 理想情况下，历史记录和游戏状态摘要应由调用处理程序（Speech/Vote）准备好，
        # 并传递给 call_model。目前使用占位符。
        history_placeholder = "Placeholder history" 
        game_state_summary_placeholder = "Placeholder game state summary"
        werewolf_chat_history_placeholder = None # 假设并非总是可用

        if model_name == "gemini":
            ask_gemini_streaming(prompt, text_widget, tag=tag, callback=callback, player_id=player_id)
        elif model_name == "deepseek":
            ask_deepseek_streaming(prompt, text_widget, tag=tag, callback=callback, player_id=player_id)
        elif model_name == "glm4":
            ask_glm4_streaming(prompt, text_widget, tag=tag, callback=callback, player_id=player_id)
        elif model_name == "sparkmax":
            ask_sparkmax_streaming(prompt, text_widget, tag=tag, callback=callback, player_id=player_id)
        elif model_name == "cohere":
            ask_cohere_streaming(prompt, text_widget, tag=tag, callback=callback, player_id=player_id)
        elif model_name == "mistral":
            ask_mistral_streaming(prompt, text_widget, tag=tag, callback=callback, player_id=player_id)
        elif model_name == "qwq":
            ask_qwq_streaming(prompt, text_widget, tag=tag, callback=callback, player_id=player_id)
        elif model_name == "hunyuan":
            ask_hunyuan_streaming(prompt, text_widget, tag=tag, callback=callback, player_id=player_id)
        elif model_name == "Ollama":
            ask_ollama_streaming(
                prompt, 
                text_widget, 
                tag=tag, 
                callback=callback, 
                player_id=player_id,
                role=role, 
                history=history_placeholder, 
                game_state_summary=game_state_summary_placeholder, 
                werewolf_chat_history=werewolf_chat_history_placeholder 
            )
