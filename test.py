import os
import requests
from pathlib import Path
import hashlib
from requests.auth import HTTPBasicAuth

# Configuration
BASE_URL = "http://localhost:8000"
AUTH_URL = f"{BASE_URL}/token"  # Update if your auth endpoint is different
USERNAME = "testuser"           # Use your actual test credentials
PASSWORD = "testpassword"       # Use your actual test credentials
TEST_FILE = "test_file.bin"     # File to upload
CHUNK_SIZE = 1024 * 1024        # 1MB chunks

# Helper functions
def get_auth_token():
    """Get JWT token for authentication"""
    # Try both common authentication methods
    try:
        response = requests.post(
            AUTH_URL,
            data={"username": USERNAME, "password": PASSWORD}
        )
        token = response.json().get("access_token")
        
        if token:
            return token
            
        response = requests.post(
            AUTH_URL,
            auth=HTTPBasicAuth(USERNAME, PASSWORD)
        )
        token = response.json().get("access_token")
        
        if token:
            return token
            
    except Exception as e:
        print(f"Authentication failed: {str(e)}")
        print("Response:", response.text)
        raise

    raise ValueError("Could not obtain access token. Check your auth endpoint and credentials")

def create_chunk_header(start: int, end: int, chunk_data: bytes) -> bytes:
    """Create the 9-byte header as specified in requirements"""
    checksum = sum(chunk_data) % 256
    return (
        start.to_bytes(4, 'big') +
        end.to_bytes(4, 'big') +
        checksum.to_bytes(1, 'big')
    )

def upload_file(filename: str, token: str):
    """Upload file in chunks with proper headers"""
    file_size = os.path.getsize(filename)
    print(f"Starting upload of {filename} ({file_size} bytes)")
    
    with open(filename, 'rb') as f:
        chunk_num = 0
        while True:
            chunk_data = f.read(CHUNK_SIZE)
            if not chunk_data:
                break
                
            start = chunk_num * CHUNK_SIZE
            end = start + len(chunk_data) - 1
            header = create_chunk_header(start, end, chunk_data)
            
            try:
                response = requests.post(
                    f"{BASE_URL}/upload?filename={os.path.basename(filename)}&total_size={file_size}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/octet-stream"
                    },
                    data=header + chunk_data
                )
                response.raise_for_status()
                print(f"Uploaded chunk {chunk_num} (bytes {start}-{end}): {response.json()}")
                
            except requests.exceptions.RequestException as e:
                print(f"Failed to upload chunk {chunk_num}: {str(e)}")
                if hasattr(e, 'response') and e.response:
                    print("Server response:", e.response.text)
                return False
                
            chunk_num += 1
    
    print("Upload completed successfully")
    return True

def download_file(filename: str, token: str, output_path: str):
    """Download complete file"""
    print(f"Downloading {filename}...")
    try:
        response = requests.get(
            f"{BASE_URL}/files/{filename}",
            headers={"Authorization": f"Bearer {token}"},
            stream=True
        )
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"File successfully downloaded to {output_path}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Download failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print("Server response:", e.response.text)
        return False

def check_status(filename: str, token: str):
    """Check upload status"""
    print(f"Checking status for {filename}...")
    try:
        response = requests.get(
            f"{BASE_URL}/files/{filename}/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        status_info = response.json()
        print("File status:")
        print(f"- Status: {status_info.get('status')}")
        print(f"- Next expected byte: {status_info.get('next_expected_byte')}")
        print(f"- Last updated: {status_info.get('last_updated')}")
        return status_info
        
    except requests.exceptions.RequestException as e:
        print(f"Status check failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print("Server response:", e.response.text)
        return None

def verify_files(original: str, downloaded: str):
    """Verify file integrity using MD5 checksum"""
    print("\nVerifying file integrity...")
    
    def get_md5(filepath):
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    if not os.path.exists(original):
        print(f"Original file {original} not found")
        return False
        
    if not os.path.exists(downloaded):
        print(f"Downloaded file {downloaded} not found")
        return False
    
    orig_hash = get_md5(original)
    dl_hash = get_md5(downloaded)
    
    print(f"Original file MD5: {orig_hash}")
    print(f"Downloaded file MD5: {dl_hash}")
    
    if orig_hash == dl_hash:
        print("Files match perfectly!")
        return True
    else:
        print("Files differ!")
        return False

def test_partial_download(filename: str, token: str):
    """Test partial download with Range header"""
    print("\nTesting partial download...")
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Range": "bytes=0-999"  # First 1000 bytes
        }
        
        response = requests.get(
            f"{BASE_URL}/files/{filename}",
            headers=headers
        )
        response.raise_for_status()
        
        print("Partial download successful")
        print("Headers received:")
        for header, value in response.headers.items():
            print(f"{header}: {value}")
        print(f"Received {len(response.content)} bytes")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Partial download failed: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print("Server response:", e.response.text)
        return False

def main():
    # Create a test file if it doesn't exist
    if not os.path.exists(TEST_FILE):
        print(f"Creating test file {TEST_FILE}...")
        with open(TEST_FILE, 'wb') as f:
            f.write(os.urandom(5 * 1024 * 1024))  # 5MB random file
        print(f"Created {TEST_FILE} ({os.path.getsize(TEST_FILE)} bytes)")
    
    # Get auth token
    print("\nAuthenticating...")
    try:
        token = get_auth_token()
        print(f"Authentication successful (token: {token[:10]}...)")
    except Exception as e:
        print(f" Failed to authenticate: {str(e)}")
        print("Please check:")
        print("- Your API is running")
        print("- The auth endpoint is correct")
        print("- Your credentials are valid")
        return
    
    # Test upload
    print("\n=== Testing upload ===")
    if not upload_file(TEST_FILE, token):
        print("Upload test failed")
        return
    
    # Check status
    print("\n=== Checking status ===")
    status_info = check_status(os.path.basename(TEST_FILE), token)
    if not status_info:
        print("Status check failed")
        return
    
    # Test download
    print("\n=== Testing download ===")
    downloaded_file = "downloaded_" + os.path.basename(TEST_FILE)
    if not download_file(os.path.basename(TEST_FILE), token, downloaded_file):
        print("Download test failed")
        return
    
    # Verify integrity
    print("\n=== Verifying integrity ===")
    if not verify_files(TEST_FILE, downloaded_file):
        print("Integrity verification failed")
        return
    
    # Test partial download
    print("\n=== Testing partial download ===")
    if not test_partial_download(os.path.basename(TEST_FILE), token):
        print("Partial download test failed")
        return
    
    print("\nAll tests completed successfully!")

if __name__ == "__main__":
    main()
