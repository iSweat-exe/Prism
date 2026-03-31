from fastapi import APIRouter

router = APIRouter()

@router.get("")
def api_info():
    return {
        "name": "PrismAPI",
        "version": "1.0.0",
        "status": "running"
    }