import json
import logging
import os
from pathlib import Path

import firebase_admin
from firebase_admin import auth, credentials, firestore_async
from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK once
if not firebase_admin._apps:
    try:
        raw_val = settings.firebase_service_account_json.strip()
        
        # Check if it's a file path
        if os.path.isfile(raw_val):
            logger.info(f"Loading Firebase credentials from file path: {raw_val}")
            cred = credentials.Certificate(raw_val)
        # Check if serviceAccountKey.json exists in root
        elif os.path.isfile("serviceAccountKey.json"):
            logger.info("Found serviceAccountKey.json in working directory.")
            cred = credentials.Certificate("serviceAccountKey.json")
        else:
            # Try to parse as JSON string
            # Handle accidental leading/trailing single/double quotes around the entire JSON
            if (raw_val.startswith("'") and raw_val.endswith("'")) or (raw_val.startswith('"') and raw_val.endswith('"')):
                raw_val = raw_val[1:-1].strip()
            
            service_account_info = json.loads(raw_val)
            cred = credentials.Certificate(service_account_info)
            
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        raise RuntimeError(
            f"Firebase initialization failed: {e}\n"
            f"Tip: You can simply copy your downloaded JSON file into 'backend/serviceAccountKey.json' "
            f"and set FIREBASE_SERVICE_ACCOUNT_JSON=serviceAccountKey.json in .env"
        ) from e

# Firestore async client
db = firestore_async.client()


async def verify_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the decoded token payload."""
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid token. Please log in again.")
    except auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="Token has been revoked. Please log in again.")
    except Exception as e:
        logger.warning(f"Token verification failed: {type(e).__name__}")
        raise HTTPException(status_code=401, detail="Authentication failed. Please log in again.")
