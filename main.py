from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.responses import JSONResponse
from db import get_db, engine
import models as models
import schemas as schemas
from repositories import UserRepo, MessageRepo, AnalysisRepo
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
import whisper
import os
import uvicorn
import json
import time
from tempfile import NamedTemporaryFile
from websocket_pool import ConnectionManager
from ai import SessionManager, send_to_gemini, analyse_from_gemini

manager = ConnectionManager()
ai_manager = SessionManager()

model = whisper.load_model('base')

app = FastAPI(title="Sample FastAPI Application",
              description="Sample FastAPI Application with Swagger and Sqlalchemy",
              version="1.0.0",)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)

DEFAULT_USER_NAME = "Anonymous"

DEFAULT_FLAGS = "task, fact, inconsistency, suspicious"


@app.exception_handler(Exception)
def validation_exception_handler(request, err):
    base_error_message = f"Failed to execute: {request.method}: {request.url}"
    return JSONResponse(status_code=400, content={"message": f"{base_error_message}. Detail: {err}"})


@app.get('/')
async def hello():
    return {"hey": "hi"}


@app.post('/call/transcribe')
def transcribe(file: UploadFile):
    start_time = time.time()
    temp = NamedTemporaryFile(delete=False)
    try:
        try:
            contents = file.file.read()
            with temp as f:
                f.write(contents)
        except Exception:
            raise HTTPException(
                status_code=500, detail='Error on uploading the file')
        finally:
            file.file.close()
        print("Time took to do file stuff {} sec".format(
            time.time() - start_time))
        start_time = time.time()
        result = model.transcribe(temp.name, fp16=False)
        print("Time took to process the request and return response is {} sec".format(
            time.time() - start_time))
        return {"transcript": result["text"]}

    except Exception:
        raise HTTPException(status_code=500, detail='Something went wrong')
    finally:
        # temp.close()  # the `with` statement above takes care of closing the file
        os.remove(temp.name)  # Delete temp file


@app.post('/post/{channel_id}/{user_id}')
async def post_message(channel_id, user_id, file: UploadFile, background_tasks: BackgroundTasks, flags: str | None = None, db: Session = Depends(get_db)):
    transcript = transcribe(file)["transcript"]
    msg = await MessageRepo.create(db, schemas.Message(transcript, user_id, channel_id))
    user = UserRepo.fetch_by_id(db, user_id)
    if user:
        msg.username = user.name
    else:
        msg.username = DEFAULT_USER_NAME
    if not flags:
        flags = DEFAULT_FLAGS
    background_tasks.add_task(
        send_to_gemini, msg, flags, ai_manager, manager, db)
    await manager.broadcast(json.dumps(jsonable_encoder(msg)), channel_id)
    return msg


@app.post('/{channel_id}/analyse')
async def analysis(channel_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Check if last message on the channel is the same as analysis
    # if it is then push last analysis to socket
    last = AnalysisRepo.fetch_latest(db, channel_id)
    if last and MessageRepo.fetch_by_channel(db, channel_id, 0, 1)[0].id == last.last_message_id:
        await manager.broadcast(json.dumps(jsonable_encoder({"summary": last.summary})), channel_id)
    else:
        background_tasks.add_task(
            analyse_from_gemini, channel_id, ai_manager, manager, db)


@app.get('/user/get')
async def get_user_id(name: str, db: Session = Depends(get_db)):
    return (await UserRepo.get_or_create(db, name)).id


@app.get('/{channel_id}/report')
def get_conversation(channel_id, db: Session = Depends(get_db)):
    msgs = MessageRepo.fetch_by_channel(db, channel_id)
    for msg in msgs:
        user = UserRepo.fetch_by_id(db, msg.sender_id)
        if user:
            msg.username = user.name
        else:
            msg.username = "Anonymous"
    return msgs


@app.websocket("/ws/{channel_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, channel_id: str, user_id: int):
    await manager.connect(channel_id, websocket)
    try:
        while True:
            # This is dummy, we never expect the client to send anything
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{user_id} left the chat", channel_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
