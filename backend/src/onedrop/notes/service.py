"""Note use cases: search, pin, convert into a task."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from onedrop.db.models.notes import Note
from onedrop.db.models.planner import Task
from onedrop.db.repositories.notes import NoteRepository
from onedrop.db.repositories.tasks import TaskRepository
from onedrop.errors import NotFoundError
from onedrop.notes.schemas import NoteCreate, NoteUpdate

TASK_TITLE_LIMIT = 200


def derive_task_title(note: Note) -> str:
    """Use the note title, or the first line of its content."""
    if note.title:
        return note.title[:TASK_TITLE_LIMIT]
    first_line = note.content.strip().splitlines()[0] if note.content.strip() else "Note"
    return first_line[:TASK_TITLE_LIMIT]


class NoteService:
    """Application service for notes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._notes = NoteRepository(session)
        self._tasks = TaskRepository(session)

    async def create(self, user_id: UUID, payload: NoteCreate) -> Note:
        note = await self._notes.create(
            user_id=user_id, values=payload.model_dump(exclude_unset=False)
        )
        await self._session.commit()
        return note

    async def get(self, user_id: UUID, note_id: UUID) -> Note:
        note = await self._notes.get(note_id, user_id)
        if note is None:
            raise NotFoundError("Note not found")
        return note

    async def list(
        self, user_id: UUID, *, search: str | None, limit: int, offset: int
    ) -> tuple[list[Note], bool]:
        rows = await self._notes.list(
            user_id, search=search, limit=limit + 1, offset=offset
        )
        return rows[:limit], len(rows) > limit

    async def patch(self, user_id: UUID, note_id: UUID, payload: NoteUpdate) -> Note:
        note = await self.get(user_id, note_id)
        note = await self._notes.apply_changes(note, payload.model_dump(exclude_unset=True))
        await self._session.commit()
        return note

    async def set_pinned(self, user_id: UUID, note_id: UUID, pinned: bool) -> Note:
        note = await self.get(user_id, note_id)
        note = await self._notes.apply_changes(note, {"pinned": pinned})
        await self._session.commit()
        return note

    async def delete(self, user_id: UUID, note_id: UUID) -> None:
        note = await self.get(user_id, note_id)
        await self._notes.soft_delete(note)
        await self._session.commit()

    async def convert_to_task(
        self,
        user_id: UUID,
        note_id: UUID,
        *,
        due_at: datetime | None = None,
        keep_note: bool = True,
    ) -> Task:
        """Create a task from a note, optionally removing the note."""
        note = await self.get(user_id, note_id)
        task = await self._tasks.create(
            user_id=user_id,
            values={
                "title": derive_task_title(note),
                "description": note.content,
                "due_at": due_at,
                "source_inbox_item_id": note.source_inbox_item_id,
            },
        )
        if not keep_note:
            await self._notes.soft_delete(note)
        await self._session.commit()
        return task
