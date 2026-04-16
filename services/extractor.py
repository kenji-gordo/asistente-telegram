import json
import logging
import asyncio
from datetime import datetime
from typing import Optional
from groq import Groq
from models.event import Event
from config.settings import settings

logger = logging.getLogger(__name__)


# University course keywords mapping
UNIVERSITY_COURSES = {
    "AS": ["análisis de sistemas", "analisis de sistemas", "asignatura as", "curso as"],
    "MAT": ["matemática 2", "matematica 2", "matematicas 2", "mate 2", "mat2"],
    "FIS": ["física 2", "fisica 2", "fisica dos", "fi2"],
    "SSL": ["sintaxis", "semántica", "sintaxis y semántica", "ssl"],
    "SO": ["sistemas operativos", "sistema operativo", "so", "sao"],
    "PARA": ["paradigmas", "paradigmas de programación", "para"],
}

# Category keywords
CATEGORY_KEYWORDS = {
    "trabajo": ["reunión", "trabajo", "oficina", "jefe", "cliente", "proyecto", "deadline", "entrega"],
    "personal": ["personal", "cumpleaños", "médico", "doctor", "dentista", "familia"],
}

# Event type keywords for university events
EVENT_TYPE_KEYWORDS = {
    "parcial": ["parcial", "examen", "evaluación", "prueba"],
    "tp": ["tp", "trabajo práctico", "practico", "práctico", "tp integrador"],
    "entrega": ["entrega", "hand in", "submit", "entregar"],
    "final": ["final", "examen final", "recuperatorio"],
    "clase": ["clase", "teórico", "practica", "práctica", " laboratorio", "lab"],
}


def detect_category(text: str) -> tuple[str, Optional[str], Optional[str]]:
    """
    Detect category, course, and event type from text

    Returns:
        Tuple of (category, course_code, event_type)
    """
    text_lower = text.lower()

    category = "general"
    course = None
    event_type = None

    # Check for university courses first
    for course_code, keywords in UNIVERSITY_COURSES.items():
        for keyword in keywords:
            if keyword in text_lower:
                category = "universidad"
                course = course_code
                break
        if course:
            break

    # Check for other categories
    if category == "general":
        for cat, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    category = cat
                    break
            if category != "general":
                break

    # Check for event types (university specific)
    if category == "universidad":
        for etype, keywords in EVENT_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    event_type = etype
                    break
            if event_type:
                break

    return (category, course, event_type)


class EventExtractor:
    """Service for extracting event details from text using LLM"""

    SYSTEM_PROMPT = """Eres un asistente que extrae información de eventos de texto en español.

Responde SOLO con JSON válido siguiendo este formato:
{
    "title": "Título del evento",
    "description": "Descripción adicional (puede estar vacío)",
    "start_date": "YYYY-MM-DD o 'manana'",
    "start_time": "HH:MM",
    "end_time": "HH:MM (opcional, dejar vacío si no se especifica)",
    "duration_hours": 1 (por defecto 1 hora si no se especifica),
    "category": "universidad|trabajo|personal|general",
    "course": "AS|MAT|FIS|SSL|SO|PARA (solo si es universidad, sino dejar vacío)",
    "event_type": "parcial|tp|entrega|final|clase (solo si es universidad, sino dejar vacío)"
}

Reglas:
- Si no puedes determinar la fecha, usa "manana" como referencia (dia actual + 1)
- Si no hay hora, usa las 9:00 como predeterminado
- Para categoría "universidad", incluye el código del curso si lo identificas
- Para eventos universitarios, incluye el tipo: parcial (examen), tp (trabajo práctico), entrega, final, clase
- Courses: AS (Análisis de Sistemas), MAT (Matemática 2), FIS (Física 2), SSL (Sintaxis y Semántica), SO (Sistemas Operativos), PARA (Paradigmas)"""

    USER_PROMPT_TEMPLATE = """Extrae la información del siguiente mensaje:

\"{message}\"

Responde solo con JSON."""

    def __init__(self):
        self._client = None

    @property
    def client(self) -> Groq:
        """Get or create Groq client"""
        if self._client is None:
            if not settings.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY not configured")
            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    async def extract_event(self, text: str) -> Event:
        """
        Extract event details from text

        Args:
            text: Input text (can be transcription or direct message)

        Returns:
            Event object with extracted data

        Raises:
            Exception: If extraction fails
        """
        try:
            # First, detect category using keywords (fast, no API call)
            category, course, event_type = detect_category(text)

            # Then use LLM for structured extraction (run in thread to avoid blocking)
            def _call_llm():
                return self.client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": self.USER_PROMPT_TEMPLATE.format(message=text)},
                    ],
                    temperature=0.3,
                    max_tokens=500,
                )

            response = await asyncio.to_thread(_call_llm)

            content = response.choices[0].message.content.strip()

            # Try to parse JSON from response
            # Sometimes the model adds markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            data = json.loads(content)

            # Parse date and time - handle relative dates like "mañana 15:00"
            raw_date = data.get("start_date", "")
            raw_time = data.get("start_time", "09:00")

            # If date contains time embedded (e.g., "mañana 15:00"), extract both
            import re
            combined_match = re.match(r"(\w+)\s+(\d{1,2}:\d{2})", raw_date)
            if combined_match:
                raw_date = combined_match.group(1)
                raw_time = combined_match.group(2)

            # Normalize relative dates
            from datetime import timedelta
            tomorrow = datetime.now() + timedelta(days=1)

            # Map weekday names to their next occurrence
            weekdays = {
                "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
                "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6
            }

            # Map month names
            months = {
                "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
                "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
                "septiembre": 9, "setiembre": 9, "octubre": 10,
                "noviembre": 11, "diciembre": 12
            }

            raw_date_lower = raw_date.lower().strip()
            current_year = datetime.now().year

            # Try to parse "27 de mayo" or "27 de mayo de 2026"
            date_match = re.match(r"(\d{1,2})\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?", raw_date_lower)
            if date_match:
                day = int(date_match.group(1))
                month_name = date_match.group(2)
                year = int(date_match.group(3)) if date_match.group(3) else current_year
                if month_name in months:
                    date_str = f"{year}-{months[month_name]:02d}-{day:02d}"
                else:
                    date_str = tomorrow.strftime("%Y-%m-%d")
            elif raw_date and re.match(r"\d{4}-\d{2}-\d{2}", raw_date):
                # Validate year - if it's in the past, assume current year
                parts = raw_date.split("-")
                year = int(parts[0])
                if year < current_year:
                    parts[0] = str(current_year)
                    date_str = "-".join(parts)
                else:
                    date_str = raw_date
            elif raw_date_lower in weekdays:
                # Find next occurrence of this weekday
                current_weekday = datetime.now().weekday()
                target_weekday = weekdays[raw_date_lower]
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead == 0:
                    days_ahead = 7  # If today is the same weekday, go to next week
                target_date = datetime.now() + timedelta(days=days_ahead)
                date_str = target_date.strftime("%Y-%m-%d")
            elif "manana" in raw_date_lower or "mañana" in raw_date_lower:
                date_str = tomorrow.strftime("%Y-%m-%d")
            elif raw_date and re.match(r"\d{4}-\d{2}-\d{2}", raw_date):
                date_str = raw_date
            else:
                date_str = tomorrow.strftime("%Y-%m-%d")

            start_datetime = datetime.strptime(
                f"{date_str} {raw_time}",
                "%Y-%m-%d %H:%M"
            )

            # Calculate end time
            end_time_str = data.get("end_time", "")
            if end_time_str:
                end_datetime = datetime.strptime(
                    f"{date_str} {end_time_str}",
                    "%Y-%m-%d %H:%M"
                )
            else:
                duration = data.get("duration_hours", 1)
                from datetime import timedelta
                end_datetime = start_datetime + timedelta(hours=duration)

            # Use LLM-detected category if keyword detection wasn't confident
            llm_category = data.get("category", "general")
            if category == "general" and llm_category != "general":
                category = llm_category

            course = data.get("course") or course
            event_type = data.get("event_type") or event_type

            event = Event(
                title=data.get("title", "Evento sin título"),
                description=data.get("description", ""),
                start_time=start_datetime,
                end_time=end_datetime,
                category=category,
                course=course if course and category == "universidad" else None,
                event_type=event_type if event_type and category == "universidad" else None,
                reminder_minutes=30,
            )

            logger.info(f"Extracted event: {event.title} [{event.category}]")
            return event

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise Exception("No pude procesar el mensaje. Intenta de nuevo.")
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            raise Exception(f"Error al extraer el evento: {e}")


extractor = EventExtractor()