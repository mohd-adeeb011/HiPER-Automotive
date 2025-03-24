from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import StreamingResponse, FileResponse
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import shutil
import uuid
import asyncio
from typing import Dict, Optional

from .auth import get_current_user
from .config import settings
from .schemas import User, TokenData
from .models import UploadSession, get_db, update_db, delete_from_db

app = FastAPI()

# Setup upload directories
Path(settings.TEMP_UPLOAD_DIR).mkdir(exist_ok=True)
Path(settings.PERM_UPLOAD_DIR).mkdir(exist_ok=True)

@app.post("/upload")
async def upload_file(
    request: Request,
    filename: str,
    total_size: int,
    user: User = Depends(get_current_user),
):
    data = await request.body()
    if len(data) < 9:
        raise HTTPException(status_code=400, detail="Invalid chunk header")

    header = data[:9]
    start = int.from_bytes(header[:4], 'big')
    end = int.from_bytes(header[4:8], 'big')
    checksum = header[8]
    chunk_data = data[9:]

    if (sum(chunk_data) % 256) != checksum:
        raise HTTPException(status_code=400, detail="Checksum mismatch")

    session_key = f"{user.username}_{filename}"
    db = get_db()

    if session_key in db:
        session = db[session_key]
        if session.total_size != total_size:
            raise HTTPException(status_code=400, detail="Total size mismatch")
        if session.status == "complete":
            raise HTTPException(status_code=400, detail="Upload already complete")
        if start != session.next_expected_byte:
            raise HTTPException(
                status_code=400,
                detail=f"Expected next byte {session.next_expected_byte}",
            )
    else:
        temp_file = Path(settings.TEMP_UPLOAD_DIR) / f"{session_key}_{uuid.uuid4()}"
        session = UploadSession(
            user_id=user.username,
            filename=filename,
            total_size=total_size,
            next_expected_byte=0,
            status="pending",
            temp_file=str(temp_file),
            last_updated=datetime.now(),
        )
        update_db(session_key, session)

    with open(session.temp_file, "ab") as f:
        f.write(chunk_data)

    session.next_expected_byte = end + 1
    session.last_updated = datetime.now()

    if session.next_expected_byte >= session.total_size:
        session.status = "complete"
        perm_file = Path(settings.PERM_UPLOAD_DIR) / filename
        shutil.move(session.temp_file, perm_file)
        delete_from_db(session_key)
    else:
        update_db(session_key, session)

    return {"next_expected_byte": session.next_expected_byte}

@app.get("/files/{filename}/status")
async def get_status(filename: str, user: User = Depends(get_current_user)):
    session_key = f"{user.username}_{filename}"
    db = get_db()
    if session_key not in db:
        return {"status": "not found"}
    session = db[session_key]
    return {
        "status": session.status,
        "next_expected_byte": session.next_expected_byte,
        "last_updated": session.last_updated.isoformat(),
    }

@app.get("/files/{filename}")
async def download_file(
    filename: str,
    request: Request,
    user: User = Depends(get_current_user),
):
    perm_file = Path(settings.PERM_UPLOAD_DIR) / filename
    if not perm_file.exists():
        raise HTTPException(status_code=404, detail="File not found")

    file_size = perm_file.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        start, end = parse_range_header(range_header, file_size)
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(end - start + 1),
            "Accept-Ranges": "bytes",
        }
        return StreamingResponse(
            file_chunk_generator(perm_file, start, end),
            status_code=206,
            headers=headers,
            media_type="application/octet-stream",
        )
    return FileResponse(perm_file)

def parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    try:
        _, ranges = range_header.split("=")
        start_str, end_str = ranges.split("-")
        start = int(start_str)
        end = int(end_str) if end_str else file_size - 1
        if start >= file_size or end >= file_size or start > end:
            raise ValueError
        return start, end
    except ValueError:
        raise HTTPException(
            status_code=416,
            detail="Requested range not satisfiable",
            headers={"Content-Range": f"bytes */{file_size}"},
        )

def file_chunk_generator(file_path: Path, start: int, end: int):
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk_size = min(4096, remaining)
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk
            remaining -= len(chunk)

async def cleanup_task():
    while True:
        await asyncio.sleep(settings.CLEANUP_INTERVAL)
        now = datetime.now()
        db = get_db()
        for session_key in list(db.keys()):
            session = db[session_key]
            if (now - session.last_updated).total_seconds() > settings.STALE_THRESHOLD:
                if session.status == "pending":
                    perm_file = Path(settings.PERM_UPLOAD_DIR) / session.filename
                    shutil.move(session.temp_file, perm_file)
                delete_from_db(session_key)

@app.on_event("startup")
async def startup():
    asyncio.create_task(cleanup_task())