from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Event:
    """Event model for calendar events"""

    title: str
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    category: str = "general"  # "universidad", "trabajo", "personal", "general"
    course: Optional[str] = None  # AS, MAT, FIS, SSL, SO/SAO, PARA
    event_type: Optional[str] = None  # "parcial", "tp", "entrega", "final", "clase"
    reminder_minutes: Optional[int] = 30

    @property
    def titulo(self) -> str:
        """Alias for title (Spanish compatibility)"""
        return self.title

    @property
    def descripcion(self) -> Optional[str]:
        """Alias for description (Spanish compatibility)"""
        return self.description

    @property
    def fecha_inicio(self) -> Optional[datetime]:
        """Alias for start_time (Spanish compatibility)"""
        return self.start_time

    @property
    def fecha_fin(self) -> Optional[datetime]:
        """Alias for end_time (Spanish compatibility)"""
        return self.end_time

    @property
    def recordatorio_minutes(self) -> Optional[int]:
        """Alias for reminder_minutes (Spanish compatibility)"""
        return self.reminder_minutes