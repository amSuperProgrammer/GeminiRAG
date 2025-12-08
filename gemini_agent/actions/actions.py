import os
import requests
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

class ActionQueryRag(Action):
    def name(self) -> Text:
        return "action_query_rag"

    def run(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:

        query = tracker.latest_message.get("text", "").strip()
        if not query:
            return []

        lang = "ru"

        rag_url = os.getenv("RAG_URL", "http://localhost:8000/query")

        payload = {
            "query": query,
            "top_k": 10
        }

        try:
            response = requests.post(rag_url, json=payload, timeout=45)
            response.raise_for_status()
            result = response.json()

            answer = result.get("answer", "").strip()
            sources = result.get("sources", [])

            # Основной ответ
            if answer:
                dispatcher.utter_message(text=answer)
            else:
                no_info = {
                    "en": "I couldn't find relevant information in the knowledge base.",
                    "ru": "Я не нашёл релевантной информации в базе знаний.",
                    "kk": "Білім базасында сәйкес ақпарат таба алмадым."
                }
                dispatcher.utter_message(text=no_info.get(lang, no_info["ru"]))

            # Источники (если есть)
            if sources:
                intro = {
                    "en": "Sources:",
                    "ru": "Источники:",
                    "kk": "Дереккөздер:"
                }.get(lang, "Sources:")

                lines = []
                for s in sources:
                    title = s.get("title", "Document")
                    score = s.get("score", 0)
                    lines.append(f"- {title} (релевантность: {score:.3f})")

                dispatcher.utter_message(text=intro + "\n" + "\n".join(lines))

        except requests.exceptions.RequestException:
            error_msg = {
                "en": "Sorry, the knowledge base is temporarily unavailable. Please try again in a couple of minutes.",
                "ru": "Извините, база знаний временно недоступна. Попробуйте чуть позже.",
                "kk": "Кешіріңіз, білім базасы уақытша қолжетімсіз. Бірнеше минуттан кейін қайталап көріңіз."
            }
            dispatcher.utter_message(text=error_msg.get(lang, error_msg["ru"]))

        except Exception as e:
            # На самый крайний случай
            dispatcher.utter_message(text="Произошла ошибка, попробуйте позже / An error occurred, please try again later.")

        return []