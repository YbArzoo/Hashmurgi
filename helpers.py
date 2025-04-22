from models import DeliveryIssue, User
from sqlalchemy import desc
from datetime import datetime, timedelta

def get_recent_issues(limit=5):
    """
    Get recent delivery issues for notifications
    """
    # Get issues from the last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    # Join with User to get reporter information
    issues = DeliveryIssue.query.join(
        User, DeliveryIssue.reported_by == User.id
    ).filter(
        DeliveryIssue.created_at >= seven_days_ago
    ).order_by(
        desc(DeliveryIssue.created_at)
    ).limit(limit).all()
    
    return issues
