import logging
import operator, json
from operator import itemgetter
from typing import AsyncGenerator, Optional, Sequence

import quivr_core.generation as generation

# TODO(@aminediro): this is the only dependency to langchain package, we should remove it
from langchain.retrievers import ContextualCompressionRetriever

from langchain_core.callbacks import Callbacks
from langchain_core.documents import BaseDocumentCompressor, Document
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage, ToolMessage, SystemMessage
from langchain_core.messages.ai import AIMessageChunk
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.vectorstores import VectorStore

from quivr_core.chat import ChatHistory
from quivr_core.config import RAGConfig
from quivr_core.llm import LLMEndpoint
from quivr_core.models import (
    ParsedRAGChunkResponse,
    ParsedRAGResponse,
    QuivrKnowledge,
    RAGResponseMetadata,
    cited_answer,
)
from datetime import datetime
from quivr_core.prompts import ANSWER_PROMPT, CONDENSE_QUESTION_PROMPT, NEW_ANSWER_PROMPT, get_answer_prompt
from quivr_core.utils import (
    combine_documents,
    format_file_list,
    get_chunk_metadata,
    parse_chunk_response,
    parse_response,
)
from langgraph.graph import END, StateGraph

from typing import TypedDict, Annotated, Sequence

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

logger = logging.getLogger("quivr_core")

ToolMap = {
    "update_community_description": generation.update_community_description,
    "get_channel_list": generation.get_channel_list,
    "get_group_list": generation.get_group_list,
    "create_channel": generation.create_channel,
    "get_channel_group_history": generation.get_channel_group_history,
    "get_community_detail": generation.get_community_detail,
    "get_community_chat_analysis": generation.get_community_chat_analysis,
    "get_bots_in_community": generation.get_bots_in_community,
    "delete_all_messages": generation.delete_all_messages,
    "add_bot_to_community": generation.add_bot_to_community,
    "get_commands_in_channel_group": generation.get_commands_in_channel_group,
    "send_message": generation.send_message,
    "create_group": generation.create_group,
    "get_community_guidelines": generation.get_community_guidelines,
    "get_user_info": generation.get_user_info,
}


class IdempotentCompressor(BaseDocumentCompressor):
    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Optional[Callbacks] = None,
    ) -> Sequence[Document]:
        return documents


class QuivrQARAG:
    def __init__(
        self,
        *,
        rag_config: RAGConfig,
        llm: LLMEndpoint,
        vector_store: VectorStore,
        reranker: BaseDocumentCompressor | None = None,
    ):
        self.rag_config = rag_config
        self.vector_store = vector_store
        self.llm_endpoint = llm
        self.reranker = reranker if reranker is not None else IdempotentCompressor()

    @property
    def retriever(self):
        return self.vector_store.as_retriever()

    def filter_history(
        self,
        chat_history: ChatHistory,
    ):
        """
        Filter out the chat history to only include the messages that are relevant to the current question

        Takes in a chat_history= [HumanMessage(content='Qui est Chloé ? '), AIMessage(content="Chloé est une salariée travaillant pour l'entreprise Quivr en tant qu'AI Engineer, sous la direction de son supérieur hiérarchique, Stanislas Girard."), HumanMessage(content='Dis moi en plus sur elle'), AIMessage(content=''), HumanMessage(content='Dis moi en plus sur elle'), AIMessage(content="Désolé, je n'ai pas d'autres informations sur Chloé à partir des fichiers fournis.")]
        Returns a filtered chat_history with in priority: first max_tokens, then max_history where a Human message and an AI message count as one pair
        a token is 4 characters
        """
        total_tokens = 0
        total_pairs = 0
        filtered_chat_history: list[AIMessage | HumanMessage] = []
        for human_message, ai_message in chat_history.iter_pairs():
            # TODO: replace with tiktoken
            message_tokens = (len(human_message.content) + len(ai_message.content)) // 4
            if (
                total_tokens + message_tokens > self.rag_config.llm_config.max_tokens
                or total_pairs >= self.rag_config.max_history
            ):
                break
            filtered_chat_history.append(human_message)
            filtered_chat_history.append(ai_message)
            total_tokens += message_tokens
            total_pairs += 1

        return filtered_chat_history[::-1]

    def should_continue(self, state):
        messages = state["messages"]
        last_message = messages[-1]
        # Make sure there is a previous message

        if last_message.tool_calls:
            name = last_message.tool_calls[0]["name"]
            if name == "image-generator":
                return "final"
        # If there is no function call, then we finish
        if not last_message.tool_calls:
            return "end"
        # Otherwise if there is, we check if it's suppose to return direct
        else:
            return "continue"


    def build_chain(self, files: str):
        logger.info("calling build chain")
        compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.reranker, base_retriever=self.retriever
        )
    
        loaded_memory = RunnablePassthrough.assign(
            chat_history=RunnableLambda(
                lambda x: self.filter_history(x["chat_history"]),
            ),
            question=lambda x: x["question"],
        )

        standalone_question = {
            "standalone_question": {
                "question": lambda x: x["question"],
                "chat_history": itemgetter("chat_history"),
            }
            | CONDENSE_QUESTION_PROMPT
            | self.llm_endpoint._llm
            | StrOutputParser(),
        }

        # Now we retrieve the documents
        retrieved_documents = {
            "docs": itemgetter("standalone_question") | compression_retriever,
            "question": lambda x: x["standalone_question"],
            "custom_instructions": lambda x: self.rag_config.prompt,
        }

        final_inputs = {
            "context": lambda x: combine_documents(x["docs"]),
            "question": itemgetter("question"),
            "custom_instructions": itemgetter("custom_instructions"),
            "date": lambda x: datetime.now().strftime("%B %d, %Y"),
            "files": lambda _: files,  # TODO: shouldn't be here
        }

        # Bind the llm to cited_answer if model supports it
        llm = self.llm_endpoint._llm

        if self.llm_endpoint.supports_func_calling():
            logger.info("the llm model supports func calling ")
            llm = self.llm_endpoint._llm.bind_tools(
                [*ToolMap.values(),
                    cited_answer
                ],
            )
        answer = {
            "answer": final_inputs | get_answer_prompt(self.rag_config.prompt) | llm,
            "docs": itemgetter("docs"),
        }

        return loaded_memory | standalone_question | retrieved_documents | answer


    async def parse_tool_call(self, raw_llm_response, question, history, chain):

            for tool in raw_llm_response["answer"].tool_calls:
                    print(tool["args"], 290)
                    if "function" in tool:
                        f_name = tool["function"]['name']
                        args = tool["function"]['arguments']
                    else:
                        f_name = tool["name"]
                        args = tool["args"]
                    if f_name in ToolMap:
                        logger.info(f"Starting tool: {f_name} with inputs: {args}")
                        try:
                            output = await ToolMap[f_name].ainvoke(args)

                            print(output)
                            history.append(ToolMessage(content=f"Here is the output: {output}", tool_call_id=tool['id']))
                        except Exception as e:
                            print(e)
                            history.append(ToolMessage(content=f"An error occured: {e}", tool_call_id=tool['id']))
#            if raw_llm_response["answer"].tool_calls:
 #               return await self.parse_tool_call(raw_llm_response, question,  history, chain)

            return raw_llm_response, history


    async def answer(
        self,
        question: str,
        history: ChatHistory,
        list_files: list[QuivrKnowledge],
        metadata: dict[str, str] = {},
    ) -> ParsedRAGResponse:
        concat_list_files = format_file_list(list_files, self.rag_config.max_files)
        conversational_qa_chain = self.build_chain(concat_list_files)

        print("history:", history.get_chat_history())
        print("question:", question)
        print("cnf:", self.rag_config.prompt)
        print(conversational_qa_chain) 

        raw_llm_response = conversational_qa_chain.invoke(
            {
                "question": question,
                "chat_history": history,
                "custom_instructions": (self.rag_config.prompt),
            },
            config={"metadata": metadata},
        )
        h_history = []

        if raw_llm_response and raw_llm_response["answer"].tool_calls and raw_llm_response["answer"].tool_calls[0]["name"] != "cited_answer":
            raw_llm_response, h_history = await self.parse_tool_call(raw_llm_response, question, h_history, conversational_qa_chain)

        from langchain_groq import ChatGroq

        chat = ChatGroq(
            api_key="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",
            model="llama3-groq-8b-8192-tool-use-preview",
            temperature=0.5     
        )
        print(f"{raw_llm_response=}")

       # chat = chat.bind_tools(ToolMap.values())
        response = chat.invoke(
            [
                SystemMessage(content="""You are a Chat Analyst. Your task is to review the response generated by the AI model and provide feedback in JSON format on the quality of the response. If the response is not up to the mark, you can provide a valid and proper response for the query. \n\nPlease provide the feedback on the response generated by the AI model. \n\n"""),
                SystemMessage(content="Also, make sure the response generated is more human like, be charming and engaging with the people!. If the response of AI is unclear and AI does not have enough context, generate a response on the behalf of AI model, follow the prompt instructions and make sure, the generated response is valid"),
                SystemMessage(
                    content=f"AI model was given the following prompt:\n\n'''{self.rag_config.prompt}'''\n\nThe AI model was asked the following question:\n\n'''{question}\n\nbased on the prompt and question provided to the AI model, validate the response generated by the AI model. if the response is not up to the mark, provide a valid and proper response for the query."),
                SystemMessage(content='Provide a JSON response with format: {"feedback": "Your feedback here", "response": "Your response here"}\n\nDont include anything extra other than JSON response.'),
                SystemMessage(content="You are also the head of the AI, and its your responsibility to make sure proper ability is used, since the AI is community assistant, It has power of managing, updating and organizing the community. Which makes it lot cruicial to provide the right information to the user. Process through the operation, user is asking for and provide approval for execution only if it is valid"),
                SystemMessage(content="The AI model has generated the following response: \n\n" + raw_llm_response["answer"].content),
                *h_history
            ]
        )

        print(f"{response=}")
        try:
            response.content = json.loads(response.content)['response']
        except Exception as e:
            print(e)

        response = {"answer": response, "docs": raw_llm_response.get("docs", [])}

        # if raw_llm_response["answer"].tool_calls:
        #     raw_llm_response = await conversational_qa_chain.ainvoke({
        #         "question": question,
        #         "chat_history": history,
        #         "custom_instructions": (self.rag_config.prompt),
        #     },
        #     config={"metadata": metadata},)
        #     raw_llm_response = await self.parse_tool_call(raw_llm_response, question, history, conversational_qa_chain)
    
        response = parse_response(response, self.rag_config.llm_config.model)
        return response


    def create_graph(self):
        # Define a new graph
        workflow = StateGraph(AgentState)

        # Define the two nodes we will cycle between
        workflow.add_node("agent", self.call_model)
        workflow.add_node("action", self.call_tool)
        workflow.add_node("final", self.call_tool)

        # Set the entrypoint as `agent`
        # This means that this node is the first one called
        workflow.set_entry_point("agent")

        # We now add a conditional edge
        workflow.add_conditional_edges(
            # First, we define the start node. We use `agent`.
            # This means these are the edges taken after the `agent` node is called.
            "agent",
            # Next, we pass in the function that will determine which node is called next.
            self.should_continue,
            # Finally we pass in a mapping.
            # The keys are strings, and the values are other nodes.
            # END is a special node marking that the graph should finish.
            # What will happen is we will call `should_continue`, and then the output of that
            # will be matched against the keys in this mapping.
            # Based on which one it matches, that node will then be called.
            {
                # If `tools`, then we call the tool node.
                "continue": "action",
                # Final call
                "final": "final",
                # Otherwise we finish.
                "end": END,
            },
        )

        # We now add a normal edge from `tools` to `agent`.
        # This means that after `tools` is called, `agent` node is called next.
        workflow.add_edge("action", "agent")
        workflow.add_edge("final", END)

        # Finally, we compile it!
        # This compiles it into a LangChain Runnable,
        # meaning you can use it as you would any other runnable
        app = workflow.compile()
        return app

    async def answer_astream(
        self,
        question: str,
        history: ChatHistory,
        list_files: list[QuivrKnowledge],
        metadata: dict[str, str] = {},
    ) -> AsyncGenerator[ParsedRAGChunkResponse, ParsedRAGChunkResponse]:
        concat_list_files = format_file_list(list_files, self.rag_config.max_files)
        conversational_qa_chain = self.build_chain(concat_list_files)
        logger.info(f"using chat history: {history}")
        rolling_message = AIMessageChunk(content="")
        sources = []
        prev_answer = ""
        chunk_id = 0
        print(history)

        async for event in conversational_qa_chain.astream_events(
            {
                "question": question,
                "chat_history": history,
                "custom_personality": (self.rag_config.prompt),
            },
            config={"metadata": metadata},
            version="v1",

        ):
            kind = event["event"]
            print(event)

            if kind == "on_chat_model_stream":
                # Could receive this anywhere so we need to save it for the last chunk
                chunk = event["data"]["chunk"]
                print(chunk, 287)
                if "docs" in chunk:
                    sources = chunk["docs"] if "docs" in chunk else []

                if "answer" in chunk:
                    rolling_message, answer_str = parse_chunk_response(
                        rolling_message,
                        chunk,
                        self.llm_endpoint.supports_func_calling(),
                    )

                    if len(answer_str) > 0:
                        if self.llm_endpoint.supports_func_calling():
                            diff_answer = answer_str[len(prev_answer) :]
                            if len(diff_answer) > 0:
                                parsed_chunk = ParsedRAGChunkResponse(
                                    answer=diff_answer,
                                    metadata=RAGResponseMetadata(),
                                )
                                prev_answer += diff_answer

                                logger.debug(
                                    f"answer_astream func_calling=True question={question} rolling_msg={rolling_message} chunk_id={chunk_id}, chunk={parsed_chunk}"
                                )
                                yield parsed_chunk
                        else:
                            parsed_chunk = ParsedRAGChunkResponse(
                                answer=answer_str,
                                metadata=RAGResponseMetadata(),
                            )
                            logger.debug(
                                f"answer_astream func_calling=False question={question} rolling_msg={rolling_message} chunk_id={chunk_id}, chunk={parsed_chunk}"
                            )
                            yield parsed_chunk

                        chunk_id += 1

                content = chunk.content

            elif kind == "on_tool_start":
                print("--")
                print(
                    f"Starting tool: {event['name']} with inputs: {event['data'].get('input')}"
                )
            elif kind == "on_tool_end":
                print(f"Done tool: {event['name']}")
                print(f"Tool output was: {event['data'].get('output')}")
                print("--")

            elif kind == "on_chain_end":
                output = event["data"]["output"]
                final_output = [item for item in output if "final" in item]
                print(final_output)
                # if final_output:
                #     if (
                #         final_output[0]["final"]["messages"][0].name
                #         == "image-generator"
                #     ):
                #         final_message = final_output[0]["final"]["messages"][0].content
                #         response_tokens.append(final_message)
                #         streamed_chat_history.assistant = final_message
                #         yield f"data: {json.dumps(streamed_chat_history.dict())}"


            
        # Last chunk provides metadata
        last_chunk = ParsedRAGChunkResponse(
            answer="",
            metadata=get_chunk_metadata(rolling_message, sources),
            last_chunk=True,
        )
        logger.debug(
            f"answer_astream last_chunk={last_chunk} question={question} rolling_msg={rolling_message} chunk_id={chunk_id}"
        )
        yield last_chunk
