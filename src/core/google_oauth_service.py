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
from datetime import datetime, timezone
from email.mime.text import MIMEText

from src.core.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",       # FASE 4A: enviar e-mails
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
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

    async def gmail_list(self, user_id: str, query: str = "", max_results: int = 10) -> str:
        """List emails matching Gmail query string."""
        creds = await self.get_credentials(user_id)
        if not creds:
            return _NOT_CONNECTED_MSG

        try:
            from googleapiclient.discovery import build
            service = build("gmail", "v1", credentials=creds)

            results = service.users().messages().list(
                userId="me",
                q=query or "in:inbox",
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
