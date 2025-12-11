from fastapi import FastAPI,UploadFile,File,Form
from pydantic import BaseModel,Field
from typing import Optional,Annotated
import os
import sys
from pathlib import Path
from utils.read_file import read_file

import uuid
from src.flow import MultiModalFlow
from langchain_core.messages import BaseMessage,HumanMessage,AIMessage,SystemMessage
from settings.logger import Logger

logger=Logger.get_logger(__name__)
logger.info("Server started")


app=FastAPI()
agent= MultiModalFlow()
SESSION_STORE={} 

@app.post("/send")
async def send_message(query: str=Form(...),file: Optional[UploadFile]=File(None),session_id: Optional[str]=Form(None)): 
    extract_text=""
    apend_txt=""
    if file:
        logger.info(f"Received file: {file.filename} of type {file.content_type}")
        extract_text=await read_file(file)
    if not session_id:
        session_id=str(uuid.uuid4())
        
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id]=[]
    
    chat_history=SESSION_STORE[session_id]
    if extract_text:
        apend_txt='\n User Provided:' + extract_text + '\n'
    chat_history.append(HumanMessage(content=query+apend_txt))
    result= agent.run(user_query=query,history=chat_history,extracted_text=extract_text)
    
    response_text=result["final_response"]
    
    chat_history.append(AIMessage(content=response_text))
    SESSION_STORE[session_id] = chat_history
    logger.info(f"Session {session_id} updated. \n Current Session State: {SESSION_STORE[session_id]}")
    return {
        "session_id": session_id,
        "response": response_text
    }
if __name__=="__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0",port=8963)