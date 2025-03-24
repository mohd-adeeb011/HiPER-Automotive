# HiPER-Automotive

# File Handling REST API

This is a FastAPI-based REST API for handling file uploads and downloads with support for resumable uploads, partial downloads, and real-time file status monitoring. The API is designed to be secure, efficient, and reliable for managing file transfers between remote devices and a server.

## Features

### Resumable File Uploads:
- Files can be uploaded in small chunks.
- Supports resuming interrupted uploads.
- Persists partial uploads to disk.

### Partial File Downloads:
- Supports HTTP Content-Range headers for partial downloads.
- Efficiently streams large files.

### Real-Time File Status Monitoring:
- Check the status of file uploads (complete, partial, or pending).
- Provides the next expected byte for resuming uploads.

### Background Cleanup:
- Automatically cleans up stale upload sessions.
- Moves incomplete uploads to permanent storage after a timeout.

### Security:
- Token-based authentication (JWT) for secure access.
- Only authorized devices can upload or download files.

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- FastAPI
- Uvicorn (ASGI server)
- Python dependencies (listed in `requirements.txt`)

### Installation

#### Clone the repository:
```bash
git clone https://github.com/your-repo/file-handling-api.git
cd file-handling-api
```

#### Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### Install dependencies:
```bash
pip install -r requirements.txt
```

#### Set up environment variables:
Create a `.env` file in the root directory with the following content:
```env
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
TEMP_UPLOAD_DIR=temp_uploads
PERM_UPLOAD_DIR=perm_uploads
CLEANUP_INTERVAL=3600
STALE_THRESHOLD=3600
```

#### Run the application:
```bash
uvicorn app.main:app --reload
```

#### Access the API documentation:
Open your browser and navigate to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to view the Swagger UI.

## API Endpoints

### 1. Upload File
- **Endpoint:** `POST /upload`
- **Description:** Uploads a file in chunks. Supports resumable uploads.
- **Headers:**
  - `Authorization: Bearer <token>`
- **Parameters:**
  - `filename`: Name of the file.
  - `total_size`: Total size of the file in bytes.
- **Request Body:**
  - Binary data with a custom header (start byte, end byte, checksum).
- **Response:**
  - `next_expected_byte`: The next byte expected for resuming uploads.

### 2. Check File Status
- **Endpoint:** `GET /files/{filename}/status`
- **Description:** Checks the status of a file upload.
- **Headers:**
  - `Authorization: Bearer <token>`
- **Response:**
  - `status`: Upload status (pending, complete).
  - `next_expected_byte`: Next byte expected for resuming.
  - `last_updated`: Timestamp of the last update.

### 3. Download File
- **Endpoint:** `GET /files/{filename}`
- **Description:** Downloads a file or a portion of it.
- **Headers:**
  - `Authorization: Bearer <token>`
  - `Range`: Optional. Specifies the byte range for partial downloads.
- **Response:**
  - File content or partial content with `Content-Range` header.

## Design Decisions

### Resumable Uploads:
- Files are uploaded in chunks with a custom header containing start/end bytes and a checksum.
- Partial uploads are stored in a temporary directory and reassembled once complete.
- The API tracks the next expected byte for each upload session.

### Partial Downloads:
- The API supports HTTP Content-Range headers for efficient handling of large files.
- Files are streamed using FastAPI's `StreamingResponse`.

### Background Cleanup:
- A background task periodically checks for stale upload sessions.
- Incomplete uploads older than the `STALE_THRESHOLD` are moved to permanent storage.

### Security:
- Token-based authentication (JWT) ensures only authorized devices can access the API.
- All file operations are validated to prevent unauthorized access.

### Asynchronous Operations:
- FastAPI's asynchronous capabilities are leveraged for efficient I/O operations.
- File uploads and downloads are handled asynchronously to improve performance.

## Assumptions

### File Chunks:
Each file chunk includes a custom binary header with:
- Start byte (4 bytes)
- End byte (4 bytes)
- Checksum (1 byte, sum of bytes modulo 256)

### Connectivity:
- Devices may experience intermittent connectivity.
- The API is designed to handle interruptions gracefully.

### Storage:
- Partial uploads are stored in a temporary directory (`temp_uploads`).
- Completed files are moved to a permanent directory (`perm_uploads`).

### Scalability:
- The current implementation uses an in-memory database for tracking upload sessions.
- For production, this can be replaced with a distributed database like Redis.

## Example Usage

### Upload a File
1. Split the file into chunks (e.g., 1 MB each).
2. For each chunk, send a `POST` request to `/upload` with the custom header and chunk data.

### Check Upload Status
- Send a `GET` request to `/files/{filename}/status` to check the upload progress.

### Download a File
- Send a `GET` request to `/files/{filename}`.
- Use the `Range` header to download specific portions of the file.

## Future Enhancements
- **Cloud Integration:** Replace local storage with cloud storage solutions (e.g., AWS S3, Google Cloud Storage).
- **Distributed Tracking:** Use Redis or another distributed database for tracking upload sessions.
- **Rate Limiting:** Implement rate limiting to prevent abuse.
- **File Encryption:** Add support for encrypting files at rest.
