"""
Agent Optimus — Apple iCloud Service (FASE 8).

Provides access to Apple iCloud via open protocols:
  - Calendar (CalDAV)   → caldav.icloud.com
  - Reminders (CalDAV)  → caldav.icloud.com (VTODO components)
  - Contacts (CardDAV)  → contacts.icloud.com

iCloud Mail is handled separately by ImapService (FASE 4C).
Use the 'icloud' preset in PROVIDER_PRESETS to configure imap.mail.me.com.

Authentication:
  - Apple ID (email)
  - App-Specific Password (NOT the regular Apple ID password)
  - Generate at: https://appleid.apple.com → Security → App-Specific Passwords
  - Format: xxxx-xxxx-xxxx-xxxx (16 chars, auto-hyphenated by Apple)

Call Path:
  calendar_list(user_id, days_ahead)
    → _get_credentials(user_id) → SELECT FROM apple_credentials
    → caldav.DAVClient(ICLOUD_CALDAV_URL, apple_id, app_password)
    → client.principal() → calendars() → date_search(start, end)
    → [VEVENT] → formatted string list

  reminders_list(user_id)
    → _get_credentials(user_id)
    → same CalDAV client → calendars with VTODO support → todos()
    → [VTODO] → formatted string list

  contacts_search(user_id, query)
    → _get_credentials(user_id)
    → httpx.BasicAuth(apple_id, app_password) → PROPFIND + REPORT
    → vCard data → filter by query → formatted list
"""

import base64
import hashlib
import logging
from datetime import datetime, timedelta, timezone

from src.core.config import settings

logger = logging.getLogger(__name__)

ICLOUD_CALDAV_URL = "https://caldav.icloud.com"
ICLOUD_CARDDAV_URL = "https://contacts.icloud.com"

_NOT_CONFIGURED = (
    "⚠️ iCloud não configurado. "
    "Acesse /settings.html → Apple iCloud, informe seu Apple ID e "
    "gere um App-Specific Password em appleid.apple.com → Segurança → Senhas específicas para apps."
)


class AppleService:
    """
    Apple iCloud integration via CalDAV (Calendar + Reminders) and CardDAV (Contacts).
    Credentials stored per-user in DB, encrypted with Fernet.
    """

    # ──────────────────────────────────────────
    # Encryption (same pattern as ImapService)
    # ──────────────────────────────────────────

    def _get_fernet(self):
        from cryptography.fernet import Fernet
        key_bytes = hashlib.sha256(settings.JWT_SECRET.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key_bytes))

    def _encrypt(self, plaintext: str) -> str:
        return self._get_fernet().encrypt(plaintext.encode()).decode()

    def _decrypt(self, encrypted: str) -> str:
        return self._get_fernet().decrypt(encrypted.encode()).decode()

    # ──────────────────────────────────────────
    # Credential Management
    # ──────────────────────────────────────────

    async def save_credentials(
        self,
        user_id: str,
        apple_id: str,
        app_password: str,
        display_name: str = "",
    ) -> dict:
        """Save Apple ID + App-Specific Password for a user (upsert)."""
        encrypted_pwd = self._encrypt(app_password)
        try:
            from sqlalchemy import text
            from src.infra.supabase_client import get_async_session

            async with get_async_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO apple_credentials
                            (user_id, apple_id, app_password_encrypted, display_name, updated_at)
                        VALUES (:uid, :apple_id, :pwd, :display_name, NOW())
                        ON CONFLICT (user_id) DO UPDATE SET
                            apple_id = EXCLUDED.apple_id,
                            app_password_encrypted = EXCLUDED.app_password_encrypted,
                            display_name = EXCLUDED.display_name,
                            updated_at = NOW()
                    """),
                    {
                        "uid": user_id,
                        "apple_id": apple_id,
                        "pwd": encrypted_pwd,
                        "display_name": display_name,
                    },
                )
                await session.commit()
            return {"ok": True, "apple_id": apple_id}
        except Exception as e:
            logger.error(f"apple save_credentials error: {e}")
            return {"ok": False, "error": str(e)}

    async def get_credentials(self, user_id: str) -> tuple[str, str] | None:
        """Return (apple_id, app_password) or None if not configured."""
        try:
            from sqlalchemy import text
            from src.infra.supabase_client import get_async_session

            async with get_async_session() as session:
                row = await session.execute(
                    text("SELECT apple_id, app_password_encrypted FROM apple_credentials WHERE user_id = :uid"),
                    {"uid": user_id},
                )
                rec = row.fetchone()
                if not rec:
                    return None
                return rec[0], self._decrypt(rec[1])
        except Exception as e:
            logger.warning(f"apple get_credentials error: {e}")
            return None

    async def remove_credentials(self, user_id: str) -> dict:
        """Delete Apple credentials for a user."""
        try:
            from sqlalchemy import text
            from src.infra.supabase_client import get_async_session

            async with get_async_session() as session:
                await session.execute(
                    text("DELETE FROM apple_credentials WHERE user_id = :uid"),
                    {"uid": user_id},
                )
                await session.commit()
            return {"ok": True}
        except Exception as e:
            logger.error(f"apple remove_credentials error: {e}")
            return {"ok": False, "error": str(e)}

    async def test_connection(self, user_id: str) -> dict:
        """
        Test CalDAV connection with stored credentials.
        Returns {ok, apple_id, calendars_count, error?}
        """
        creds = await self.get_credentials(user_id)
        if not creds:
            return {"ok": False, "error": "Credenciais não configuradas"}

        apple_id, app_password = creds
        try:
            import caldav
            client = caldav.DAVClient(
                url=ICLOUD_CALDAV_URL,
                username=apple_id,
                password=app_password,
            )
            principal = client.principal()
            calendars = principal.calendars()
            return {
                "ok": True,
                "apple_id": apple_id,
                "calendars_count": len(calendars),
            }
        except Exception as e:
            logger.warning(f"apple test_connection failed for user {user_id}: {e}")
            return {
                "ok": False,
                "apple_id": apple_id,
                "error": str(e),
            }

    # ──────────────────────────────────────────
    # Internal CalDAV client
    # ──────────────────────────────────────────

    async def _caldav_client(self, user_id: str):
        """Return authenticated caldav.DAVClient or None."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return None
        apple_id, app_password = creds
        try:
            import caldav
            return caldav.DAVClient(
                url=ICLOUD_CALDAV_URL,
                username=apple_id,
                password=app_password,
            )
        except Exception as e:
            logger.error(f"apple _caldav_client error: {e}")
            return None

    # ──────────────────────────────────────────
    # Calendar (VEVENT)
    # ──────────────────────────────────────────

    async def calendar_list(self, user_id: str, days_ahead: int = 7) -> str:
        """
        List upcoming events from all iCloud calendars.
        Returns formatted text: "📅 Título | Data | Local | Calendário"
        """
        client = await self._caldav_client(user_id)
        if not client:
            return _NOT_CONFIGURED

        try:
            principal = client.principal()
            calendars = principal.calendars()
            now = datetime.now(timezone.utc)
            end = now + timedelta(days=days_ahead)

            events = []
            for cal in calendars:
                try:
                    cal_name = getattr(cal, "name", None) or "Calendário"
                    results = cal.date_search(start=now, end=end, expand=True)
                    for evt in results:
                        try:
                            vobj = evt.vobject_instance
                            vevent = vobj.vevent
                            title = str(getattr(vevent, "summary", None) or "(sem título)")
                            dtstart = getattr(vevent, "dtstart", None)
                            location = str(getattr(vevent, "location", None) or "")
                            dt_str = ""
                            if dtstart:
                                dt = dtstart.value
                                if hasattr(dt, "strftime"):
                                    dt_str = dt.strftime("%d/%m/%Y %H:%M")
                            events.append(
                                f"📅 **{title}**"
                                + (f" | {dt_str}" if dt_str else "")
                                + (f" | 📍 {location}" if location else "")
                                + f" | [{cal_name}]"
                            )
                        except Exception:
                            continue
                except Exception:
                    continue

            if not events:
                return f"Nenhum evento nos próximos {days_ahead} dias no iCloud Calendar."
            return f"**iCloud Calendar — próximos {days_ahead} dias ({len(events)} eventos):**\n\n" + "\n".join(events)

        except Exception as e:
            logger.error(f"apple calendar_list error: {e}")
            return f"❌ Erro ao acessar iCloud Calendar: {e}"

    async def calendar_search(self, user_id: str, query: str) -> str:
        """Search events by text in summary/description."""
        client = await self._caldav_client(user_id)
        if not client:
            return _NOT_CONFIGURED

        try:
            principal = client.principal()
            calendars = principal.calendars()
            q = query.lower()
            found = []

            for cal in calendars:
                try:
                    cal_name = getattr(cal, "name", None) or "Calendário"
                    for evt in cal.events():
                        try:
                            vobj = evt.vobject_instance
                            vevent = vobj.vevent
                            title = str(getattr(vevent, "summary", None) or "")
                            desc = str(getattr(vevent, "description", None) or "")
                            if q in title.lower() or q in desc.lower():
                                dtstart = getattr(vevent, "dtstart", None)
                                dt_str = ""
                                if dtstart and hasattr(dtstart.value, "strftime"):
                                    dt_str = dtstart.value.strftime("%d/%m/%Y %H:%M")
                                found.append(
                                    f"📅 **{title}**"
                                    + (f" | {dt_str}" if dt_str else "")
                                    + f" | [{cal_name}]"
                                )
                        except Exception:
                            continue
                except Exception:
                    continue

            if not found:
                return f"Nenhum evento encontrado com '{query}' no iCloud Calendar."
            return f"**iCloud Calendar — busca '{query}' ({len(found)} resultado(s)):**\n\n" + "\n".join(found[:20])

        except Exception as e:
            logger.error(f"apple calendar_search error: {e}")
            return f"❌ Erro ao buscar no iCloud Calendar: {e}"

    async def calendar_create_event(
        self,
        user_id: str,
        title: str,
        start: str,
        end: str,
        notes: str = "",
        calendar_name: str = "",
    ) -> str:
        """
        Create a new event in iCloud Calendar.
        start/end: ISO 8601 strings (e.g. "2026-02-20T14:00:00")
        calendar_name: empty = first/default calendar
        """
        client = await self._caldav_client(user_id)
        if not client:
            return _NOT_CONFIGURED

        try:
            from datetime import datetime as dt
            import uuid

            principal = client.principal()
            calendars = principal.calendars()
            if not calendars:
                return "❌ Nenhum calendário encontrado na sua conta iCloud."

            # Find calendar by name, fallback to first
            target_cal = calendars[0]
            if calendar_name:
                for cal in calendars:
                    name = getattr(cal, "name", "") or ""
                    if calendar_name.lower() in name.lower():
                        target_cal = cal
                        break

            start_dt = dt.fromisoformat(start)
            end_dt = dt.fromisoformat(end)
            uid = str(uuid.uuid4())

            ical_data = (
                "BEGIN:VCALENDAR\r\n"
                "VERSION:2.0\r\n"
                "PRODID:-//AgentOptimus//FASE8//PT\r\n"
                "BEGIN:VEVENT\r\n"
                f"UID:{uid}\r\n"
                f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}\r\n"
                f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}\r\n"
                f"SUMMARY:{title}\r\n"
                + (f"DESCRIPTION:{notes}\r\n" if notes else "")
                + "END:VEVENT\r\n"
                "END:VCALENDAR\r\n"
            )

            target_cal.save_event(ical_data)
            cal_name = getattr(target_cal, "name", None) or "Calendário"
            return (
                f"✅ Evento criado no iCloud Calendar!\n"
                f"**{title}**\n"
                f"📅 {start_dt.strftime('%d/%m/%Y %H:%M')} → {end_dt.strftime('%H:%M')}\n"
                f"📆 Calendário: {cal_name}"
            )
        except Exception as e:
            logger.error(f"apple calendar_create_event error: {e}")
            return f"❌ Erro ao criar evento no iCloud: {e}"

    # ──────────────────────────────────────────
    # Reminders (VTODO)
    # ──────────────────────────────────────────

    async def reminders_list(self, user_id: str, completed: bool = False) -> str:
        """List iCloud Reminders (VTODO components)."""
        client = await self._caldav_client(user_id)
        if not client:
            return _NOT_CONFIGURED

        try:
            principal = client.principal()
            calendars = principal.calendars()
            todos = []

            for cal in calendars:
                try:
                    cal_name = getattr(cal, "name", None) or "Lembretes"
                    for todo in cal.todos(include_completed=completed):
                        try:
                            vobj = todo.vobject_instance
                            vtodo = vobj.vtodo
                            title = str(getattr(vtodo, "summary", None) or "(sem título)")
                            due = getattr(vtodo, "due", None)
                            status = str(getattr(vtodo, "status", None) or "NEEDS-ACTION")
                            is_done = status.upper() == "COMPLETED"
                            if is_done and not completed:
                                continue
                            icon = "✅" if is_done else "🔲"
                            due_str = ""
                            if due and hasattr(due.value, "strftime"):
                                due_str = f" | prazo: {due.value.strftime('%d/%m/%Y')}"
                            todos.append(f"{icon} **{title}**{due_str} [{cal_name}]")
                        except Exception:
                            continue
                except Exception:
                    continue

            if not todos:
                label = "concluídos" if completed else "pendentes"
                return f"Nenhum lembrete {label} no iCloud Reminders."
            label = "todos" if completed else "pendentes"
            return f"**iCloud Reminders — {label} ({len(todos)}):**\n\n" + "\n".join(todos[:30])

        except Exception as e:
            logger.error(f"apple reminders_list error: {e}")
            return f"❌ Erro ao acessar iCloud Reminders: {e}"

    async def reminders_create(self, user_id: str, title: str, due_date: str = "") -> str:
        """Create a new Reminder in iCloud."""
        client = await self._caldav_client(user_id)
        if not client:
            return _NOT_CONFIGURED

        try:
            import uuid
            principal = client.principal()
            calendars = principal.calendars()
            if not calendars:
                return "❌ Nenhum calendário encontrado na sua conta iCloud."

            uid = str(uuid.uuid4())
            due_line = ""
            if due_date:
                try:
                    from datetime import datetime as dt
                    due_dt = dt.fromisoformat(due_date)
                    due_line = f"DUE:{due_dt.strftime('%Y%m%dT%H%M%S')}\r\n"
                except ValueError:
                    pass

            vtodo_data = (
                "BEGIN:VCALENDAR\r\n"
                "VERSION:2.0\r\n"
                "PRODID:-//AgentOptimus//FASE8//PT\r\n"
                "BEGIN:VTODO\r\n"
                f"UID:{uid}\r\n"
                f"SUMMARY:{title}\r\n"
                "STATUS:NEEDS-ACTION\r\n"
                + due_line
                + "END:VTODO\r\n"
                "END:VCALENDAR\r\n"
            )

            # Use first calendar (Reminders list)
            calendars[0].save_todo(vtodo_data)
            return (
                f"✅ Lembrete criado no iCloud!\n"
                f"**{title}**"
                + (f"\n📅 Prazo: {due_date}" if due_date else "")
            )
        except Exception as e:
            logger.error(f"apple reminders_create error: {e}")
            return f"❌ Erro ao criar lembrete no iCloud: {e}"

    # ──────────────────────────────────────────
    # Contacts (CardDAV)
    # ──────────────────────────────────────────

    async def _fetch_contacts_raw(self, apple_id: str, app_password: str) -> list[dict]:
        """
        Fetch vCards from iCloud CardDAV.
        Returns list of dicts: {name, email, phone, org}
        """
        import httpx

        # Step 1: Discover the addressbook URL via PROPFIND
        auth = (apple_id, app_password)
        headers = {
            "Depth": "0",
            "Content-Type": "application/xml; charset=utf-8",
        }
        propfind_body = (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<D:propfind xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">'
            "<D:prop><D:current-user-principal/></D:prop>"
            "</D:propfind>"
        )

        contacts = []
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as http:
                # Discover principal
                r = await http.request(
                    "PROPFIND",
                    f"{ICLOUD_CARDDAV_URL}/",
                    content=propfind_body,
                    headers=headers,
                    auth=auth,
                )
                if r.status_code not in (207, 200):
                    logger.warning(f"CardDAV discovery failed: {r.status_code}")
                    return contacts

                # REPORT to get all vCards
                report_body = (
                    '<?xml version="1.0" encoding="utf-8"?>'
                    '<C:addressbook-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">'
                    "<D:prop>"
                    "<D:getetag/>"
                    "<C:address-data/>"
                    "</D:prop>"
                    "<C:filter/>"
                    "</C:addressbook-query>"
                )
                r2 = await http.request(
                    "REPORT",
                    f"{ICLOUD_CARDDAV_URL}/",
                    content=report_body,
                    headers={
                        "Depth": "1",
                        "Content-Type": "application/xml; charset=utf-8",
                    },
                    auth=auth,
                )

                # Parse vCard data from XML response
                import re as _re
                vcard_blocks = _re.findall(
                    r"BEGIN:VCARD.*?END:VCARD",
                    r2.text,
                    _re.DOTALL,
                )
                for block in vcard_blocks:
                    contact = _parse_vcard(block)
                    if contact:
                        contacts.append(contact)

        except Exception as e:
            logger.error(f"apple _fetch_contacts_raw error: {e}")

        return contacts

    async def contacts_search(self, user_id: str, query: str) -> str:
        """Search iCloud Contacts by name, email, or phone."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONFIGURED

        apple_id, app_password = creds
        try:
            contacts = await self._fetch_contacts_raw(apple_id, app_password)
            q = query.lower()
            found = [
                c for c in contacts
                if q in c.get("name", "").lower()
                or q in c.get("email", "").lower()
                or q in c.get("phone", "").lower()
                or q in c.get("org", "").lower()
            ]
            if not found:
                return f"Nenhum contato encontrado com '{query}' no iCloud."
            return _format_contacts(found[:20], f"iCloud Contacts — busca '{query}'")
        except Exception as e:
            logger.error(f"apple contacts_search error: {e}")
            return f"❌ Erro ao buscar contatos no iCloud: {e}"

    async def contacts_list(self, user_id: str, limit: int = 20) -> str:
        """List iCloud Contacts."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONFIGURED

        apple_id, app_password = creds
        try:
            contacts = await self._fetch_contacts_raw(apple_id, app_password)
            if not contacts:
                return "Nenhum contato encontrado no iCloud Contacts."
            return _format_contacts(contacts[:limit], f"iCloud Contacts ({len(contacts)} total)")
        except Exception as e:
            logger.error(f"apple contacts_list error: {e}")
            return f"❌ Erro ao listar contatos do iCloud: {e}"


# ──────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────

def _parse_vcard(block: str) -> dict | None:
    """Parse a VCARD text block into a dict."""
    import re
    try:
        name = ""
        email = ""
        phone = ""
        org = ""

        fn = re.search(r"^FN[;:](.+)$", block, re.MULTILINE)
        if fn:
            name = fn.group(1).strip()

        em = re.search(r"^EMAIL[;:A-Z=a-z]*:(.+)$", block, re.MULTILINE)
        if em:
            email = em.group(1).strip()

        tel = re.search(r"^TEL[;:A-Z=a-z]*:(.+)$", block, re.MULTILINE)
        if tel:
            phone = tel.group(1).strip()

        org_m = re.search(r"^ORG[;:](.+)$", block, re.MULTILINE)
        if org_m:
            org = org_m.group(1).strip().rstrip(";")

        if not name and not email:
            return None
        return {"name": name, "email": email, "phone": phone, "org": org}
    except Exception:
        return None


def _format_contacts(contacts: list[dict], header: str) -> str:
    lines = [f"**{header} ({len(contacts)}):**\n"]
    for c in contacts:
        line = f"👤 **{c['name'] or c['email']}**"
        if c["email"]:
            line += f" — {c['email']}"
        if c["phone"]:
            line += f" | 📱 {c['phone']}"
        if c["org"]:
            line += f" | 🏢 {c['org']}"
        lines.append(line)
    return "\n".join(lines)


# Singleton
apple_service = AppleService()
