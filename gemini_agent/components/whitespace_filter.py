from typing import Dict, Text, Any, List
from rasa.engine.graph import GraphComponent, ExecutionContext
from rasa.engine.recipes.default_recipe import DefaultV1Recipe
from rasa.engine.storage.resource import Resource
from rasa.engine.storage.storage import ModelStorage
from rasa.shared.nlu.training_data.message import Message
from rasa.shared.nlu.training_data.training_data import TrainingData

import logging

logger = logging.getLogger(__name__)

@DefaultV1Recipe.register(
    [DefaultV1Recipe.ComponentType.MESSAGE_TOKENIZER],
    is_trainable=False
)
class WhitespaceFilter(GraphComponent):
    @staticmethod
    def required_components() -> List:
        return []

    @classmethod
    def create(
            cls,
            config: Dict[Text, Any],
            model_storage: ModelStorage,
            resource: Resource,
            execution_context: ExecutionContext,
    ) -> GraphComponent:
        return cls()

    def train(self, training_data: TrainingData) -> Resource:
        return Resource("")

    def process_training_data(self, training_data: TrainingData) -> TrainingData:
        return training_data

    def process(self, messages: List[Message]) -> List[Message]:
        for message in messages:
            if message.get("text", "").strip() == "":
                message.set("text", "[empty]")
                # message.data["intent"] = {"name": "ignore_blank", "confidence": 1.0}
        return messages