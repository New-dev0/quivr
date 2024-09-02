import logging
from urllib.parse import parse_qs, urlparse

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama.llms import OllamaLLM
from langchain_ollama.chat_models import ChatOllama
from langchain_groq.chat_models import ChatGroq
from pydantic.v1 import SecretStr

from quivr_core.brain.info import LLMInfo
from quivr_core.config import LLMEndpointConfig
from quivr_core.utils import model_supports_function_calling

logger = logging.getLogger("quivr_core")


class LLMEndpoint:
    def __init__(self, llm_config: LLMEndpointConfig, llm: BaseChatModel):
        self._config = llm_config
        self._llm = llm
        self._supports_func_calling = model_supports_function_calling(
            self._config.model
        )

    def get_config(self):
        return self._config

    @classmethod
    def from_config(cls, config: LLMEndpointConfig = LLMEndpointConfig()):
        try:
            from langchain_openai import AzureChatOpenAI, ChatOpenAI

            if config.model.startswith("azure/"):
                # Parse the URL
                parsed_url = urlparse(config.llm_base_url)
                deployment = parsed_url.path.split("/")[3]  # type: ignore
                api_version = parse_qs(parsed_url.query).get("api-version", [None])[0]  # type: ignore
                azure_endpoint = f"https://{parsed_url.netloc}"  # type: ignore
                _llm = AzureChatOpenAI(
                    azure_deployment=deployment,  # type: ignore
                    api_version=api_version,
                    api_key=SecretStr(config.llm_api_key)
                    if config.llm_api_key
                    else None,
                    azure_endpoint=azure_endpoint,
                )
            elif True:
                _llm = ChatGroq(
            api_key="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",
            model="llama3-groq-8b-8192-tool-use-preview",
 #             temperature=0.9
                )
            elif True or config.model.startswith("ollama/"):
                logger.info("Using Ollama LLM")
                _llm = ChatOllama(
                    model="llama3", #config.model.split("/")[-1],
                    base_url="https://2bd2-109-199-104-77.ngrok-free.app"# config.llm_base_url,
                )
            else:
                # todo: change
                _llm = ChatOpenAI(
                    model=config.model,
                    api_key=SecretStr(config.llm_api_key)
                    if config.llm_api_key
                    else None,
                    base_url= config.llm_base_url,
                )
            return cls(llm=_llm, llm_config=config)

        except ImportError as e:
            raise ImportError(
                "Please provide a valid BaseLLM or install quivr-core['base'] package"
            ) from e

    def supports_func_calling(self) -> bool:
        return self._supports_func_calling

    def info(self) -> LLMInfo:
        return LLMInfo(
            model=self._config.model,
            llm_base_url=(
                self._config.llm_base_url or "openai"
            ),
            temperature=self._config.temperature,
            max_tokens=self._config.max_tokens,
            supports_function_calling=self.supports_func_calling(),
        )
