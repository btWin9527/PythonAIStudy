from dotenv import load_dotenv
from my_llm import MYLLM
import os

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

llm = MYLLM()  # 自动检测 provider（当前 .env 为 DashScope/百炼）

# 准备消息
messages = [{"role": "user", "content": "你好，请介绍一下自己"}]

response_stream = llm.think(messages)

print("ModelScope Response")
for chunk in response_stream:
    # chunk在my_llm库中已经打印过一遍，这里只需要pass即可
    # print(chunk, end="", flush=True)
    pass
