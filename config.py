import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    UPLOAD_FOLDER = 'uploads'
    DATA_FOLDER = 'data'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # 確保目錄存在
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(DATA_FOLDER, exist_ok=True)