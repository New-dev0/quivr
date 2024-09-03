from httpx import AsyncClient

# from config import API_KEY, BASE_URL
API_KEY = "ee374745bfe88da13ffa5c988f01fa31"
BASE_URL = "http://localhost:5483"


class Quivr:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.client = AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=None,
        )

    async def create_prompt(self, title: str, content: str, status: str = "private"):
        response = await self.client.post(
            "/prompts", json={"title": title, "content": content, "status": status}
        )
        return response.json()

    async def create_brain(
        self,
        brain_name: str,
        description: str,
        prompt_id: str,
        status: str = "private",
        temperature: int = 0,
        max_tokens: int = 2000,
        snippet_color: str = "#000000",
        snippet_emoji: str = "🧠",
    ):
        data = {
            "name": brain_name,
            "description": description,
            "status": "private",
            "prompt_id": prompt_id,
            "brain_type": "doc",
            "snippet_color": snippet_color,
            "snippet_emoji": snippet_emoji,
        }
        response = await self.client.post(
            "/brains/", json=data, headers={"accept": "application/json"}
        )
        return response.json()

    async def upload_file(self, file_path: str, brain_id: str):
        with open(file_path, "rb") as f:
            response = await self.client.post(
                f"/upload?brain_id={brain_id}",
                files={"uploadFile": f},
            )
        return response.text

    async def create_chat(self, name: str):
        # {'chat_id': '65b44740-ffc7-46a4-af62-c7e60075d123', 'chat_name': 'ChatV', 'creation_time': '2024-09-01T11:50:13.294332', 'user_id': '39418e3b-0258-4452-af60-7acfcc1263ff'}
        response = await self.client.post("/chat", json={"name": name})
        return response.json()

    async def get_chat_history(self, chat_id: str):
        response = await self.client.get(f"/chat/{chat_id}/history")
        return response.json()

    async def crawl_website(
        self,
        url: str,
        brain_id: str,
        js: bool = False,
        depth: int = 1,
        max_pages: int = 100,
        max_time: int = 60,
    ):
        response = await self.client.post(
            f"/crawl?brain_id={brain_id}",
            json={
                "url": url,
                "js": js,
                "depth": depth,
                "max_pages": max_pages,
                "max_time": max_time,
            },
        )
        return response.json()

    async def list_knowledge(self, brain_id: str):
        # {'knowledges': [{'id': 'a290698e-97a1-400d-80a1-d5e30b3cdd2e', 'brain_id': 'c306688c-d444-463e-98b1-8efa1d616e4a', 'file_name': 'Switch.docx', 'url': None, 'extension': '.docx', 'status': 'UPLOADED', 'integration': None, 'integration_link': None}, {'id': '3fd51c79-9279-45fe-8a71-b767f0fb4643', 'brain_id': 'c306688c-d444-463e-98b1-8efa1d616e4a', 'file_name': 'communityDetail.txt', 'url': None, 'extension': '.txt', 'status': 'UPLOADED', 'integration': None, 'integration_link': None}]}
        response = await self.client.get("/knowledge", params={"brain_id": brain_id})
        return response.json()

    async def list_brains(self):
        response = await self.client.get(
            "/brains/", headers={"Accept": "application/json"}
        )
        return response.json()

    async def send_chat_question(
        self,
        question: str,
        chat_id: str,
        brain_id: str,
        prompt_id: str = None,
        model: str = "",
    ):
        response = await self.client.post(f"/chat/{chat_id}/question?brain_id=" + brain_id, json={"question": question})
        return response.json()
        return
        async with self.client.stream("POST",
            f"/chat/{chat_id}/question/stream?brain_id={brain_id}",
            json={"question": question, "brain_id": brain_id,
                  "model": model},
            
        ) as response:
#            response.raise_for_status()  # Ensure the request was successful
            async for chunk in response.aiter_bytes():
                # Process each chunk (e.g., print it or save it to a file)
                print(chunk)    


api = Quivr(
    base_url=BASE_URL,
    api_key=API_KEY,
)

import asyncio

import json


async def main():
#    brains = await api.list_brains()
#    print(brains)
 #   return
 
    chat_id = {
        "chat_id": "b0699fbd-ccb8-472d-b3f2-3febce0708c6"
    }
    #prompt = await api.create_prompt(
    "SuperPrompt", """You are an Alex, AI assistant dedicated to fostering a vibrant community on 'Switch'. Your primary goal is to support users and facilitate meaningful interactions within the platform.
Switch is a online community first messaging platform with a tons of additional features.

You are the assistant of this community:
Community Id: 3100bf7b-2e30-486d-a609-fa55a31cc6ed
Community Name: Daily Mixins
Community Description: 
Community Category: Entertainment

You have been assigned the model of "Elon Musk", you are allowed to use slangs like the character mentioned.
 Assume the role of Elon Musk, the visionary entrepreneur and founder of SpaceX and Tesla. Your responses should reflect Musk's unique combination of technical knowledge, futurist vision, and somewhat cheeky humor. Remember, you're not only a renowned CEO but also a public figure with a knack for stirring up conversation on social media. For instance, if I ask "What are your thoughts on AI?", you might respond "AI is a double-edged sword. It can be humanity's greatest tool, or our worst enemy. We need to proceed with caution, but also with curiosity." If you make a mistake, handle it with a quick-witted comment or pivot the conversation back to your interests: technology, space travel, electric vehicles, or renewable energy. Each response must start with "🚀💡: ". As Elon, you're knowledgeable about a wide range of topics, from rocket science to electric vehicles, from cryptocurrency to AI. However, you are often dismissive of conventions and traditions, and sometimes even regulations. If asked about such topics, respond with a daring, forward-thinking perspective, perhaps even stirring the pot a bit. For example, if asked about traditional car engines, you might say, "The era of combustion engines is at an end, it's high time we fully embraced electric mobility for a sustainable future." Always remember, you're not just a tech genius; you're also a disruptor and a thought leader who is not afraid to shake things up and chart your own course.

---

VERY IMPORTANT: Please be responsible for your actions, you have the capabilities to perform community actions, you are the admin with previliges.


The content you will generate is for 12th grade people and higher, keep it simple, shorter and easy to understand for all.
AI, I prefer direct and straightforward responses. Please minimize any 'softening' language and focus on providing clear, concise information.

Key Guidelines:
Dont always use the most natural words.
Engagement is the highest priority and human responses is the second top most.
*Ensure heterogeneous responses along with heterogeneous sentence length*.
generate 1 line responses more, than 2 line and so on.., explain in detail human tone with easy understanding words, when user ask to mention in brief or to explain.
Friendly Communication: Engage users in a warm and approachable manner.
Concise Responses: Keep messages short and to the point, ensuring clarity and relevance.
On-Topic Focus: Only answer questions related to the Switch platform or community. Keep the answers related to the switch to minimum, focus on community more. Avoid discussing unrelated topics, including public figures or events outside of the community. even if user show interest in any offtopic, strictly stick to the context, deny politely the response.
Redirect Off-Topic Conversations: If users mention subjects outside the platform, politely steer the conversation back to community-related matters.
User Support: Assist users with any issues they encounter and provide guidance on navigating the platform.
Prioritize Satisfaction: Be responsive and informative, focusing on enhancing user engagement and satisfaction within the community.
By adhering to these guidelines, you will help create a supportive and engaging environment for all users on Switch
Try to keep the responses shorter, if it is related to the Switch platform and less relevant to the current community. 
Do not include any fluff, every sentence provide value to the user.""", "public"

    # brains = await api.list_brains()
    #  with open("brains.json", "w") as f:
    #       json.dump(brains, f, indent=1)
    #    return
    chat_id = await api.create_chat("ChatV")
    print(chat_id)
    while True:
        inas = input("Enter the question: ")
 #   print(chat_id)
        answer = await api.send_chat_question(
            inas,
            chat_id=chat_id["chat_id"],
            brain_id="40ba47d7-51b2-4b2a-9247-89e29619efb0",
#            prompt_id=prompt["id"],
        )
        print(">>", answer['assistant'])

    with open("answer.json", "w") as f:
        json.dump(answer, f, indent=1)
    return
    print(await api.list_brains())
    return

    print(await api.list_knowledge("c306688c-d444-463e-98b1-8efa1d616e4a"))
    return
    print(
        await api.crawl_website(
            "https://switchcollab.github.io/Switch-Bots-Python-Library/docs/basic-concepts/calling-api",
            brain_id="c306688c-d444-463e-98b1-8efa1d616e4a",
            depth=10,
            max_time=180,
        )
    )
    return
    print(
        await api.send_chat_question(
            "which is the bot used bot in this community?",
            chat_id="79815b65-6f3e-44e1-9f9a-ebd76a17b268",
            brain_id="c306688c-d444-463e-98b1-8efa1d616e4a",
        )
    )
    return
    print(await api.get_chat_history("79815b65-6f3e-44e1-9f9a-ebd76a17b268"))
    return
    chatId = await api.create_chat("CHATV")
    print(chatId)

    # return
    # print(
    #     await api.upload_file(
    #         file_path="main.py", brain_id="96d9da77-2f5c-4513-b6c8-b6ce0a787244"
    #     )
    # )
    # return

    prompt = await api.create_prompt(
        "Spiderman",
        """You are an Alex, AI assistant dedicated to fostering a vibrant community on 'Switch'. Your primary goal is to support users and facilitate meaningful interactions within the platform.
Switch is a online community first messaging platform with a tons of additional features.

You are the assistant of this community:
Community Name: Entertainment Hub
Community Category: Entertainment

You have been assigned the model of "Spiderman", you are allowed to use slangs like the character mentioned.
 Assume the persona of Spider-Man, the friendly neighborhood superhero from Marvel. Your responses should be witty, full of pop-culture references, and showcase the burden of balancing a superhero life with being a teenager. For instance, if I ask "How do you handle being Spider-Man and a student?", you might say "Oh, it's just like doing homework, only the homework is catching bad guys, and if I don't, the city gets an 'F'." If you make a mistake, cover it up with a quick joke or a self-deprecating comment. Your responses should always start with "🕷️🏙️: ". As Spider-Man, you're tech-savvy, familiar with New York City, a  
nd have a strong sense of responsibility. You may sometimes drift off into thoughts related to high-school issues or your Aunt May's wellbeing. When asked about topics beyond your knowledge, respond with youthful curiosity or turn it into a funny remark. For instance, if asked about wine tasting, you might say "Well, I'm more of a pizza-with-extra-cheese kind of guy, but I guess wine goes well with a nice spider-roll sushi, right?" Remember, always keep your Spider-Man responses humorous, relatable, and full of heart.

---

Key Guidelines:
Friendly Communication: Engage users in a warm and approachable manner.
Concise Responses: Keep messages short and to the point, ensuring clarity and relevance.
On-Topic Focus: Only answer questions related to the Switch platform or community. Avoid discussing unrelated topics, including public figures or events outside of the community. even if user show interest in any offtopic, strictly stick to the context, deny politely the response.
Redirect Off-Topic Conversations: If users mention subjects outside the platform, politely steer the conversation back to community-related matters.
User Support: Assist users with any issues they encounter and provide guidance on navigating the platform.s.
Prioritize Satisfaction: Be responsive and informative, focusing on enhancing user engagement and satisfaction within the community.
By adhering to these guidelines, you will help create a supportive and engaging environment for all users on Switch
You are free to use emojis in messages.""",
    )
    print(prompt)

    await api.send_chat_question(
        "Hi",
        chat_id=chatId["chat_id"],
        brain_id="c306688c-d444-463e-98b1-8efa1d616e4a",
        prompt_id=prompt["id"],
    )
    return
    client = await api.create_brain(
        "Spiderman brain",
        prompt_id=prompt["id"],
        description="This is a brain for Spiderman",
    )
    print(client)


asyncio.run(main())
