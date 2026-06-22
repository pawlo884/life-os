from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import APPLIED_STATUS, JOB_STATUSES
from app.database import get_db
from app.models.fitness_log import FitnessLog
from app.models.job_application import JobApplication
from app.models.learning_progress import LearningProgress
from app.models.task import Task
from app.schemas.fitness_log import FitnessLogCreate, FitnessLogRead, StreakInfo
from app.schemas.job_application import JobApplicationCreate, JobApplicationRead, JobApplicationUpdate
from app.schemas.learning_progress import (
    LearningProgressCreate,
    LearningProgressRead,
    LearningProgressUpdate,
    ReadingEstimate,
    ReadingLogRequest,
)
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate
from app.services.reading import estimate_book_completion
from app.services.streak import calculate_streak, get_heatmap_data

router = APIRouter()


def _learning_with_percent(item: LearningProgress) -> LearningProgressRead:
    percent = 0.0
    if item.total_units > 0:
        percent = round((item.completed_units / item.total_units) * 100, 1)
    return LearningProgressRead(
        id=item.id,
        resource_type=item.resource_type,
        title=item.title,
        total_units=item.total_units,
        completed_units=item.completed_units,
        status=item.status,
        completion_percent=percent,
    )


# --- Tasks ---


@router.get("/tasks", response_model=list[TaskRead])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).order_by(Task.due_date.asc().nullslast()))
    return result.scalars().all()


@router.post("/tasks", response_model=TaskRead, status_code=201)
async def create_task(payload: TaskCreate, db: AsyncSession = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update_task(task_id: int, payload: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, key, value)
    await db.commit()
    await db.refresh(task)
    return task


# --- Job applications ---


@router.get("/jobs", response_model=list[JobApplicationRead])
async def list_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobApplication).order_by(JobApplication.applied_date.desc().nullslast()))
    return result.scalars().all()


@router.post("/jobs", response_model=JobApplicationRead, status_code=201)
async def create_job(payload: JobApplicationCreate, db: AsyncSession = Depends(get_db)):
    job = JobApplication(**payload.model_dump())
    if not job.applied_date and payload.status == APPLIED_STATUS:
        job.applied_date = date.today()
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.patch("/jobs/{job_id}", response_model=JobApplicationRead)
async def update_job(job_id: int, payload: JobApplicationUpdate, db: AsyncSession = Depends(get_db)):
    job = await db.get(JobApplication, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job application not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, key, value)
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/jobs/stats/weekly")
async def weekly_job_stats(db: AsyncSession = Depends(get_db)):
    week_start = date.today() - timedelta(days=date.today().weekday())
    result = await db.execute(
        select(func.count(JobApplication.id)).where(
            JobApplication.status == APPLIED_STATUS,
            JobApplication.applied_date >= week_start,
        )
    )
    sent_count = result.scalar() or 0
    kpi_target = 5
    return {
        "week_start": week_start.isoformat(),
        "applications_sent": sent_count,
        "kpi_target": kpi_target,
        "kpi_met": sent_count >= kpi_target,
        "statuses": JOB_STATUSES,
    }


# --- Learning ---


@router.get("/learning", response_model=list[LearningProgressRead])
async def list_learning(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LearningProgress).order_by(LearningProgress.id.desc()))
    return [_learning_with_percent(item) for item in result.scalars().all()]


@router.post("/learning", response_model=LearningProgressRead, status_code=201)
async def create_learning(payload: LearningProgressCreate, db: AsyncSession = Depends(get_db)):
    item = LearningProgress(**payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _learning_with_percent(item)


@router.patch("/learning/{item_id}", response_model=LearningProgressRead)
async def update_learning(
    item_id: int, payload: LearningProgressUpdate, db: AsyncSession = Depends(get_db)
):
    item = await db.get(LearningProgress, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Learning resource not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return _learning_with_percent(item)


@router.post("/learning/read", response_model=ReadingEstimate)
async def log_reading(payload: ReadingLogRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await estimate_book_completion(db, payload.pages, payload.title)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/learning/{course_title}/module/{module_name}")
async def complete_module(course_title: str, module_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(LearningProgress).where(
            LearningProgress.resource_type == "COURSE",
            LearningProgress.title.ilike(f"%{course_title}%"),
        )
    )
    course = result.scalar_one_or_none()
    if not course:
        course = LearningProgress(
            resource_type="COURSE",
            title=course_title,
            total_units=1,
            completed_units=1,
            status="IN_PROGRESS",
        )
        db.add(course)
    else:
        course.completed_units = min(course.completed_units + 1, course.total_units or course.completed_units + 1)
        if course.total_units and course.completed_units >= course.total_units:
            course.status = "COMPLETED"
    await db.commit()
    await db.refresh(course)
    return {
        "course": course.title,
        "module": module_name,
        "progress": _learning_with_percent(course),
    }


# --- Fitness ---


@router.get("/fitness", response_model=list[FitnessLogRead])
async def list_fitness(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(FitnessLog).order_by(FitnessLog.date.desc()))
    return result.scalars().all()


@router.post("/fitness", response_model=FitnessLogRead, status_code=201)
async def create_fitness(payload: FitnessLogCreate, db: AsyncSession = Depends(get_db)):
    log = FitnessLog(**payload.model_dump())
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


@router.get("/fitness/streak", response_model=StreakInfo)
async def get_streak(db: AsyncSession = Depends(get_db)):
    return await calculate_streak(db)


@router.get("/fitness/heatmap")
async def fitness_heatmap(days: int = Query(default=365, ge=30, le=730), db: AsyncSession = Depends(get_db)):
    return await get_heatmap_data(db, days)


# --- Daily report ---


@router.get("/report/daily")
async def daily_report(db: AsyncSession = Depends(get_db)):
    today = date.today()
    jobs_today = await db.execute(
        select(func.count(JobApplication.id)).where(
            JobApplication.applied_date == today,
            JobApplication.status == APPLIED_STATUS,
        )
    )
    streak = await calculate_streak(db)
    book_result = await db.execute(
        select(LearningProgress)
        .where(LearningProgress.resource_type == "BOOK", LearningProgress.status == "IN_PROGRESS")
        .order_by(LearningProgress.id.desc())
        .limit(1)
    )
    book = book_result.scalar_one_or_none()
    remaining_pages = None
    if book:
        remaining_pages = max(book.total_units - book.completed_units, 0)

    return {
        "date": today.isoformat(),
        "applications_sent_today": jobs_today.scalar() or 0,
        "fitness_streak_days": streak.current_streak,
        "streak_at_risk": streak.at_risk,
        "active_book": book.title if book else None,
        "remaining_book_pages": remaining_pages,
    }
