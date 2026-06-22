import logging
from datetime import datetime, timedelta

import discord
import httpx
from dateutil import parser as date_parser
from discord import app_commands
from discord.ext import commands

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lifeos-bot")

ACTIVITY_MAP = {
    "gym": "GYM",
    "strength": "GYM",
    "core": "CORE",
    "swim": "SWIM",
    "swimming": "SWIM",
    "run": "RUN",
    "running": "RUN",
    "bike": "BIKE",
    "cycling": "BIKE",
}

JOB_STATUS_MAP = {
    "to_apply": "to_apply",
    "applied": "applied",
    "sent": "applied",
    "hr": "hr_interview",
    "hr_interview": "hr_interview",
    "tech": "tech_interview",
    "tech_interview": "tech_interview",
    "take_home": "take_home",
    "assignment": "take_home",
    "rejected": "rejected",
    "offer": "offer",
}


class LifeOSBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.api = settings.api_base_url

    async def setup_hook(self):
        guild = discord.Object(id=settings.discord_guild_id) if settings.discord_guild_id else None
        if guild:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        logger.info("Slash commands synced")


bot = LifeOSBot()


def parse_due_date(text: str) -> datetime | None:
    lowered = text.lower().strip()
    now = datetime.now()
    if lowered in ("today",):
        return now.replace(hour=15, minute=0, second=0, microsecond=0)
    if lowered in ("tomorrow",):
        target = now + timedelta(days=1)
        return target.replace(hour=15, minute=0, second=0, microsecond=0)
    try:
        return date_parser.parse(text, dayfirst=True)
    except (ValueError, TypeError):
        return None


async def api_post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{bot.api}{path}", json=payload)
        response.raise_for_status()
        return response.json()


async def api_get(path: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{bot.api}{path}")
        response.raise_for_status()
        return response.json()


@bot.tree.command(name="task", description="Add a task with a due date")
@app_commands.describe(title="Task title", due="Date/time, e.g. tomorrow 3pm")
async def task_command(interaction: discord.Interaction, title: str, due: str):
    await interaction.response.defer(ephemeral=True)
    due_date = parse_due_date(due)
    payload = {
        "title": title,
        "due_date": due_date.isoformat() if due_date else None,
        "status": "TODO",
        "is_sla_critical": False,
    }
    try:
        result = await api_post("/tasks", payload)
        await interaction.followup.send(
            f"Task added: **{result['title']}**"
            + (f" (due: {due_date.strftime('%Y-%m-%d %H:%M')})" if due_date else "")
        )
    except httpx.HTTPError as exc:
        await interaction.followup.send(f"API error: {exc}")


@bot.tree.command(name="workout", description="Log a manual workout")
@app_commands.describe(type="e.g. gym, core, swim, run", duration="Duration in minutes")
async def workout_command(interaction: discord.Interaction, type: str, duration: int):
    await interaction.response.defer(ephemeral=True)
    activity = ACTIVITY_MAP.get(type.lower(), type.upper())
    payload = {
        "source": "DISCORD_MANUAL",
        "activity_type": activity,
        "duration_minutes": duration,
        "date": datetime.now().date().isoformat(),
        "streak_impact": True,
    }
    try:
        await api_post("/fitness", payload)
        streak = await api_get("/fitness/streak")
        await interaction.followup.send(
            f"Workout logged: **{activity}** ({duration} min). Streak: **{streak['current_streak']}** days."
        )
    except httpx.HTTPError as exc:
        await interaction.followup.send(f"API error: {exc}")


@bot.tree.command(name="read", description="Log pages read")
@app_commands.describe(pages="Number of pages")
async def read_command(interaction: discord.Interaction, pages: int):
    await interaction.response.defer(ephemeral=True)
    try:
        result = await api_post("/learning/read", {"pages": pages})
        eta = result.get("estimated_completion_date") or "n/a"
        await interaction.followup.send(
            f"**{result['title']}**: +{pages} pages. "
            f"Remaining: {result['remaining_pages']}. Estimated finish: {eta}."
        )
    except httpx.HTTPError as exc:
        await interaction.followup.send(f"API error: {exc}")


@bot.tree.command(name="learn", description="Mark a course module as completed")
@app_commands.describe(course="Course name", module="Module name")
async def learn_command(interaction: discord.Interaction, course: str, module: str):
    await interaction.response.defer(ephemeral=True)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{bot.api}/learning/{course}/module/{module}")
            response.raise_for_status()
            data = response.json()
        progress = data["progress"]
        await interaction.followup.send(
            f"Course **{data['course']}**, module **{data['module']}**. "
            f"Progress: {progress['completion_percent']}%."
        )
    except httpx.HTTPError as exc:
        await interaction.followup.send(f"API error: {exc}")


@bot.tree.command(name="job", description="Add a job application to the CRM pipeline")
@app_commands.describe(company="Company name", role="Job title", status="Pipeline status")
async def job_command(interaction: discord.Interaction, company: str, role: str, status: str):
    await interaction.response.defer(ephemeral=True)
    mapped_status = JOB_STATUS_MAP.get(status.lower(), status.lower())
    payload = {
        "company": company,
        "role": role,
        "status": mapped_status,
    }
    try:
        result = await api_post("/jobs", payload)
        await interaction.followup.send(
            f"Application added: **{result['company']}** — {result['role']} [{result['status']}]"
        )
    except httpx.HTTPError as exc:
        await interaction.followup.send(f"API error: {exc}")


@bot.tree.command(name="report", description="Daily snapshot")
async def report_command(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        report = await api_get("/report/daily")
        book_part = ""
        if report.get("active_book"):
            book_part = f" {report['remaining_book_pages']} pages left in **{report['active_book']}**."
        risk = " (streak at risk!)" if report.get("streak_at_risk") else ""
        apps = report["applications_sent_today"]
        app_label = "application" if apps == 1 else "applications"
        await interaction.followup.send(
            f"Today: **{apps}** {app_label} sent. "
            f"Workout streak: **{report['fitness_streak_days']}** days{risk}.{book_part}"
        )
    except httpx.HTTPError as exc:
        await interaction.followup.send(f"API error: {exc}")


@bot.event
async def on_ready():
    logger.info("Logged in as %s", bot.user)


def main():
    if not settings.discord_token:
        raise SystemExit("Set DISCORD_TOKEN in your .env file")
    bot.run(settings.discord_token)


if __name__ == "__main__":
    main()
