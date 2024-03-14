from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends, FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from db import get_db, engine
import models as models
import schemas as schemas
from repositories import UserRepo, MessageRepo
from sqlalchemy.orm import Session
import uvicorn
from typing import List, Optional
from fastapi.encoders import jsonable_encoder
import whisper
import os
import json
import time
from tempfile import NamedTemporaryFile
from websocket_pool import ConnectionManager

manager = ConnectionManager()

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

        result = model.transcribe(temp.name, fp16=False)
        print("Time took to process the request and return response is {} sec".format(
            time.time() - start_time))
        return {"transcript": result["text"]}

    except Exception:
        raise HTTPException(status_code=500, detail='Something went wrong')
    finally:
        # temp.close()  # the `with` statement above takes care of closing the file
        os.remove(temp.name)  # Delete temp file


@app.post('/{channel_id}/{user_id}/post')
async def post_message(channel_id, user_id, file: UploadFile, db: Session = Depends(get_db)):
    transcript = transcribe(file)["transcript"]
    msg = await MessageRepo.create(db, schemas.Message(transcript, user_id, channel_id))
    await manager.broadcast(json.dumps(jsonable_encoder(msg)), channel_id)
    return msg


@app.get('/user/get')
async def get_user_id(name: str, db: Session = Depends(get_db)):
    return (await UserRepo.get_or_create(db, name)).id


@app.get('/{channel_id}/report')
def get_conversation(channel_id, db: Session = Depends(get_db)):
    return MessageRepo.fetch_by_channel(db, channel_id)


@app.websocket("/ws/{channel_id}/{user_id}/")
async def websocket_endpoint(websocket: WebSocket, channel_id: str, user_id: int):
    await manager.connect(channel_id, websocket)
    try:
        while True:
            # This is dummy, we never expect the client to send anything
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{user_id} left the chat", channel_id)
