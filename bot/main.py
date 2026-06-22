import logging
from datetime import date

import discord
import httpx
from discord import app_commands
from discord.ext import commands

from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lifeos-bot")


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


async def api_post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(f"{bot.api}{path}", json=payload)
        response.raise_for_status()
        return response.json()


async def api_get(path: str) -> dict | list:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{bot.api}{path}")
        response.raise_for_status()
        return response.json()


async def api_delete(path: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.delete(f"{bot.api}{path}")
        response.raise_for_status()


@bot.tree.command(name="read", description="Log pages read today")
@app_commands.describe(pages="Number of pages", book="Book title (optional, uses active book)")
async def read_command(interaction: discord.Interaction, pages: int, book: str | None = None):
    await interaction.response.defer(ephemeral=True)
    payload: dict = {"pages": pages}
    if book:
        payload["title"] = book
    try:
        result = await api_post("/books/read", payload)
        b = result["book"]
        eta = b.get("estimated_completion_date") or "n/a"
        await interaction.followup.send(
            f"**{b['title']}**: +{pages} pages → {b['current_page']}/{b['total_pages']} "
            f"({b['completion_percent']}%). Remaining: {b['remaining_pages']}. Est. finish: {eta}."
        )
    except httpx.HTTPError as exc:
        await interaction.followup.send(f"API error: {exc}")


@bot.tree.command(name="book", description="Add a new book to your shelf")
@app_commands.describe(title="Book title", pages="Total pages", author="Author (optional)")
async def book_add_command(
    interaction: discord.Interaction, title: str, pages: int, author: str | None = None
):
    await interaction.response.defer(ephemeral=True)
    payload = {
        "title": title,
        "total_pages": pages,
        "is_active": True,
    }
    if author:
        payload["author"] = author
    try:
        result = await api_post("/books", payload)
        await interaction.followup.send(
            f"Added **{result['title']}** ({pages} pages)"
            + (f" by {author}" if author else "")
            + " — set as active."
        )
    except httpx.HTTPError as exc:
        await interaction.followup.send(f"API error: {exc}")


@bot.tree.command(name="books", description="Show your reading shelf")
async def books_command(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        overview = await api_get("/books/overview")
        books = await api_get("/books")
        lines = [
            f"**Today:** {overview['pages_today']} pages · "
            f"**This week:** {overview['pages_this_week']} pages",
            "",
        ]
        for b in books:
            marker = "📖 " if b["is_active"] else "   "
            lines.append(
                f"{marker}**{b['title']}** — {b['current_page']}/{b['total_pages']} "
                f"({b['completion_percent']}%) [{b['status']}]"
            )
        await interaction.followup.send("\n".join(lines))
    except httpx.HTTPError as exc:
        await interaction.followup.send(f"API error: {exc}")


@bot.tree.command(name="active", description="Set a book as your active reading target")
@app_commands.describe(title="Book title (partial match)")
async def active_command(interaction: discord.Interaction, title: str):
    await interaction.response.defer(ephemeral=True)
    try:
        books = await api_get("/books")
        match = next((b for b in books if title.lower() in b["title"].lower()), None)
        if not match:
            await interaction.followup.send(f'No book matching "{title}".')
            return
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{bot.api}/books/{match['id']}/activate")
            response.raise_for_status()
            result = response.json()
        await interaction.followup.send(f"Active book: **{result['title']}**")
    except httpx.HTTPError as exc:
        await interaction.followup.send(f"API error: {exc}")


@bot.tree.command(name="delete-book", description="Remove a book from your shelf")
@app_commands.describe(title="Book title (partial match)")
async def delete_book_command(interaction: discord.Interaction, title: str):
    await interaction.response.defer(ephemeral=True)
    try:
        books = await api_get("/books")
        match = next((b for b in books if title.lower() in b["title"].lower()), None)
        if not match:
            await interaction.followup.send(f'No book matching "{title}".')
            return
        await api_delete(f"/books/{match['id']}")
        await interaction.followup.send(f"Deleted **{match['title']}** from your shelf.")
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
