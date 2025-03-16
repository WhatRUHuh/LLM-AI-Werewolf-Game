from models.gemini import ask_gemini_streaming
from models.deepseek import ask_deepseek_streaming
from models.GLM4 import ask_glm4_streaming
from models.SparkMax import ask_sparkmax_streaming
from models.Cohere import ask_cohere_streaming
from models.Mistral import ask_mistral_streaming
from models.QWQ import ask_qwq_streaming
from models.hunyuan import ask_hunyuan_streaming




class ModelHandler:
    def __init__(self, app):
        self.app = app

    def call_model(self, model_name, prompt, text_widget, tag, callback, player_id):
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
