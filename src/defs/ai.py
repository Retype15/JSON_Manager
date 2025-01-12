import google.generativeai as genai

class geminiClass():
    def __init__(self, api_key):
        #print(api_key)
        genai.configure(api_key=api_key)
        self.generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }
        #self.load_model("You are Aisha, a virtual neko girl, Aisha has a very happy little girl.")
    
    def set_new_api_key(self, api_key):
        genai.configure(api_key=api_key)
    
    def load_model(self,system_instruction=""):
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=self.generation_config,
            system_instruction=system_instruction
        )
        self.chat_session = self.model.start_chat(history=[])
    
    def query(self, msg, stream=False):
        #print(msg)
        response = self.chat_session.send_message(msg, stream=stream)
        return response