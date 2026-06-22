from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fitness_log import FitnessLog
from app.schemas.fitness_log import StreakInfo


async def calculate_streak(db: AsyncSession) -> StreakInfo:
    result = await db.execute(
        select(FitnessLog.date)
        .where(FitnessLog.streak_impact.is_(True))
        .distinct()
        .order_by(FitnessLog.date.desc())
    )
    activity_dates = {row[0] for row in result.all()}

    if not activity_dates:
        return StreakInfo(current_streak=0, last_activity_date=None, at_risk=True)

    today = date.today()
    yesterday = today - timedelta(days=1)
    last_activity = max(activity_dates)

    if last_activity < yesterday:
        return StreakInfo(current_streak=0, last_activity_date=last_activity, at_risk=True)

    streak = 0
    check_date = last_activity
    while check_date in activity_dates:
        streak += 1
        check_date -= timedelta(days=1)

    at_risk = last_activity == yesterday
    return StreakInfo(current_streak=streak, last_activity_date=last_activity, at_risk=at_risk)


async def get_heatmap_data(db: AsyncSession, days: int = 365) -> dict[str, int]:
    since = date.today() - timedelta(days=days)
    result = await db.execute(
        select(FitnessLog.date, func.count(FitnessLog.id))
        .where(FitnessLog.date >= since, FitnessLog.streak_impact.is_(True))
        .group_by(FitnessLog.date)
    )
    return {row[0].isoformat(): row[1] for row in result.all()}
