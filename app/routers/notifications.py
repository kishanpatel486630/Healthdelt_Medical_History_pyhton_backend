from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Notification

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifications = (
        db.query(Notification)
        .filter(Notification.userId == current_user.id)
        .order_by(Notification.createdAt.desc())
        .limit(50)
        .all()
    )

    unread_count = db.query(Notification).filter(
        Notification.userId == current_user.id, Notification.isRead == False
    ).count()

    return {
        "success": True,
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "isRead": n.isRead,
                "actionUrl": n.actionUrl,
                "createdAt": n.createdAt.isoformat() if n.createdAt else None,
            }
            for n in notifications
        ],
        "unreadCount": unread_count,
    }


@router.put("/{notification_id}/read")
def mark_read(notification_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.id == notification_id, Notification.userId == current_user.id
    ).update({"isRead": True})
    db.commit()
    return {"success": True}


@router.put("/read-all")
def mark_all_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.userId == current_user.id, Notification.isRead == False
    ).update({"isRead": True})
    db.commit()
    return {"success": True, "message": "All notifications marked as read"}
