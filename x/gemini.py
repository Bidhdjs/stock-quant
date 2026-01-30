

# export GEMINI_API_KEY="AIzaSyDRCDmjsy1E4zjjYC-xxxFxaXelPsELXdc"

# 配置API Key
# genai.configure(api_key="")
from google import genai
client = genai.Client(api_key="AIzaSyDRCDmjsy1E4zjjYC-xxxFxaXelPsELXdc")

response = client.models.generate_content(
    model='gemini-3-pro-preview',
    contents='解释一下量子计算的基本原理'
)
print(response.text)