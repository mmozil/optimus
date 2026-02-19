"""
Agent Optimus — IMAP/SMTP Universal Email Service (FASE 4C).
Covers: Outlook, Office 365, Yahoo, Gmail (app password), corporate IMAP, Locaweb, etc.

Call Path:
  add_account()   → encrypt password → INSERT INTO imap_accounts
  read_emails()   → _get_credentials() → aioimaplib.IMAP4_SSL → SEARCH + FETCH → formatted list
  send_email()    → _get_credentials() → aiosmtplib → STARTTLS → SEND
  list_accounts() → SELECT (no passwords) → list of configured accounts
"""

import base64
import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.core.config import settings

logger = logging.getLogger(__name__)

# ============================================
# Provider presets (IMAP + SMTP config)
# ============================================
PROVIDER_PRESETS: dict[str, dict] = {
    "outlook": {
        "label": "Outlook / Hotmail / Live",
        "imap_host": "imap.outlook.com",
        "imap_port": 993,
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
    },
    "office365": {
        "label": "Office 365 / Exchange Online",
        "imap_host": "outlook.office365.com",
        "imap_port": 993,
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
    },
    "gmail": {
        "label": "Gmail (App Password)",
        "imap_host": "imap.gmail.com",
        "imap_port": 993,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
    },
    "yahoo": {
        "label": "Yahoo Mail",
        "imap_host": "imap.mail.yahoo.com",
        "imap_port": 993,
        "smtp_host": "smtp.mail.yahoo.com",
        "smtp_port": 587,
    },
    "locaweb": {
        "label": "Locaweb",
        "imap_host": "imap.locaweb.com.br",
        "imap_port": 993,
        "smtp_host": "smtp.locaweb.com.br",
        "smtp_port": 587,
    },
    "hostgator": {
        "label": "HostGator Brasil",
        "imap_host": "mail.hostgator.com.br",
        "imap_port": 993,
        "smtp_host": "mail.hostgator.com.br",
        "smtp_port": 587,
    },
    "uol": {
        "label": "UOL Mail",
        "imap_host": "imap.uol.com.br",
        "imap_port": 993,
        "smtp_host": "smtp.uol.com.br",
        "smtp_port": 587,
    },
    "terra": {
        "label": "Terra",
        "imap_host": "imap.terra.com.br",
        "imap_port": 993,
        "smtp_host": "smtp.terra.com.br",
        "smtp_port": 587,
    },
    "custom": {
        "label": "Personalizado (IMAP/SMTP próprio)",
        "imap_host": "",
        "imap_port": 993,
        "smtp_host": "",
        "smtp_port": 587,
    },
}

_NOT_CONFIGURED_MSG = (
    "⚠️ Nenhuma conta de email configurada. "
    "Acesse /settings.html → Emails (IMAP/SMTP) → Adicionar Conta."
)


class ImapService:
    """
    Universal IMAP/SMTP email service.
    Supports any email provider with IMAP/SMTP access.
    Passwords are encrypted with Fernet (derived from JWT_SECRET).
    """

    # ============================================
    # Encryption helpers
    # ============================================

    def _get_fernet(self):
        """Derive a Fernet cipher from JWT_SECRET (deterministic — survives restarts)."""
        from cryptography.fernet import Fernet
        key_bytes = hashlib.sha256(settings.JWT_SECRET.encode()).digest()  # 32 bytes
        key_b64 = base64.urlsafe_b64encode(key_bytes)
        return Fernet(key_b64)

    def _encrypt(self, plaintext: str) -> str:
        return self._get_fernet().encrypt(plaintext.encode()).decode()

    def _decrypt(self, encrypted: str) -> str:
        return self._get_fernet().decrypt(encrypted.encode()).decode()

    # ============================================
    # Account Management
    # ============================================

    async def add_account(
        self,
        user_id: str,
        email: str,
        password: str,
        provider: str = "custom",
        imap_host: str = "",
        imap_port: int = 993,
        smtp_host: str = "",
        smtp_port: int = 587,
        username: str = "",
        display_name: str = "",
    ) -> dict:
        """
        Add (or update) an IMAP/SMTP account for a user.
        Password is encrypted before storing.
        Provider preset fills host/port if not provided manually.
        """
        # Apply preset if applicable
        preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["custom"])
        if not imap_host:
            imap_host = preset["imap_host"]
        if not smtp_host:
            smtp_host = preset["smtp_host"]
        if not imap_host or not smtp_host:
            return {"ok": False, "error": "imap_host e smtp_host são obrigatórios para provider 'custom'"}

        # Username defaults to email address
        if not username:
            username = email

        encrypted_pwd = self._encrypt(password)

        try:
            from sqlalchemy import text
            from src.infra.supabase_client import get_async_session

            async with get_async_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO imap_accounts
                            (user_id, email, provider, imap_host, imap_port,
                             smtp_host, smtp_port, username, password_encrypted,
                             display_name, updated_at)
                        VALUES (:uid, :email, :provider, :imap_host, :imap_port,
                                :smtp_host, :smtp_port, :username, :pwd,
                                :display_name, NOW())
                        ON CONFLICT (user_id, email) DO UPDATE SET
                            provider = EXCLUDED.provider,
                            imap_host = EXCLUDED.imap_host,
                            imap_port = EXCLUDED.imap_port,
                            smtp_host = EXCLUDED.smtp_host,
                            smtp_port = EXCLUDED.smtp_port,
                            username = EXCLUDED.username,
                            password_encrypted = EXCLUDED.password_encrypted,
                            display_name = EXCLUDED.display_name,
                            updated_at = NOW()
                    """),
                    {
                        "uid": user_id, "email": email, "provider": provider,
                        "imap_host": imap_host, "imap_port": imap_port,
                        "smtp_host": smtp_host, "smtp_port": smtp_port,
                        "username": username, "pwd": encrypted_pwd,
                        "display_name": display_name or email,
                    },
                )
                await session.commit()

            logger.info(f"IMAP account added for user {user_id}: {email} ({provider})")
            return {"ok": True, "email": email, "provider": provider}

        except Exception as e:
            logger.error(f"IMAP add_account error for user {user_id}: {e}")
            return {"ok": False, "error": str(e)}

    async def list_accounts(self, user_id: str) -> list[dict]:
        """List IMAP accounts for a user (no passwords returned)."""
        try:
            from sqlalchemy import text
            from src.infra.supabase_client import get_async_session

            async with get_async_session() as session:
                result = await session.execute(
                    text("""
                        SELECT email, provider, imap_host, imap_port,
                               smtp_host, smtp_port, display_name, is_active, created_at
                        FROM imap_accounts
                        WHERE user_id = :uid
                        ORDER BY created_at ASC
                    """),
                    {"uid": user_id},
                )
                rows = result.fetchall()

            return [
                {
                    "email": r[0], "provider": r[1],
                    "imap_host": r[2], "imap_port": r[3],
                    "smtp_host": r[4], "smtp_port": r[5],
                    "display_name": r[6] or r[0],
                    "is_active": r[7],
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"IMAP list_accounts error for user {user_id}: {e}")
            return []

    async def remove_account(self, user_id: str, email: str) -> bool:
        """Remove an IMAP account."""
        try:
            from sqlalchemy import text
            from src.infra.supabase_client import get_async_session

            async with get_async_session() as session:
                await session.execute(
                    text("DELETE FROM imap_accounts WHERE user_id = :uid AND email = :email"),
                    {"uid": user_id, "email": email},
                )
                await session.commit()

            logger.info(f"IMAP account removed for user {user_id}: {email}")
            return True
        except Exception as e:
            logger.error(f"IMAP remove_account error for user {user_id}: {e}")
            return False

    async def test_connection(self, user_id: str, email: str) -> dict:
        """Test IMAP connection for a configured account."""
        creds = await self._get_credentials(user_id, email)
        if not creds:
            return {"ok": False, "message": "Conta não encontrada."}

        try:
            import aioimaplib
            imap = aioimaplib.IMAP4_SSL(host=creds["imap_host"], port=creds["imap_port"])
            await imap.wait_hello_from_server()
            await imap.login(creds["username"], creds["password"])
            await imap.logout()
            return {"ok": True, "message": f"✅ Conexão IMAP bem-sucedida para {email}"}
        except Exception as e:
            logger.warning(f"IMAP test_connection failed for {email}: {e}")
            return {"ok": False, "message": f"❌ Falha na conexão: {e}"}

    # ============================================
    # Credentials (internal)
    # ============================================

    async def _get_credentials(self, user_id: str, account_email: str = "") -> dict | None:
        """
        Load and decrypt credentials for a specific account (or the first active one).
        Returns None if no account configured.
        """
        try:
            from sqlalchemy import text
            from src.infra.supabase_client import get_async_session

            async with get_async_session() as session:
                if account_email:
                    result = await session.execute(
                        text("""
                            SELECT email, username, password_encrypted,
                                   imap_host, imap_port, smtp_host, smtp_port
                            FROM imap_accounts
                            WHERE user_id = :uid AND email = :email AND is_active = TRUE
                        """),
                        {"uid": user_id, "email": account_email},
                    )
                else:
                    result = await session.execute(
                        text("""
                            SELECT email, username, password_encrypted,
                                   imap_host, imap_port, smtp_host, smtp_port
                            FROM imap_accounts
                            WHERE user_id = :uid AND is_active = TRUE
                            ORDER BY created_at ASC
                            LIMIT 1
                        """),
                        {"uid": user_id},
                    )
                row = result.fetchone()

            if not row:
                return None

            return {
                "email": row[0],
                "username": row[1],
                "password": self._decrypt(row[2]),
                "imap_host": row[3],
                "imap_port": row[4],
                "smtp_host": row[5],
                "smtp_port": row[6],
            }
        except Exception as e:
            logger.error(f"IMAP _get_credentials error for user {user_id}: {e}")
            return None

    # ============================================
    # Read Emails (IMAP)
    # ============================================

    async def read_emails(
        self,
        user_id: str,
        query: str = "",
        account_email: str = "",
        max_results: int = 10,
    ) -> str:
        """
        Read emails via IMAP.

        Query syntax (subset of Gmail-style):
          is:unread → UNSEEN
          from:boss@co.com → FROM boss@co.com
          subject:meeting → SUBJECT meeting
          newer_than:3d → SINCE (3 days ago)
          "" (empty) → ALL (last N emails)
        """
        creds = await self._get_credentials(user_id, account_email)
        if not creds:
            return _NOT_CONFIGURED_MSG

        try:
            import aioimaplib
            imap_criteria = self._translate_query(query)

            imap = aioimaplib.IMAP4_SSL(
                host=creds["imap_host"], port=creds["imap_port"]
            )
            await imap.wait_hello_from_server()
            await imap.login(creds["username"], creds["password"])
            await imap.select("INBOX")

            _, data = await imap.search(imap_criteria)
            if not data or not data[0]:
                await imap.logout()
                return f"📭 Nenhum email encontrado{' para: ' + query if query else ''}."

            # data[0] is bytes like b"1 2 3 4 5"
            msg_ids = data[0].split() if isinstance(data[0], bytes) else []
            if not msg_ids:
                await imap.logout()
                return f"📭 Nenhum email encontrado{' para: ' + query if query else ''}."

            # Fetch the most recent N emails (last in list = newest)
            ids_to_fetch = msg_ids[-max_results:]

            lines = [f"📧 **{len(ids_to_fetch)} email(s) — {creds['email']}:**\n"]

            for msg_id in reversed(ids_to_fetch):
                try:
                    mid_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                    _, msg_data = await imap.fetch(
                        mid_str,
                        "(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)])",
                    )
                    # aioimaplib fetch response varies by server:
                    # Format 1 (separate): [b'N (BODY... {size}', b'From: ...\r\n...', b')']
                    # Format 2 (combined): [b'N (BODY... {size}\r\nFrom: ...\r\n\r\n)', b')']
                    # IMPORTANT: always try to extract AFTER {size}\r\n FIRST,
                    # before doing a plain content search (to avoid IMAP metadata prefix).
                    raw_header = b""
                    _HEADER_MARKERS = (b"from:", b"subject:", b"date:", b"to:")
                    for part in msg_data:
                        if not isinstance(part, bytes) or not part.strip():
                            continue
                        # Case B FIRST: extract after literal {size}\r\n marker
                        # This handles Format 2 where metadata and headers are in the same part
                        m = re.search(rb"\{\d+\}\r\n([\s\S]+)", part)
                        if m:
                            candidate = m.group(1).rstrip(b" )\r\n")
                            if candidate and any(h in candidate.lower() for h in _HEADER_MARKERS):
                                raw_header = candidate
                                break
                        # Case A: part is pure header content (Format 1 — separate item)
                        # Only use if part does NOT contain {size} (not IMAP metadata)
                        elif b"{" not in part:
                            if any(h in part.lower() for h in _HEADER_MARKERS):
                                raw_header = part
                                break
                    # Case C: nothing matched — fallback to full RFC822.HEADER fetch
                    if not raw_header:
                        try:
                            _, hdr_data = await imap.fetch(mid_str, "(RFC822.HEADER)")
                            for hpart in hdr_data:
                                if not isinstance(hpart, bytes) or not hpart.strip():
                                    continue
                                # Same strategy: extract after literal first
                                m2 = re.search(rb"\{\d+\}\r\n([\s\S]+)", hpart)
                                if m2:
                                    candidate = m2.group(1).rstrip(b" )\r\n")
                                    if any(h in candidate.lower() for h in _HEADER_MARKERS):
                                        raw_header = candidate
                                        break
                                elif b"{" not in hpart and any(h in hpart.lower() for h in _HEADER_MARKERS):
                                    raw_header = hpart
                                    break
                        except Exception:
                            pass

                    msg = message_from_bytes(raw_header)
                    subject = _decode_header_value(msg.get("Subject", "(sem assunto)"))
                    sender = _decode_header_value(msg.get("From", "Desconhecido"))
                    date = msg.get("Date", "")[:30]

                    lines.append(
                        f"- **{subject}**\n"
                        f"  De: {sender}\n"
                        f"  📅 {date} | ID: `{mid_str}`"
                    )
                except Exception as e:
                    logger.debug(f"IMAP fetch error for msg {msg_id}: {e}")
                    continue

            await imap.logout()
            return "\n".join(lines)

        except Exception as e:
            logger.error(f"IMAP read_emails error for user {user_id}: {e}")
            return f"❌ Erro ao ler emails de {creds.get('email', account_email)}: {e}"

    async def get_email_body(
        self,
        user_id: str,
        message_id: str,
        account_email: str = "",
    ) -> str:
        """Fetch full body of a specific email by IMAP sequence number."""
        creds = await self._get_credentials(user_id, account_email)
        if not creds:
            return _NOT_CONFIGURED_MSG

        try:
            import aioimaplib
            imap = aioimaplib.IMAP4_SSL(host=creds["imap_host"], port=creds["imap_port"])
            await imap.wait_hello_from_server()
            await imap.login(creds["username"], creds["password"])
            await imap.select("INBOX")

            _, msg_data = await imap.fetch(message_id, "(RFC822)")

            raw = b""
            for part in msg_data:
                if isinstance(part, bytes) and len(part) > 100:
                    raw = part
                    break

            msg = message_from_bytes(raw)
            subject = _decode_header_value(msg.get("Subject", "(sem assunto)"))
            sender = _decode_header_value(msg.get("From", ""))
            date = msg.get("Date", "")

            body = _extract_text_body(msg)
            await imap.logout()

            return (
                f"**Email:** {subject}\n"
                f"**De:** {sender}\n"
                f"**Data:** {date}\n\n"
                f"---\n{body[:4000]}"
            )

        except Exception as e:
            logger.error(f"IMAP get_email_body error for user {user_id}: {e}")
            return f"❌ Erro ao ler email: {e}"

    # ============================================
    # Send Email (SMTP)
    # ============================================

    async def send_email(
        self,
        user_id: str,
        to: str,
        subject: str,
        body: str,
        from_account: str = "",
        cc: str = "",
    ) -> str:
        """
        Send an email via SMTP.

        IMPORTANT: Agent must show full draft and get user approval before calling.

        Args:
            from_account: Email address of the IMAP account to use (empty = first configured)
        """
        creds = await self._get_credentials(user_id, from_account)
        if not creds:
            return _NOT_CONFIGURED_MSG

        try:
            import aiosmtplib

            # Build MIME message
            mime_msg = MIMEMultipart("alternative")
            mime_msg["From"] = creds["email"]
            mime_msg["To"] = to
            mime_msg["Subject"] = subject
            if cc:
                mime_msg["Cc"] = cc

            mime_msg.attach(MIMEText(body, "plain", "utf-8"))

            recipients = [to]
            if cc:
                recipients.extend([a.strip() for a in cc.split(",") if a.strip()])

            await aiosmtplib.send(
                mime_msg,
                hostname=creds["smtp_host"],
                port=creds["smtp_port"],
                username=creds["username"],
                password=creds["password"],
                use_tls=(creds["smtp_port"] == 465),
                start_tls=(creds["smtp_port"] != 465),
                timeout=30,
            )

            logger.info(f"SMTP email sent for user {user_id} via {creds['email']} → {to}")
            return (
                f"✅ E-mail enviado com sucesso!\n"
                f"📧 **Para:** {to}\n"
                f"📋 **Assunto:** {subject}\n"
                f"📤 **De:** {creds['email']}"
            )

        except Exception as e:
            logger.error(f"SMTP send_email error for user {user_id}: {e}")
            return f"❌ Erro ao enviar e-mail: {e}"

    # ============================================
    # Query translation
    # ============================================

    def _translate_query(self, query: str) -> str:
        """
        Translate Gmail-style query syntax to IMAP SEARCH criteria.
        Falls back to TEXT search for unrecognized patterns.
        """
        if not query or not query.strip():
            return "ALL"

        parts = []

        # is:unread / is:read
        if re.search(r'\bis:unread\b', query, re.I):
            parts.append("UNSEEN")
        elif re.search(r'\bis:read\b', query, re.I):
            parts.append("SEEN")

        # from:email
        m = re.search(r'\bfrom:(\S+)', query, re.I)
        if m:
            parts.append(f'FROM "{m.group(1)}"')

        # to:email
        m = re.search(r'\bto:(\S+)', query, re.I)
        if m:
            parts.append(f'TO "{m.group(1)}"')

        # subject:text (up to next keyword or end)
        m = re.search(r'\bsubject:([^\s:]+(?:\s+[^\s:]+)*?)(?=\s+\w+:|$)', query, re.I)
        if m:
            parts.append(f'SUBJECT "{m.group(1).strip()}"')

        # newer_than:Nd / Nh / Nw
        m = re.search(r'\bnewer_than:(\d+)([dhw])\b', query, re.I)
        if m:
            n = int(m.group(1))
            unit = m.group(2).lower()
            days = n if unit == 'd' else (n // 24 or 1) if unit == 'h' else n * 7
            since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
            parts.append(f"SINCE {since}")

        # older_than:Nd
        m = re.search(r'\bolder_than:(\d+)([dhw])\b', query, re.I)
        if m:
            n = int(m.group(1))
            unit = m.group(2).lower()
            days = n if unit == 'd' else (n // 24 or 1) if unit == 'h' else n * 7
            before = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%d-%b-%Y")
            parts.append(f"BEFORE {before}")

        # Fallback: treat as TEXT search
        if not parts:
            safe = query.replace('"', '').strip()
            parts.append(f'TEXT "{safe}"')

        return " ".join(parts)


# ============================================
# Email parsing helpers
# ============================================

def _decode_header_value(value: str) -> str:
    """Decode RFC 2047 encoded email headers."""
    if not value:
        return ""
    try:
        parts = decode_header(value)
        decoded = []
        for text, charset in parts:
            if isinstance(text, bytes):
                decoded.append(text.decode(charset or "utf-8", errors="replace"))
            else:
                decoded.append(str(text))
        return " ".join(decoded)
    except Exception:
        return value


def _extract_text_body(msg) -> str:
    """Extract plain text body from a parsed email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        # Fallback: try text/html
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    text = payload.decode(charset, errors="replace")
                    # Strip basic HTML tags
                    return re.sub(r"<[^>]+>", " ", text)[:3000]
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return "(corpo não disponível)"


# Singleton
imap_service = ImapService()
