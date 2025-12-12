from typing import TypedDict, Annotated, Union,Literal,Optional,List
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage,AIMessage,BaseMessage
from settings.logger import Logger
from utils.yt_extract import ytube_transcript, extract_yt_url

logger =Logger.get_logger(__name__)
from dotenv import load_dotenv
load_dotenv()
class IntentResponse(BaseModel):
    """This Model captures the structured output from the LLM for intent classification."""
    intent: Literal[
        "summarize",
        "sentiment",
        "code_explain",
        "general_chat",
        "ambiguous"
    ]
class ChatBotState(TypedDict):
    user_query: str          
    extracted_text: str      
    metadata: dict           
    intent: str              
    final_response: str 
    chat_history: List[BaseMessage]
    
class MultiModalFlow():
    
    def __init__(self,):
        self.workflow=StateGraph(ChatBotState)
        self.llm= ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        self.build_graph()
        self.app =self.workflow.compile()
        self.history: List[BaseMessage]= []
        
    def router_node(self,state:ChatBotState):
        query=state['user_query'].lower()
        extracted_text= state['extracted_text'].lower()
        self.history =state.get("chat_history", [])
        logger.info(f"Router Node Invoked. Query: {query}, Extracted Text Length: {len(extracted_text)}")
        logger.debug(f"Chat History: {self.history}")
        
        # yt_url=extract_yt_url(query)
        # if yt_url:
        #     logger.info(f"YouTube URL detected in query: {yt_url}. Fetching transcript.")
        #     transcript_text= ytube_transcript(yt_url)
        #     extracted_text += "\n" + transcript_text
        #     logger.info(f"Transcript fetched and appended. New Extracted Text Length: {len(extracted_text)}")
        
        system_prompt=f"""
        You are the Brain of a Multi-Modal File Assistant.
        Your job is to classify the User's Intent based on their Query and the File Content.

        Context:
        - File Snippet: {extracted_text[:800]}...
        - Recent Chat History:
        {self.history[-10:]}
        
        Possible Intents:
        1. 'summarize' (User wants a summary)
        2. 'sentiment' (User wants sentiment analysis)
        3. 'code_explain' (User wants code explanation/debugging)
        4. 'general_chat' (User is saying hello or asking general questions unrelated to file)
        5. 'ambiguous' (The goal is unclear)

        CRITICAL RULES:
        - If the user provides a file but NO query (or an empty query), return 'ambiguous'.
        - If the user says vague things like "Check this", "Analyze", "What is this?", return 'ambiguous'.
        - If multiple tasks are equally plausible, return 'ambiguous'.
        
        Output ONLY one word from the list above.
        """

        user_msg=f"User Query: '{query}"
        
        llm_context=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_msg)
        ]
        structured_llm=self.llm.with_structured_output(IntentResponse)
        logger.info(f"Final LLM Context for Intent Classification: {llm_context}")
        logger.info("Invoking LLM for intent classification.")
        response=structured_llm.invoke(llm_context)
        logger.info(f"Intent Classified as: {response.intent}")
        return {**state, "intent": response.intent,"extracted_text": extracted_text}
    
    def clarification_node(self, state: ChatBotState):
        """
        Triggered when intent is 'ambiguous'. Asks a specific follow-up question.
        """
        system_prompt =f"""
        The user has provided input but the goal is unclear. 
        Generate a polite, short (1 sentence) follow-up question.
        
        Examples:
        - "Could you clarify if you want a summary or sentiment analysis?"
        - "What specific part of this code would you like me to explain?"
        - "Do you want me to summarize this audio file?"
        
        Recent Chat History:
        {self.history[-10:]}
        """
        
        response= self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=state.get("user_query", ""))
        ])
        
        return {"final_response": response.content}

    
    
    def executor_node(self, state: ChatBotState):
        """
        Performs the actual task (Summary, Sentiment, etc.) with STRICT formatting.
        """
        intent= state["intent"]
        text= state["extracted_text"]
        
        if intent =="summarize":
            task_prompt= """
            Task: Summarize the provided text.
            
            REQUIRED OUTPUT FORMAT:
            1. A 1-line summary.
            2. Exactly 3 bullet points highlighting key details.
            3. A 5-sentence summary paragraph.
            """
        elif intent=="sentiment":
            task_prompt="""
            Task: Analyze the sentiment of the text.
            
            REQUIRED OUTPUT FORMAT:
            1. Label (Positive / Negative / Neutral).
            2. Confidence Score (estimate between 0-100%).
            3. A one-line justification for this label.
            """
        elif intent=="code_explain":
            task_prompt = """
            Task: Explain the provided code snippet.
            
            REQUIRED OUTPUT FORMAT:
            1. Explanation: What does the code do?
            2. Bug Report: Detect and list any potential bugs or security issues.
            """
        elif intent=="general_chat":
            logger.info("General chat intent detected, Constructing prompt.")
            task_prompt= "You are a helpful Massistant. Answer the user's question directly."
        else:
            task_prompt="Process the request."
        sys_prompt_task=f"""{task_prompt}\n\nContext:\n{text[:1000]}..."""
        final_message=[SystemMessage(content=sys_prompt_task)]+self.history[-10:]
        logger.info(f"Executing intent: {intent} with context: {final_message}")
        response =self.llm.invoke(final_message)
        
        return {"final_response": response.content}
    
    
    def route_decision(self, state: ChatBotState):
        intent =state["intent"]
        if intent =="ambiguous":
            return "clarification_node"
        else:
            return "executor_node"
            
    def build_graph(self): 
        self.workflow.add_node("router_node", self.router_node)
        self.workflow.add_node("clarification_node", self.clarification_node)
        self.workflow.add_node("executor_node", self.executor_node)

        self.workflow.set_entry_point("router_node")

        self.workflow.add_conditional_edges(
            "router_node",
            self.route_decision,
            {
                "clarification_node": "clarification_node",
                "executor_node": "executor_node"
            }
        )
        self.workflow.add_edge("clarification_node", END)
        self.workflow.add_edge("executor_node", END)
    
    def run(self, user_query:str, history:List[BaseMessage],extracted_text:str):
        """
        The main entry point to call from FastAPI.
        """
        initial_state={
            "user_query": user_query,
            "extracted_text": extracted_text,
            "intent": "",
            "final_response": "",
            "chat_history": history
        }
        
       
        result=self.app.invoke(initial_state)
        return result
    
    
