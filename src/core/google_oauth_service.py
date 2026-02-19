"""
Agent Optimus — Google OAuth Service (FASE 4).
Manages OAuth2 tokens and API calls for Gmail, Calendar, Drive.

Call Path:
  User clicks "Conectar Google" → /api/v1/oauth/google/connect
    → google_oauth_service.get_auth_url(user_id)
      → Google consent page
        → /api/v1/oauth/google/callback?code=...&state=user_id
          → google_oauth_service.exchange_code(code, state)
            → tokens saved to google_oauth_tokens table

  ReAct loop → gmail_read tool
    → google_oauth_service.gmail_list(user_id, query)
      → get_credentials(user_id) → refresh if expired
        → Gmail API call → formatted results
"""

import base64
import logging
import re
from datetime import datetime, timezone
from email.mime.text import MIMEText

from src.core.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",       # FASE 4A: enviar e-mails
    "https://www.googleapis.com/auth/gmail.modify",     # FASE 4B: marcar lido, arquivar, labels, lixo
    "https://www.googleapis.com/auth/calendar",         # FASE 4B: criar/editar/deletar eventos (inclui readonly)
    "https://www.googleapis.com/auth/drive",            # FASE 4B: criar/editar arquivos (inclui readonly)
    "https://www.googleapis.com/auth/contacts.readonly", # FASE 4B: buscar contatos
    "openid",
    "email",
    "profile",
]

_NOT_CONNECTED_MSG = (
    "⚠️ Google não conectado. Acesse /settings.html → Integrações Google → "
    "clique em 'Conectar Google' para autorizar acesso."
)


class GoogleOAuthService:
    """
    Manages Google OAuth2 tokens and API interactions.
    Tokens stored in google_oauth_tokens DB table (one per user).
    """

    def get_auth_url(self, user_id: str) -> str:
        """Generate Google OAuth consent URL with state=user_id."""
        if not settings.GOOGLE_OAUTH_CLIENT_ID:
            raise ValueError("GOOGLE_OAUTH_CLIENT_ID not configured")

        from google_auth_oauthlib.flow import Flow

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
        )
        flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=user_id,
        )
        return auth_url

    async def exchange_code(self, code: str, user_id: str) -> dict:
        """Exchange OAuth code for tokens and save to DB."""
        from google_auth_oauthlib.flow import Flow
        from sqlalchemy import text
        from src.infra.supabase_client import get_async_session

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
                    "redirect_uris": [settings.GOOGLE_OAUTH_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=SCOPES,
            state=user_id,
        )
        flow.redirect_uri = settings.GOOGLE_OAUTH_REDIRECT_URI

        # Allow Google to return equivalent scopes (e.g. "email" → "userinfo.email")
        import os
        os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

        flow.fetch_token(code=code)

        creds = flow.credentials
        expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None

        # Get user's Google email
        google_email = ""
        try:
            from googleapiclient.discovery import build
            oauth2_service = build("oauth2", "v2", credentials=creds)
            user_info = oauth2_service.userinfo().get().execute()
            google_email = user_info.get("email", "")
        except Exception as e:
            logger.warning(f"Could not fetch Google user info: {e}")

        async with get_async_session() as session:
            await session.execute(
                text("""
                    INSERT INTO google_oauth_tokens
                        (user_id, access_token, refresh_token, token_expiry, scopes, google_email)
                    VALUES (:uid, :at, :rt, :exp, :scopes, :email)
                    ON CONFLICT (user_id) DO UPDATE SET
                        access_token = EXCLUDED.access_token,
                        refresh_token = COALESCE(EXCLUDED.refresh_token, google_oauth_tokens.refresh_token),
                        token_expiry = EXCLUDED.token_expiry,
                        scopes = EXCLUDED.scopes,
                        google_email = EXCLUDED.google_email,
                        updated_at = now()
                """),
                {
                    "uid": user_id,
                    "at": creds.token,
                    "rt": creds.refresh_token,
                    "exp": expiry,
                    "scopes": " ".join(creds.scopes or SCOPES),
                    "email": google_email,
                },
            )
            await session.commit()

        logger.info(f"Google OAuth tokens saved for user {user_id} ({google_email})")
        return {"google_email": google_email, "scopes": creds.scopes}

    async def get_credentials(self, user_id: str):
        """Load credentials from DB, refresh if expired. Returns None if not connected."""
        from sqlalchemy import text
        from src.infra.supabase_client import get_async_session
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        async with get_async_session() as session:
            result = await session.execute(
                text("""
                    SELECT access_token, refresh_token, token_expiry, scopes
                    FROM google_oauth_tokens
                    WHERE user_id = :uid
                """),
                {"uid": user_id},
            )
            row = result.fetchone()

        if not row:
            return None

        access_token, refresh_token, token_expiry, scopes_str = row
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=(scopes_str or "").split(),
        )

        # Set expiry
        if token_expiry:
            creds.expiry = token_expiry.replace(tzinfo=None)  # google-auth expects naive UTC

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save refreshed token
                async with get_async_session() as session:
                    await session.execute(
                        text("""
                            UPDATE google_oauth_tokens
                            SET access_token = :at, token_expiry = :exp, updated_at = now()
                            WHERE user_id = :uid
                        """),
                        {
                            "uid": user_id,
                            "at": creds.token,
                            "exp": creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None,
                        },
                    )
                    await session.commit()
                logger.info(f"Google tokens refreshed for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to refresh Google token for user {user_id}: {e}")
                return None

        return creds

    async def get_connection_status(self, user_id: str) -> dict:
        """Returns {connected, google_email, scopes}."""
        from sqlalchemy import text
        from src.infra.supabase_client import get_async_session

        try:
            async with get_async_session() as session:
                result = await session.execute(
                    text("SELECT google_email, scopes FROM google_oauth_tokens WHERE user_id = :uid"),
                    {"uid": user_id},
                )
                row = result.fetchone()

            if not row:
                return {"connected": False, "google_email": "", "scopes": []}

            return {
                "connected": True,
                "google_email": row[0] or "",
                "scopes": (row[1] or "").split(),
            }
        except Exception as e:
            logger.warning(f"Could not check Google connection status: {e}")
            return {"connected": False, "google_email": "", "scopes": []}

    async def revoke(self, user_id: str) -> bool:
        """Revoke Google tokens and delete from DB."""
        import httpx
        from sqlalchemy import text
        from src.infra.supabase_client import get_async_session

        creds = await self.get_credentials(user_id)
        if creds and creds.token:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": creds.token},
                    )
            except Exception as e:
                logger.warning(f"Could not revoke Google token remotely: {e}")

        async with get_async_session() as session:
            await session.execute(
                text("DELETE FROM google_oauth_tokens WHERE user_id = :uid"),
                {"uid": user_id},
            )
            await session.commit()

        logger.info(f"Google OAuth revoked for user {user_id}")
        return True

    # ============================================
    # Gmail
    # ============================================

    def _preprocess_gmail_query(self, query: str) -> str:
        """
        Preprocess Gmail query to handle time-based filters not natively supported.
        Converts 'after:YYYY/MM/DD HH:MM' to Unix timestamp form 'after:UNIX'.
        """
        if not query:
            return "in:inbox"
        # Handle 'after:YYYY/MM/DD HH:MM' or 'after:YYYY-MM-DD HH:MM'
        m = re.search(r'after:(\d{4}[/-]\d{2}[/-]\d{2})\s+(\d{2}):(\d{2})', query)
        if m:
            date_str = m.group(1).replace('-', '/')
            hour, minute = int(m.group(2)), int(m.group(3))
            try:
                from datetime import datetime, timezone, timedelta
                # Assume BRT (UTC-3)
                dt = datetime.strptime(date_str, "%Y/%m/%d").replace(
                    hour=hour, minute=minute, tzinfo=timezone(timedelta(hours=-3))
                )
                unix_ts = int(dt.timestamp())
                query = query[:m.start()] + f"after:{unix_ts}" + query[m.end():]
            except Exception:
                pass
        return query

    async def gmail_list(self, user_id: str, query: str = "", max_results: int = 10) -> str:
        """List emails matching Gmail query string."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG

        try:
            from googleapiclient.discovery import build
            service = build("gmail", "v1", credentials=creds)

            processed_query = self._preprocess_gmail_query(query)
            results = service.users().messages().list(
                userId="me",
                q=processed_query,
                maxResults=max_results,
            ).execute()

            messages = results.get("messages", [])
            if not messages:
                return "📭 Nenhum email encontrado para a busca."

            lines = [f"📧 **{len(messages)} emails encontrados:**\n"]
            for msg in messages[:max_results]:
                detail = service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                ).execute()

                headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
                subject = headers.get("Subject", "(sem assunto)")
                sender = headers.get("From", "Desconhecido")
                date = headers.get("Date", "")
                snippet = detail.get("snippet", "")[:100]

                lines.append(f"- **{subject}**\n  De: {sender} | {date}\n  {snippet}...")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Gmail list error for user {user_id}: {e}")
            return f"❌ Erro ao acessar Gmail: {e}"

    async def gmail_get(self, user_id: str, message_id: str) -> str:
        """Get full content of a Gmail message."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG

        try:
            from googleapiclient.discovery import build
            service = build("gmail", "v1", credentials=creds)

            msg = service.users().messages().get(
                userId="me", id=message_id, format="full"
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            subject = headers.get("Subject", "(sem assunto)")
            sender = headers.get("From", "")
            date = headers.get("Date", "")

            # Extract body text
            body = _extract_email_body(msg.get("payload", {}))

            return (
                f"**Email:** {subject}\n"
                f"**De:** {sender}\n"
                f"**Data:** {date}\n\n"
                f"---\n{body[:3000]}"
            )

        except Exception as e:
            logger.error(f"Gmail get error for user {user_id}: {e}")
            return f"❌ Erro ao ler email: {e}"

    async def gmail_send(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
    ) -> str:
        """
        Send an email via Gmail API.

        IMPORTANT: Agent must always show draft and get explicit user approval
        before calling this method.

        Requires scope: gmail.send (user must reconnect Google after scope change).
        """
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG

        try:
            from googleapiclient.discovery import build

            service = build("gmail", "v1", credentials=creds)

            # Build MIME message
            mime_msg = MIMEText(body, "plain", "utf-8")
            mime_msg["to"] = to
            mime_msg["subject"] = subject
            if cc:
                mime_msg["cc"] = cc

            # Encode to base64url
            raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")

            result = service.users().messages().send(
                userId="me",
                body={"raw": raw},
            ).execute()

            msg_id = result.get("id", "")
            logger.info(f"Email sent for user {user_id} → {to} (id={msg_id})")
            return f"✅ E-mail enviado com sucesso para **{to}**!\n📧 Assunto: {subject}"

        except Exception as e:
            logger.error(f"Gmail send error for user {user_id}: {e}")
            return f"❌ Erro ao enviar e-mail: {e}"

    async def gmail_mark_read(self, user_id: str, message_id: str) -> str:
        """Mark a Gmail message as read (removes UNREAD label)."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG
        try:
            from googleapiclient.discovery import build
            service = build("gmail", "v1", credentials=creds)
            service.users().messages().modify(
                userId="me", id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            return f"✅ Email `{message_id}` marcado como lido."
        except Exception as e:
            logger.error(f"Gmail mark_read error for user {user_id}: {e}")
            return f"❌ Erro ao marcar email como lido: {e}"

    async def gmail_archive(self, user_id: str, message_id: str) -> str:
        """Archive a Gmail message (removes from INBOX)."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG
        try:
            from googleapiclient.discovery import build
            service = build("gmail", "v1", credentials=creds)
            service.users().messages().modify(
                userId="me", id=message_id,
                body={"removeLabelIds": ["INBOX"]},
            ).execute()
            return f"✅ Email `{message_id}` arquivado com sucesso."
        except Exception as e:
            logger.error(f"Gmail archive error for user {user_id}: {e}")
            return f"❌ Erro ao arquivar email: {e}"

    async def gmail_trash(self, user_id: str, message_id: str) -> str:
        """Move a Gmail message to trash."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG
        try:
            from googleapiclient.discovery import build
            service = build("gmail", "v1", credentials=creds)
            service.users().messages().trash(userId="me", id=message_id).execute()
            return f"✅ Email `{message_id}` movido para a lixeira."
        except Exception as e:
            logger.error(f"Gmail trash error for user {user_id}: {e}")
            return f"❌ Erro ao mover email para lixeira: {e}"

    async def gmail_add_label(self, user_id: str, message_id: str, label_name: str) -> str:
        """Add a label to a Gmail message (creates label if not exists)."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG
        try:
            from googleapiclient.discovery import build
            service = build("gmail", "v1", credentials=creds)

            # Find existing label by name (case-insensitive)
            labels_resp = service.users().labels().list(userId="me").execute()
            label_id = None
            for lbl in labels_resp.get("labels", []):
                if lbl["name"].lower() == label_name.lower():
                    label_id = lbl["id"]
                    break

            # Create label if not found
            if not label_id:
                new_lbl = service.users().labels().create(
                    userId="me", body={"name": label_name}
                ).execute()
                label_id = new_lbl["id"]

            service.users().messages().modify(
                userId="me", id=message_id,
                body={"addLabelIds": [label_id]},
            ).execute()
            return f"✅ Label **{label_name}** adicionada ao email `{message_id}`."
        except Exception as e:
            logger.error(f"Gmail add_label error for user {user_id}: {e}")
            return f"❌ Erro ao adicionar label: {e}"

    # ============================================
    # Google Calendar
    # ============================================

    async def calendar_list(self, user_id: str, days_ahead: int = 7) -> str:
        """List upcoming calendar events."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG

        try:
            from googleapiclient.discovery import build
            from datetime import timedelta

            service = build("calendar", "v3", credentials=creds)

            now = datetime.now(timezone.utc)
            time_max = now + timedelta(days=days_ahead)

            events_result = service.events().list(
                calendarId="primary",
                timeMin=now.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=20,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = events_result.get("items", [])
            if not events:
                return f"📅 Nenhum evento nos próximos {days_ahead} dias."

            lines = [f"📅 **{len(events)} evento(s) nos próximos {days_ahead} dias:**\n"]
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date", ""))
                summary = event.get("summary", "(sem título)")
                location = event.get("location", "")
                loc_str = f" | 📍 {location}" if location else ""
                lines.append(f"- **{summary}**\n  🕐 {start}{loc_str}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Calendar list error for user {user_id}: {e}")
            return f"❌ Erro ao acessar Calendar: {e}"

    async def calendar_search(self, user_id: str, query: str) -> str:
        """Search calendar events by text."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG

        try:
            from googleapiclient.discovery import build

            service = build("calendar", "v3", credentials=creds)
            events_result = service.events().list(
                calendarId="primary",
                q=query,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            events = events_result.get("items", [])
            if not events:
                return f"📅 Nenhum evento encontrado para '{query}'."

            lines = [f"📅 **{len(events)} evento(s) encontrado(s) para '{query}':**\n"]
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date", ""))
                summary = event.get("summary", "(sem título)")
                lines.append(f"- **{summary}** | 🕐 {start}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Calendar search error for user {user_id}: {e}")
            return f"❌ Erro ao pesquisar Calendar: {e}"

    async def calendar_create_event(
        self,
        user_id: str,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        attendees: str = "",
        timezone: str = "America/Sao_Paulo",
    ) -> str:
        """
        Create a Google Calendar event.

        Args:
            start_time: ISO 8601 datetime, e.g. '2026-02-20T14:00:00'
            end_time: ISO 8601 datetime, e.g. '2026-02-20T15:00:00'
            attendees: Comma-separated email addresses
            timezone: IANA timezone (default: America/Sao_Paulo)

        IMPORTANT: Agent must show event details and get user approval before calling.
        """
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG
        try:
            from googleapiclient.discovery import build
            service = build("calendar", "v3", credentials=creds)

            event_body: dict = {
                "summary": title,
                "description": description,
                "location": location,
                "start": {"dateTime": start_time, "timeZone": timezone},
                "end": {"dateTime": end_time, "timeZone": timezone},
            }

            if attendees:
                event_body["attendees"] = [
                    {"email": e.strip()} for e in attendees.split(",") if e.strip()
                ]

            result = service.events().insert(
                calendarId="primary", body=event_body
            ).execute()

            event_id = result.get("id", "")
            link = result.get("htmlLink", "")
            logger.info(f"Calendar event created for user {user_id}: {title} ({event_id})")
            return (
                f"✅ Evento criado com sucesso!\n"
                f"📅 **{title}**\n"
                f"🕐 Início: {start_time}\n"
                f"🕑 Fim: {end_time}\n"
                f"🆔 ID: `{event_id}`\n"
                f"🔗 {link}"
            )
        except Exception as e:
            logger.error(f"Calendar create_event error for user {user_id}: {e}")
            return f"❌ Erro ao criar evento: {e}"

    async def calendar_update_event(
        self,
        user_id: str,
        event_id: str,
        title: str = "",
        start_time: str = "",
        end_time: str = "",
        description: str = "",
        location: str = "",
        timezone: str = "America/Sao_Paulo",
    ) -> str:
        """
        Update an existing Google Calendar event (partial update — only provided fields changed).

        IMPORTANT: Agent must show changes and get user approval before calling.
        """
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG
        try:
            from googleapiclient.discovery import build
            service = build("calendar", "v3", credentials=creds)

            # Fetch existing event to do a full update (PATCH requires same structure)
            event = service.events().get(calendarId="primary", eventId=event_id).execute()

            if title:
                event["summary"] = title
            if description:
                event["description"] = description
            if location:
                event["location"] = location
            if start_time:
                event["start"] = {"dateTime": start_time, "timeZone": timezone}
            if end_time:
                event["end"] = {"dateTime": end_time, "timeZone": timezone}

            result = service.events().update(
                calendarId="primary", eventId=event_id, body=event
            ).execute()

            logger.info(f"Calendar event updated for user {user_id}: {event_id}")
            return (
                f"✅ Evento atualizado!\n"
                f"📅 **{result.get('summary', event_id)}**\n"
                f"🆔 ID: `{event_id}`\n"
                f"🔗 {result.get('htmlLink', '')}"
            )
        except Exception as e:
            logger.error(f"Calendar update_event error for user {user_id}: {e}")
            return f"❌ Erro ao atualizar evento: {e}"

    async def calendar_delete_event(self, user_id: str, event_id: str) -> str:
        """
        Delete a Google Calendar event by ID.

        IMPORTANT: Agent must confirm with user before calling — action is irreversible.
        """
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG
        try:
            from googleapiclient.discovery import build
            service = build("calendar", "v3", credentials=creds)
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            logger.info(f"Calendar event deleted for user {user_id}: {event_id}")
            return f"✅ Evento `{event_id}` deletado com sucesso do Google Calendar."
        except Exception as e:
            logger.error(f"Calendar delete_event error for user {user_id}: {e}")
            return f"❌ Erro ao deletar evento: {e}"

    # ============================================
    # Google Drive
    # ============================================

    async def drive_search(self, user_id: str, query: str, max_results: int = 10) -> str:
        """Search files in Google Drive."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG

        try:
            from googleapiclient.discovery import build

            service = build("drive", "v3", credentials=creds)
            results = service.files().list(
                q=f"name contains '{query}' or fullText contains '{query}'",
                pageSize=max_results,
                fields="files(id, name, mimeType, modifiedTime, webViewLink)",
            ).execute()

            files = results.get("files", [])
            if not files:
                return f"📁 Nenhum arquivo encontrado para '{query}'."

            lines = [f"📁 **{len(files)} arquivo(s) encontrado(s):**\n"]
            for f in files:
                name = f.get("name", "")
                mime = f.get("mimeType", "").split(".")[-1]
                modified = f.get("modifiedTime", "")[:10]
                link = f.get("webViewLink", "")
                lines.append(f"- **{name}** ({mime}) | Modificado: {modified}\n  🔗 {link}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Drive search error for user {user_id}: {e}")
            return f"❌ Erro ao pesquisar Drive: {e}"

    async def drive_read(self, user_id: str, file_id: str) -> str:
        """Read content of a Google Drive file (exports Docs as plain text)."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG

        try:
            from googleapiclient.discovery import build
            import io

            service = build("drive", "v3", credentials=creds)

            # Get file metadata
            file_meta = service.files().get(fileId=file_id, fields="name,mimeType").execute()
            mime_type = file_meta.get("mimeType", "")
            name = file_meta.get("name", "")

            # Export Google Docs/Sheets/Slides as plain text
            if "google-apps" in mime_type:
                export_mime = "text/plain"
                if "spreadsheet" in mime_type:
                    export_mime = "text/csv"
                content = service.files().export(fileId=file_id, mimeType=export_mime).execute()
                text = content.decode("utf-8") if isinstance(content, bytes) else str(content)
            else:
                # Download binary file
                request = service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                from googleapiclient.http import MediaIoBaseDownload
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                text = fh.getvalue().decode("utf-8", errors="replace")

            return f"**{name}**\n\n{text[:4000]}"

        except Exception as e:
            logger.error(f"Drive read error for user {user_id}: {e}")
            return f"❌ Erro ao ler arquivo do Drive: {e}"


    async def drive_upload_text(
        self,
        user_id: str,
        filename: str,
        content: str,
        folder_id: str = "",
    ) -> str:
        """
        Upload a text file to Google Drive (creates as plain text or Google Doc).

        IMPORTANT: Agent must show file name + content preview and get user approval before calling.
        """
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG
        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaInMemoryUpload

            service = build("drive", "v3", credentials=creds)

            media = MediaInMemoryUpload(content.encode("utf-8"), mimetype="text/plain")
            file_meta: dict = {"name": filename}
            if folder_id:
                file_meta["parents"] = [folder_id]

            result = service.files().create(
                body=file_meta, media_body=media, fields="id,name,webViewLink"
            ).execute()

            logger.info(f"Drive file uploaded for user {user_id}: {filename} (id={result.get('id')})")
            return (
                f"✅ Arquivo enviado para o Google Drive!\n"
                f"📄 **{filename}**\n"
                f"🆔 ID: `{result.get('id', '')}`\n"
                f"🔗 {result.get('webViewLink', '')}"
            )
        except Exception as e:
            logger.error(f"Drive upload_text error for user {user_id}: {e}")
            return f"❌ Erro ao enviar arquivo para Drive: {e}"

    async def drive_create_folder(
        self,
        user_id: str,
        folder_name: str,
        parent_id: str = "",
    ) -> str:
        """Create a folder in Google Drive."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG
        try:
            from googleapiclient.discovery import build

            service = build("drive", "v3", credentials=creds)
            file_meta: dict = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            }
            if parent_id:
                file_meta["parents"] = [parent_id]

            result = service.files().create(
                body=file_meta, fields="id,name,webViewLink"
            ).execute()

            logger.info(f"Drive folder created for user {user_id}: {folder_name}")
            return (
                f"✅ Pasta criada no Google Drive!\n"
                f"📁 **{folder_name}**\n"
                f"🆔 ID: `{result.get('id', '')}`\n"
                f"🔗 {result.get('webViewLink', '')}"
            )
        except Exception as e:
            logger.error(f"Drive create_folder error for user {user_id}: {e}")
            return f"❌ Erro ao criar pasta no Drive: {e}"

    # ============================================
    # Google Contacts (People API)
    # ============================================

    async def contacts_search(self, user_id: str, query: str, max_results: int = 10) -> str:
        """Search Google Contacts by name, email or phone."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG
        try:
            from googleapiclient.discovery import build

            service = build("people", "v1", credentials=creds)
            results = service.people().searchContacts(
                query=query,
                readMask="names,emailAddresses,phoneNumbers,organizations",
                pageSize=max_results,
            ).execute()

            contacts = results.get("results", [])
            if not contacts:
                return f"👤 Nenhum contato encontrado para '{query}'."

            lines = [f"👤 **{len(contacts)} contato(s) encontrado(s) para '{query}':**\n"]
            for item in contacts:
                person = item.get("person", {})
                names = person.get("names", [{}])
                name = names[0].get("displayName", "Sem nome") if names else "Sem nome"

                emails = person.get("emailAddresses", [])
                email_str = ", ".join(e.get("value", "") for e in emails) if emails else ""

                phones = person.get("phoneNumbers", [])
                phone_str = ", ".join(p.get("value", "") for p in phones) if phones else ""

                orgs = person.get("organizations", [])
                org_str = orgs[0].get("name", "") if orgs else ""

                line = f"- **{name}**"
                if email_str:
                    line += f"\n  📧 {email_str}"
                if phone_str:
                    line += f"\n  📞 {phone_str}"
                if org_str:
                    line += f"\n  🏢 {org_str}"
                lines.append(line)

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Contacts search error for user {user_id}: {e}")
            return f"❌ Erro ao buscar contatos: {e}"

    async def contacts_list(self, user_id: str, max_results: int = 20) -> str:
        """List Google Contacts (sorted by name)."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG
        try:
            from googleapiclient.discovery import build

            service = build("people", "v1", credentials=creds)
            results = service.people().connections().list(
                resourceName="people/me",
                pageSize=max_results,
                personFields="names,emailAddresses,phoneNumbers",
                sortOrder="FIRST_NAME_ASCENDING",
            ).execute()

            connections = results.get("connections", [])
            if not connections:
                return "👤 Nenhum contato encontrado na sua agenda Google."

            lines = [f"👤 **{len(connections)} contato(s):**\n"]
            for person in connections:
                names = person.get("names", [{}])
                name = names[0].get("displayName", "Sem nome") if names else "Sem nome"

                emails = person.get("emailAddresses", [])
                email_str = emails[0].get("value", "") if emails else ""

                phones = person.get("phoneNumbers", [])
                phone_str = phones[0].get("value", "") if phones else ""

                line = f"- **{name}**"
                if email_str:
                    line += f" | {email_str}"
                if phone_str:
                    line += f" | {phone_str}"
                lines.append(line)

            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Contacts list error for user {user_id}: {e}")
            return f"❌ Erro ao listar contatos: {e}"


def _extract_email_body(payload: dict) -> str:
    """Recursively extract plain text body from Gmail message payload."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if mime_type == "text/plain" and body_data:
        return base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _extract_email_body(part)
        if result:
            return result

    return ""


# Singleton
google_oauth_service = GoogleOAuthService()
