"""
Agent Optimus — MCP Tools.
Native MCP tool definitions for agent capabilities.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """Definition of an MCP tool."""
    name: str
    description: str
    category: str  # db, fs, research, browser, terminal, custom
    parameters: dict[str, dict] = field(default_factory=dict)  # JSON Schema
    handler: Callable[..., Coroutine] | None = None
    requires_approval: bool = False  # Destructive operations need user approval
    agent_levels: list[str] = field(default_factory=lambda: ["lead", "specialist", "intern"])


@dataclass
class ToolResult:
    """Result from executing an MCP tool."""
    success: bool
    output: Any = None
    error: str | None = None
    tool_name: str = ""


class MCPToolRegistry:
    """
    Registry for native MCP tools.
    Provides tool definitions, execution, and manifest generation.
    """

    def __init__(self):
        self._tools: dict[str, MCPTool] = {}
        self._register_native_tools()

    def register(self, tool: MCPTool):
        """Register an MCP tool."""
        self._tools[tool.name] = tool
        logger.debug(f"MCP Tool registered: {tool.name} ({tool.category})")

    def get(self, name: str) -> MCPTool | None:
        return self._tools.get(name)

    def list_tools(self, category: str | None = None, agent_level: str | None = None) -> list[MCPTool]:
        """List tools, optionally filtered by category or agent level."""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        if agent_level:
            tools = [t for t in tools if agent_level in t.agent_levels]
        return tools

    async def execute(self, tool_name: str, params: dict, agent_name: str = "", user_id: str = "") -> ToolResult:
        """Execute a tool by name. user_id is per-request (avoids singleton mutation race condition)."""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{tool_name}' not found", tool_name=tool_name)

        if not tool.handler:
            return ToolResult(success=False, error=f"Tool '{tool_name}' has no handler", tool_name=tool_name)

        # Set user_id for this execution only (thread-local-style via kwarg override)
        if user_id:
            self._user_id = user_id

        try:
            logger.info(f"MCP executing: {tool_name}", extra={"props": {
                "tool": tool_name, "agent": agent_name, "category": tool.category,
            }})

            output = await tool.handler(**params)
            return ToolResult(success=True, output=output, tool_name=tool_name)

        except Exception as e:
            logger.error(f"MCP tool '{tool_name}' failed: {e}")
            return ToolResult(success=False, error=str(e), tool_name=tool_name)

    def generate_manifest(self) -> str:
        """Generate TOOLS.md manifest with all registered tools."""
        lines = ["# 🔧 MCP Tools Manifest\n", "_Auto-generated_\n"]

        categories = sorted(set(t.category for t in self._tools.values()))

        for category in categories:
            lines.append(f"\n## {category.upper()}\n")
            tools = [t for t in self._tools.values() if t.category == category]

            for tool in sorted(tools, key=lambda t: t.name):
                approval = " ⚠️ **requires approval**" if tool.requires_approval else ""
                levels = ", ".join(tool.agent_levels)
                lines.append(f"### `{tool.name}`{approval}")
                lines.append(f"{tool.description}")
                lines.append(f"_Levels: {levels}_\n")

                if tool.parameters:
                    lines.append("**Parameters:**")
                    for param_name, param_def in tool.parameters.items():
                        param_type = param_def.get("type", "string")
                        required = " *(required)*" if param_def.get("required") else ""
                        desc = param_def.get("description", "")
                        lines.append(f"- `{param_name}` ({param_type}){required}: {desc}")
                    lines.append("")

        return "\n".join(lines)

    # ============================================
    # Native Tools Registration
    # ============================================

    def _register_native_tools(self):
        """Register built-in MCP tools."""

        # --- Database Tools ---
        self.register(MCPTool(
            name="db_query",
            description="Execute a read-only SQL query against the database",
            category="db",
            parameters={
                "query": {"type": "string", "required": True, "description": "SQL SELECT query"},
                "limit": {"type": "integer", "description": "Max rows to return (default: 100)"},
            },
            handler=self._tool_db_query,
        ))

        self.register(MCPTool(
            name="db_execute",
            description="Execute a write SQL statement (INSERT, UPDATE, DELETE)",
            category="db",
            parameters={
                "statement": {"type": "string", "required": True, "description": "SQL statement"},
            },
            handler=self._tool_db_execute,
            requires_approval=True,
            agent_levels=["lead", "specialist"],
        ))

        # --- File System Tools ---
        self.register(MCPTool(
            name="fs_read",
            description="Read contents of a file",
            category="fs",
            parameters={
                "path": {"type": "string", "required": True, "description": "File path"},
            },
            handler=self._tool_fs_read,
        ))

        self.register(MCPTool(
            name="fs_write",
            description="Write content to a file",
            category="fs",
            parameters={
                "path": {"type": "string", "required": True, "description": "File path"},
                "content": {"type": "string", "required": True, "description": "Content to write"},
            },
            handler=self._tool_fs_write,
            requires_approval=True,
            agent_levels=["lead", "specialist"],
        ))

        self.register(MCPTool(
            name="fs_list",
            description="List files in a directory",
            category="fs",
            parameters={
                "path": {"type": "string", "required": True, "description": "Directory path"},
                "pattern": {"type": "string", "description": "Glob pattern filter"},
            },
            handler=self._tool_fs_list,
        ))

        # --- Finance Tools ---
        self.register(MCPTool(
            name="get_exchange_rate",
            description=(
                "Get real-time currency exchange rates. Use this when the user asks about "
                "dollar price (dólar), euro, or any currency. Supports pairs like USD-BRL, "
                "EUR-BRL, BTC-BRL, GBP-BRL, etc."
            ),
            category="research",
            parameters={
                "pairs": {
                    "type": "string",
                    "required": True,
                    "description": "Currency pairs separated by commas, e.g. 'USD-BRL' or 'USD-BRL,EUR-BRL,BTC-BRL'",
                },
            },
            handler=self._tool_get_exchange_rate,
        ))

        # --- Research Tools ---
        self.register(MCPTool(
            name="research_search",
            description="Search the web for information",
            category="research",
            parameters={
                "query": {"type": "string", "required": True, "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results (default: 5)"},
            },
            handler=self._tool_research_search,
        ))

        self.register(MCPTool(
            name="research_fetch_url",
            description=(
                "Read the full content of any URL as clean text/markdown. "
                "Uses Jina Reader (free) — ideal for reading news articles, blog posts, documentation. "
                "Use this after research_search returns URLs you want to read in depth."
            ),
            category="research",
            parameters={
                "url": {"type": "string", "required": True, "description": "URL to read (must start with http:// or https://)"},
            },
            handler=self._tool_research_fetch_url,
        ))

        # --- Knowledge Base (RAG) Tools ---
        from src.skills.knowledge_tool import search_knowledge_base
        self.register(MCPTool(
            name="search_knowledge_base",
            description="Search the company knowledge base / long-term memory for documents and information.",
            category="research",
            handler=search_knowledge_base,
            parameters={
                "query": {"type": "string", "required": True, "description": "The question or topic to search for."},
                "limit": {"type": "integer", "description": "Max results (default 5)."},
            },
            agent_levels=["lead", "specialist"]
        ))
        
        # --- Memory Tools ---
        self.register(MCPTool(
            name="memory_search",
            description="Search agent's long-term memory",
            category="memory",
            parameters={
                "agent_name": {"type": "string", "required": True, "description": "Agent name"},
                "query": {"type": "string", "required": True, "description": "Search query"},
            },
            handler=self._tool_memory_search,
        ))

        self.register(MCPTool(
            name="memory_learn",
            description="Add a learning to agent's long-term memory",
            category="memory",
            parameters={
                "agent_name": {"type": "string", "required": True, "description": "Agent name"},
                "category": {"type": "string", "required": True, "description": "Learning category"},
                "learning": {"type": "string", "required": True, "description": "The learning"},
            },
            handler=self._tool_memory_learn,
        ))

        # --- Scheduling Tools ---
        self.register(MCPTool(
            name="schedule_reminder",
            description=(
                "Schedule a future reminder or action. Use this when the user asks you to "
                "remind them about something in N minutes/hours, or to do something later. "
                "Creates a persistent cron job AND a visible task. "
                "NOTE: The reminder will appear in logs/task list, but real push notification "
                "to the user requires them to be in the chat (no background push yet)."
            ),
            category="tasks",
            parameters={
                "message": {"type": "string", "required": True, "description": "What to remind about"},
                "minutes": {"type": "integer", "description": "Minutes from now (default: 10)"},
            },
            handler=self._tool_schedule_reminder,
        ))

        # --- Task Management Tools ---
        self.register(MCPTool(
            name="task_create",
            description="Create a new task in the task manager. Use this when the user asks you to create, add or register a task.",
            category="tasks",
            parameters={
                "title": {"type": "string", "required": True, "description": "Task title"},
                "description": {"type": "string", "description": "Task details or context"},
                "priority": {"type": "string", "description": "Priority: low | medium | high | urgent (default: medium)"},
            },
            handler=self._tool_task_create,
        ))

        self.register(MCPTool(
            name="task_list",
            description="List tasks from the task manager. Optionally filter by status.",
            category="tasks",
            parameters={
                "status": {"type": "string", "description": "Filter by status: inbox | assigned | in_progress | review | done | blocked"},
                "limit": {"type": "integer", "description": "Max tasks to return (default: 10)"},
            },
            handler=self._tool_task_list,
        ))

        self.register(MCPTool(
            name="task_update",
            description="Update the status of a task. Use task_list first to get the task ID.",
            category="tasks",
            parameters={
                "task_id": {"type": "string", "required": True, "description": "Task UUID from task_list"},
                "status": {"type": "string", "required": True, "description": "New status: inbox | assigned | in_progress | review | done | blocked"},
            },
            handler=self._tool_task_update,
        ))

        # --- Browser Tools (FASE 2B) ---
        self.register(MCPTool(
            name="browser_navigate",
            description=(
                "Navigate to a URL and return the page title, status, and a text preview. "
                "Use this to open any website, check if it loads, and get initial content."
            ),
            category="browser",
            parameters={
                "url": {"type": "string", "required": True, "description": "Full URL (must start with http:// or https://)"},
            },
            handler=self._tool_browser_navigate,
        ))

        self.register(MCPTool(
            name="browser_extract",
            description=(
                "Navigate to a URL and extract text from a CSS selector. "
                "Use this to scrape articles, prices, lists, tables from any page. "
                "If unsure about selector, use 'body' to get all page text."
            ),
            category="browser",
            parameters={
                "url": {"type": "string", "required": True, "description": "Full URL to navigate"},
                "selector": {"type": "string", "description": "CSS selector to extract (default: 'body')"},
            },
            handler=self._tool_browser_extract,
        ))

        self.register(MCPTool(
            name="browser_search",
            description=(
                "Navigate to a website and perform a search (fills search box + presses Enter). "
                "Ideal for e-commerce (Mercado Livre, Amazon), news sites, or any site with a search bar. "
                "Returns extracted search results text."
            ),
            category="browser",
            parameters={
                "url": {"type": "string", "required": True, "description": "Website URL (e.g. https://www.mercadolivre.com.br)"},
                "query": {"type": "string", "required": True, "description": "Search query text"},
            },
            handler=self._tool_browser_search,
        ))

        self.register(MCPTool(
            name="browser_screenshot",
            description="Take a screenshot of any webpage. Returns base64-encoded PNG.",
            category="browser",
            parameters={
                "url": {"type": "string", "required": True, "description": "Full URL to screenshot"},
            },
            handler=self._tool_browser_screenshot,
            agent_levels=["lead", "specialist"],
        ))

        self.register(MCPTool(
            name="browser_pdf",
            description="Generate a PDF of any webpage. Returns base64-encoded PDF.",
            category="browser",
            parameters={
                "url": {"type": "string", "required": True, "description": "Full URL to convert to PDF"},
            },
            handler=self._tool_browser_pdf,
            agent_levels=["lead", "specialist"],
        ))

        # --- Google Workspace Tools (FASE 4) ---
        self.register(MCPTool(
            name="gmail_read",
            description=(
                "Search and list emails from the Gmail account connected via Google OAuth. "
                "ONLY for Gmail/Google accounts (@gmail.com or Google Workspace). "
                "For Outlook, corporate, Yahoo, etc. use email_read instead. "
                "Common queries: "
                "'' (empty) = inbox, "
                "'is:unread' = unread only, "
                "'is:unread newer_than:1d' = unread today, "
                "'newer_than:1d' = all from today, "
                "'from:boss@co.com' = from specific sender, "
                "'after:2026/02/18' = after date, "
                "'after:2026/02/18 14:00' = after date+time (auto-converts to timestamp). "
                "Combine freely: 'is:unread from:alice newer_than:3d'."
            ),
            category="google",
            parameters={
                "query": {"type": "string", "description": "Gmail search query. Empty string = show inbox. Examples: 'is:unread', 'newer_than:1d', 'from:boss@co.com after:2026/02/18'."},
                "max_results": {"type": "integer", "description": "Max emails to return (default: 10)"},
            },
            handler=self._tool_gmail_read,
        ))

        self.register(MCPTool(
            name="gmail_get",
            description="Read the full content of a specific Gmail email by its message ID. Returns subject, sender, date and full body text.",
            category="google",
            parameters={
                "message_id": {"type": "string", "required": True, "description": "Gmail message ID (from gmail_read results)"},
            },
            handler=self._tool_gmail_get,
        ))

        self.register(MCPTool(
            name="calendar_list",
            description="List upcoming Google Calendar events for the next N days. Returns event title, start/end time, location. Use days_ahead=1 for today only, days_ahead=7 for this week.",
            category="google",
            parameters={
                "days_ahead": {"type": "integer", "description": "Number of days ahead to check (default: 7)"},
            },
            handler=self._tool_calendar_list,
        ))

        self.register(MCPTool(
            name="calendar_search",
            description="Search Google Calendar events by keyword. Returns matching events with title and start time.",
            category="google",
            parameters={
                "query": {"type": "string", "required": True, "description": "Search text to find in event titles and descriptions"},
            },
            handler=self._tool_calendar_search,
        ))

        self.register(MCPTool(
            name="drive_search",
            description="Search for files and documents in Google Drive by name or content. Returns file names, types and links.",
            category="google",
            parameters={
                "query": {"type": "string", "required": True, "description": "Search text to find in file names or content"},
                "max_results": {"type": "integer", "description": "Max files to return (default: 10)"},
            },
            handler=self._tool_drive_search,
        ))

        self.register(MCPTool(
            name="drive_read",
            description="Read the text content of a Google Drive file (Google Docs, Sheets, or other files). Returns up to 4000 chars of content (truncated for large files).",
            category="google",
            parameters={
                "file_id": {"type": "string", "required": True, "description": "Google Drive file ID (from drive_search results)"},
            },
            handler=self._tool_drive_read,
        ))

        self.register(MCPTool(
            name="gmail_send",
            description=(
                "Send an email via Gmail. "
                "IMPORTANT: ALWAYS show the full email draft (to, subject, body) to the user and wait for explicit approval BEFORE calling this tool. "
                "Never send without user confirmation."
            ),
            category="google",
            parameters={
                "to": {"type": "string", "required": True, "description": "Recipient email address"},
                "subject": {"type": "string", "required": True, "description": "Email subject line"},
                "body": {"type": "string", "required": True, "description": "Email body (plain text)"},
                "cc": {"type": "string", "description": "CC email address (optional)"},
            },
            handler=self._tool_gmail_send,
            requires_approval=True,
        ))

        self.register(MCPTool(
            name="gmail_mark_read",
            description="Mark a Gmail email as read. Use gmail_read first to get the message_id.",
            category="google",
            parameters={
                "message_id": {"type": "string", "required": True, "description": "Gmail message ID (from gmail_read results)"},
            },
            handler=self._tool_gmail_mark_read,
        ))

        self.register(MCPTool(
            name="gmail_archive",
            description="Archive a Gmail email (removes from inbox, keeps in All Mail). Use gmail_read first to get the message_id.",
            category="google",
            parameters={
                "message_id": {"type": "string", "required": True, "description": "Gmail message ID (from gmail_read results)"},
            },
            handler=self._tool_gmail_archive,
        ))

        self.register(MCPTool(
            name="gmail_trash",
            description=(
                "Move a Gmail email to trash. "
                "IMPORTANT: Show the email subject/sender and wait for user confirmation before calling."
            ),
            category="google",
            parameters={
                "message_id": {"type": "string", "required": True, "description": "Gmail message ID (from gmail_read results)"},
            },
            handler=self._tool_gmail_trash,
            requires_approval=True,
        ))

        self.register(MCPTool(
            name="gmail_add_label",
            description="Add a label to a Gmail email. Creates the label if it doesn't exist. Use gmail_read first to get the message_id.",
            category="google",
            parameters={
                "message_id": {"type": "string", "required": True, "description": "Gmail message ID (from gmail_read results)"},
                "label_name": {"type": "string", "required": True, "description": "Label name to add (e.g. 'Importante', 'Projeto X')"},
            },
            handler=self._tool_gmail_add_label,
        ))

        # --- Google Calendar Write (FASE 4B) ---
        self.register(MCPTool(
            name="calendar_create_event",
            description=(
                "Create a new Google Calendar event. "
                "IMPORTANT: ALWAYS show the full event details (title, date, time, attendees) and wait for user approval BEFORE calling. "
                "Use ISO 8601 format for times, e.g. '2026-02-20T14:00:00'."
            ),
            category="google",
            parameters={
                "title": {"type": "string", "required": True, "description": "Event title/summary"},
                "start_time": {"type": "string", "required": True, "description": "Start datetime ISO 8601 (e.g. '2026-02-20T14:00:00')"},
                "end_time": {"type": "string", "required": True, "description": "End datetime ISO 8601 (e.g. '2026-02-20T15:00:00')"},
                "description": {"type": "string", "description": "Event description or notes"},
                "location": {"type": "string", "description": "Event location"},
                "attendees": {"type": "string", "description": "Comma-separated attendee emails (e.g. 'alice@gmail.com,bob@gmail.com')"},
                "timezone": {"type": "string", "description": "IANA timezone (default: America/Sao_Paulo)"},
            },
            handler=self._tool_calendar_create_event,
            requires_approval=True,
        ))

        self.register(MCPTool(
            name="calendar_update_event",
            description=(
                "Update an existing Google Calendar event. "
                "Use calendar_search or calendar_list first to get the event ID. "
                "IMPORTANT: Show proposed changes and wait for user confirmation before calling."
            ),
            category="google",
            parameters={
                "event_id": {"type": "string", "required": True, "description": "Google Calendar event ID (from calendar_search or calendar_list)"},
                "title": {"type": "string", "description": "New event title (leave empty to keep current)"},
                "start_time": {"type": "string", "description": "New start datetime ISO 8601 (leave empty to keep current)"},
                "end_time": {"type": "string", "description": "New end datetime ISO 8601 (leave empty to keep current)"},
                "description": {"type": "string", "description": "New description (leave empty to keep current)"},
                "location": {"type": "string", "description": "New location (leave empty to keep current)"},
            },
            handler=self._tool_calendar_update_event,
            requires_approval=True,
        ))

        self.register(MCPTool(
            name="calendar_delete_event",
            description=(
                "Delete a Google Calendar event permanently. "
                "IMPORTANT: ALWAYS confirm the event title and date with the user before deleting — this action is irreversible."
            ),
            category="google",
            parameters={
                "event_id": {"type": "string", "required": True, "description": "Google Calendar event ID (from calendar_search or calendar_list)"},
            },
            handler=self._tool_calendar_delete_event,
            requires_approval=True,
        ))

        # --- Google Drive Write (FASE 4B) ---
        self.register(MCPTool(
            name="drive_upload_text",
            description=(
                "Upload a text file to Google Drive. "
                "IMPORTANT: Show the file name and content preview to the user and wait for approval before calling."
            ),
            category="google",
            parameters={
                "filename": {"type": "string", "required": True, "description": "File name (e.g. 'Relatorio Q1.txt')"},
                "content": {"type": "string", "required": True, "description": "Text content of the file"},
                "folder_id": {"type": "string", "description": "Parent folder ID (optional, uploads to root if not specified)"},
            },
            handler=self._tool_drive_upload_text,
            requires_approval=True,
        ))

        self.register(MCPTool(
            name="drive_create_folder",
            description="Create a new folder in Google Drive.",
            category="google",
            parameters={
                "folder_name": {"type": "string", "required": True, "description": "Folder name"},
                "parent_id": {"type": "string", "description": "Parent folder ID (optional, creates in root if not specified)"},
            },
            handler=self._tool_drive_create_folder,
        ))

        # --- Google Contacts (FASE 4B) ---
        self.register(MCPTool(
            name="contacts_search",
            description="Search Google Contacts by name, email or phone number. Returns contact details.",
            category="google",
            parameters={
                "query": {"type": "string", "required": True, "description": "Search term (name, email, or phone)"},
                "max_results": {"type": "integer", "description": "Max contacts to return (default: 10)"},
            },
            handler=self._tool_contacts_search,
        ))

        self.register(MCPTool(
            name="contacts_list",
            description="List Google Contacts sorted by name. Returns names, emails and phone numbers.",
            category="google",
            parameters={
                "max_results": {"type": "integer", "description": "Max contacts to return (default: 20)"},
            },
            handler=self._tool_contacts_list,
        ))

        # --- IMAP/SMTP Universal Email Tools (FASE 4C) ---
        self.register(MCPTool(
            name="email_read",
            description=(
                "Read emails via IMAP from a configured account (Outlook, Office 365, Yahoo, corporate, etc.). "
                "ONLY for NON-Gmail accounts. For Gmail use gmail_read instead. "
                "IMPORTANT: Always pass account_email with the specific address. "
                "Common queries: "
                "'' (empty) = last 10 emails, "
                "'is:unread' = unread only, "
                "'newer_than:1d' = emails from today, "
                "'from:boss@co.com' = from specific sender, "
                "'subject:reunião' = by subject, "
                "'after:2026/02/18' = after date, "
                "'is:unread newer_than:3d' = combine filters. "
                "Also: 'before:2026/02/15', 'cc:user@co.com', 'has:attachment'."
            ),
            category="email",
            parameters={
                "query": {"type": "string", "description": "IMAP search query. Empty = last 10 emails. Examples: 'is:unread', 'newer_than:1d', 'from:boss@co.com'."},
                "account_email": {"type": "string", "description": "Specific email account to use (e.g. 'marcelo@tier.finance'). ALWAYS provide this when the user specifies an address."},
                "max_results": {"type": "integer", "description": "Max emails to return (default: 10)"},
            },
            handler=self._tool_email_read,
        ))

        self.register(MCPTool(
            name="email_get",
            description=(
                "Read the full body of a specific email by its IMAP message ID. "
                "Use email_read first to list emails and get the message ID."
            ),
            category="email",
            parameters={
                "message_id": {"type": "string", "required": True, "description": "IMAP message sequence number (from email_read results)"},
                "account_email": {"type": "string", "description": "Which email account to use (empty = first configured)"},
            },
            handler=self._tool_email_get,
        ))

        self.register(MCPTool(
            name="email_send",
            description=(
                "Send an email via SMTP from a configured IMAP/SMTP account (Outlook, Office 365, corporate, etc.). "
                "IMPORTANT: ALWAYS show the full email draft (to, subject, body, from_account) "
                "and wait for explicit user approval BEFORE calling this tool. Never send without confirmation."
            ),
            category="email",
            parameters={
                "to": {"type": "string", "required": True, "description": "Recipient email address"},
                "subject": {"type": "string", "required": True, "description": "Email subject line"},
                "body": {"type": "string", "required": True, "description": "Email body (plain text)"},
                "from_account": {"type": "string", "description": "Sender email account (empty = first configured account)"},
                "cc": {"type": "string", "description": "CC email addresses (comma-separated, optional)"},
            },
            handler=self._tool_email_send,
            requires_approval=True,
        ))

        self.register(MCPTool(
            name="email_list_accounts",
            description=(
                "List all IMAP/SMTP email accounts configured by the user (Outlook, corporate, Yahoo, etc.). "
                "Call this first whenever the user asks 'which email?' or mentions a specific address "
                "and you need to confirm it is configured as an IMAP account. "
                "Note: Gmail via Google OAuth is a SEPARATE system — it does NOT appear here. "
                "Use email_accounts_overview to see ALL accounts (Gmail + IMAP) at once."
            ),
            category="email",
            parameters={},
            handler=self._tool_email_list_accounts,
        ))

        self.register(MCPTool(
            name="email_accounts_overview",
            description=(
                "ALWAYS call this first when the user asks about emails or wants to know which accounts are configured. "
                "Returns a complete map of ALL email accounts: Gmail (Google OAuth) AND IMAP/SMTP accounts. "
                "Shows which tool to use for each account. "
                "Use this to decide whether to call gmail_read/gmail_send or email_read/email_send."
            ),
            category="email",
            parameters={},
            handler=self._tool_email_accounts_overview,
        ))

        # --- Apple iCloud Tools (FASE 8) ---
        self.register(MCPTool(
            name="apple_calendar_list",
            description=(
                "List upcoming events from iCloud Calendar (Apple). "
                "Use for @me.com, @icloud.com or @mac.com Apple accounts. "
                "Requires iCloud configured in /settings.html → Apple iCloud. "
                "Example: 'meus eventos essa semana no iCloud' → days_ahead=7."
            ),
            category="calendar",
            parameters={
                "days_ahead": {"type": "integer", "description": "Days to look ahead (default: 7)"},
            },
            handler=self._tool_apple_calendar_list,
        ))

        self.register(MCPTool(
            name="apple_calendar_search",
            description=(
                "Search events by text in iCloud Calendar (Apple). "
                "Searches title and description across all calendars."
            ),
            category="calendar",
            parameters={
                "query": {"type": "string", "required": True, "description": "Text to search in event title/description"},
            },
            handler=self._tool_apple_calendar_search,
        ))

        self.register(MCPTool(
            name="apple_calendar_create",
            description=(
                "Create a new event in iCloud Calendar (Apple). "
                "ALWAYS show the event details to the user and get confirmation before calling. "
                "start/end must be ISO 8601 format: '2026-02-20T14:00:00'."
            ),
            category="calendar",
            parameters={
                "title": {"type": "string", "required": True, "description": "Event title"},
                "start": {"type": "string", "required": True, "description": "Start datetime ISO 8601 (e.g. '2026-02-20T14:00:00')"},
                "end": {"type": "string", "required": True, "description": "End datetime ISO 8601 (e.g. '2026-02-20T15:00:00')"},
                "notes": {"type": "string", "description": "Event notes/description (optional)"},
                "calendar_name": {"type": "string", "description": "Target calendar name (empty = default)"},
            },
            handler=self._tool_apple_calendar_create,
            requires_approval=True,
        ))

        self.register(MCPTool(
            name="apple_reminders_list",
            description=(
                "List reminders from iCloud Reminders app (Apple). "
                "Returns pending reminders by default. Use completed=true to include done items."
            ),
            category="tasks",
            parameters={
                "completed": {"type": "boolean", "description": "Include completed reminders (default: false)"},
            },
            handler=self._tool_apple_reminders_list,
        ))

        self.register(MCPTool(
            name="apple_reminders_create",
            description=(
                "Create a new reminder in iCloud Reminders (Apple). "
                "ALWAYS confirm with the user before creating."
            ),
            category="tasks",
            parameters={
                "title": {"type": "string", "required": True, "description": "Reminder title"},
                "due_date": {"type": "string", "description": "Due date ISO 8601 (e.g. '2026-02-20T09:00:00'), optional"},
            },
            handler=self._tool_apple_reminders_create,
            requires_approval=True,
        ))

        self.register(MCPTool(
            name="apple_contacts_search",
            description=(
                "Search contacts in iCloud Contacts (Apple). "
                "Searches by name, email, phone number, or company."
            ),
            category="contacts",
            parameters={
                "query": {"type": "string", "required": True, "description": "Name, email, phone, or company to search"},
            },
            handler=self._tool_apple_contacts_search,
        ))

        self.register(MCPTool(
            name="apple_contacts_list",
            description=(
                "List contacts from iCloud Contacts (Apple). "
                "Returns up to 'limit' contacts alphabetically."
            ),
            category="contacts",
            parameters={
                "limit": {"type": "integer", "description": "Max contacts to return (default: 20)"},
            },
            handler=self._tool_apple_contacts_list,
        ))

        # --- Voice / TTS Tool ---
        self.register(MCPTool(
            name="speak",
            description=(
                "Convert text to audio and deliver it to the user as a voice message. "
                "Use when the user asks for an audio response: 'me manda um áudio', "
                "'responda em voz', 'fala isso pra mim', 'quero ouvir', etc. "
                "Pass the full response text to be spoken."
            ),
            category="voice",
            parameters={
                "text": {"type": "string", "required": True, "description": "Text to convert to speech"},
            },
            handler=self._tool_speak,
            agent_levels=["intern", "specialist", "lead"],
        ))

        # --- Code Execution Tools ---
        self.register(MCPTool(
            name="code_execute",
            description="Execute Python or Bash code in a secure sandbox",
            category="technical",
            parameters={
                "language": {"type": "string", "required": True, "description": "Language: 'python' or 'bash'"},
                "code": {"type": "string", "required": True, "description": "The code or command to execute"},
            },
            handler=self._tool_code_execute,
            requires_approval=True,
            agent_levels=["lead", "specialist"],
        ))

    # ============================================
    # Tool Handlers
    # ============================================

    async def _tool_schedule_reminder(self, message: str, minutes: int = 10) -> str:
        """Schedule a future reminder via CronScheduler + TaskManager."""
        from datetime import datetime, timedelta, timezone
        from src.core.cron_scheduler import cron_scheduler, CronJob
        from src.collaboration.task_manager import task_manager, TaskCreate, TaskPriority

        if minutes < 1 or minutes > 1440:
            return "❌ Minutos deve ser entre 1 e 1440 (24h)."

        target_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        target_local = target_time.strftime("%H:%M")

        # 1. Create persistent cron job (survives restarts)
        job = CronJob(
            name=f"Lembrete: {message[:60]}",
            schedule_type="at",
            schedule_value=target_time.isoformat(),
            payload=message,
            delete_after_run=True,
        )
        job_id = cron_scheduler.add(job)

        # 2. Create a visible task so /task list shows it
        task = await task_manager.create(TaskCreate(
            title=f"⏰ Lembrete às {target_local}: {message}",
            description=f"Agendado para {target_time.strftime('%Y-%m-%d %H:%M')} UTC. Job ID: {job_id}",
            priority=TaskPriority.HIGH,
            created_by="optimus",
        ))

        return (
            f"⏰ **Lembrete agendado!**\n"
            f"- **Mensagem:** {message}\n"
            f"- **Em:** {minutes} minutos (~{target_local} UTC)\n"
            f"- **Job ID:** `{job_id}`\n"
            f"- **Task ID:** `{str(task.id)[:8]}`\n\n"
            f"_Use `/task list` para ver o lembrete. "
            f"Nota: o sistema enviará o lembrete via logs quando o tempo chegar. "
            f"Push para o chat será disponível em breve._"
        )

    async def _tool_task_create(self, title: str, description: str = "", priority: str = "medium") -> str:
        """Create a task in TaskManager."""
        from src.collaboration.task_manager import task_manager, TaskCreate, TaskPriority

        priority_map = {
            "low": TaskPriority.LOW,
            "medium": TaskPriority.MEDIUM,
            "high": TaskPriority.HIGH,
            "urgent": TaskPriority.URGENT,
        }
        task = await task_manager.create(TaskCreate(
            title=title,
            description=description,
            priority=priority_map.get(priority.lower(), TaskPriority.MEDIUM),
            created_by="optimus",
        ))
        return f"✅ Task criada com sucesso!\n- **Título:** {task.title}\n- **ID:** `{str(task.id)[:8]}`\n- **Prioridade:** {task.priority.value}\n- **Status:** {task.status.value}"

    async def _tool_task_list(self, status: str = "", limit: int = 10) -> str:
        """List tasks from TaskManager."""
        from src.collaboration.task_manager import task_manager, TaskStatus

        status_filter = None
        if status:
            try:
                status_filter = TaskStatus(status.lower())
            except ValueError:
                return f"❌ Status inválido: '{status}'. Use: inbox, assigned, in_progress, review, done, blocked"

        tasks = await task_manager.list_tasks(status=status_filter)
        if not tasks:
            return "📋 Nenhuma task encontrada."

        status_emoji = {
            "inbox": "📥", "assigned": "📌", "in_progress": "🔄",
            "review": "👀", "done": "✅", "blocked": "🚧",
        }
        lines = [f"📋 **{len(tasks)} task(s) encontrada(s):**\n"]
        for t in tasks[:limit]:
            emoji = status_emoji.get(t.status.value, "❓")
            lines.append(f"{emoji} **{t.title}**")
            lines.append(f"   ID: `{str(t.id)[:8]}` | Status: {t.status.value} | Prioridade: {t.priority.value}")
        return "\n".join(lines)

    async def _tool_task_update(self, task_id: str, status: str) -> str:
        """Update task status in TaskManager."""
        from src.collaboration.task_manager import task_manager, TaskStatus
        from uuid import UUID

        try:
            task_uuid = UUID(task_id) if len(task_id) == 36 else None
            if not task_uuid:
                # Try to find by partial ID
                tasks = await task_manager.list_tasks()
                matches = [t for t in tasks if str(t.id).startswith(task_id)]
                if not matches:
                    return f"❌ Task não encontrada com ID: `{task_id}`"
                task_uuid = matches[0].id
        except ValueError:
            return f"❌ ID inválido: `{task_id}`"

        try:
            new_status = TaskStatus(status.lower())
        except ValueError:
            return f"❌ Status inválido: '{status}'. Use: inbox, assigned, in_progress, review, done, blocked"

        task = await task_manager.transition(task_uuid, new_status, agent_name="optimus")
        if not task:
            return f"❌ Transição inválida. Verifique o status atual da task."

        return f"✅ Task atualizada!\n- **{task.title}**\n- Novo status: **{task.status.value}**"

    async def _tool_code_execute(self, language: str, code: str) -> str:
        """Execute code in sandbox."""
        from src.infra.sandbox import code_sandbox
        
        if language.lower() == "python":
            result = await code_sandbox.execute_python(code)
        elif language.lower() == "bash":
            result = await code_sandbox.execute_bash(code)
        else:
            return f"Unsupported language: {language}"

        status = "✅ Success" if result.success else "❌ Failed"
        output = [
            f"--- Execution Result ({status}) ---",
            f"Duration: {result.duration_ms:.1f}ms",
            f"Exit Code: {result.exit_code}",
            "",
            "**STDOUT:**",
            result.stdout or "(empty)",
            "",
            "**STDERR:**",
            result.stderr or "(empty)",
        ]
        return "\n".join(output)

    async def _tool_db_query(self, query: str, limit: int = 100) -> str:
        """Execute read-only query."""
        from src.infra.supabase_client import get_async_session
        from sqlalchemy import text

        async with get_async_session() as session:
            result = await session.execute(text(f"{query} LIMIT {limit}"))
            rows = result.fetchall()
            return str([dict(row._mapping) for row in rows])

    async def _tool_db_execute(self, statement: str) -> str:
        """Execute write statement."""
        from src.infra.supabase_client import get_async_session
        from sqlalchemy import text

        async with get_async_session() as session:
            await session.execute(text(statement))
            await session.commit()
            return "Statement executed successfully."

    async def _tool_fs_read(self, path: str) -> str:
        """Read file contents."""
        import asyncio
        from pathlib import Path

        def _read():
            p = Path(path)
            if not p.exists():
                return f"File not found: {path}"
            return p.read_text(encoding="utf-8")[:10_000]

        return await asyncio.to_thread(_read)

    async def _tool_fs_write(self, path: str, content: str) -> str:
        """Write to file."""
        import asyncio
        from pathlib import Path

        def _write():
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Written {len(content)} chars to {path}"

        return await asyncio.to_thread(_write)

    async def _tool_fs_list(self, path: str, pattern: str = "*") -> str:
        """List directory contents."""
        import asyncio
        from pathlib import Path

        def _list():
            p = Path(path)
            if not p.exists():
                return f"Directory not found: {path}"
            files = list(p.glob(pattern))[:50]
            return "\n".join(str(f.relative_to(p)) for f in files)

        return await asyncio.to_thread(_list)

    async def _tool_get_exchange_rate(self, pairs: str = "USD-BRL") -> str:
        """Get real-time exchange rates from AwesomeAPI (free, no key required)."""
        import httpx
        from datetime import datetime, timezone

        pairs_clean = pairs.upper().strip().replace(" ", "")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://economia.awesomeapi.com.br/json/last/{pairs_clean}",
                    headers={"User-Agent": "AgentOptimus/1.0"},
                )
                resp.raise_for_status()
                data = resp.json()

            lines = [f"💱 **Cotações em tempo real** ({datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC)\n"]
            for key, rate in data.items():
                name = rate.get("name", key)
                bid = float(rate.get("bid", 0))
                ask = float(rate.get("ask", 0))
                pct = rate.get("pctChange", "0")
                high = rate.get("high", "-")
                low = rate.get("low", "-")
                sign = "📈" if float(pct) >= 0 else "📉"
                lines.append(
                    f"**{name}**\n"
                    f"  Compra: R$ {bid:.4f} | Venda: R$ {ask:.4f}\n"
                    f"  Variação: {sign} {pct}% | Máx: {high} | Mín: {low}"
                )
            return "\n\n".join(lines)

        except httpx.HTTPStatusError as e:
            return f"❌ Par inválido '{pairs}'. Exemplos válidos: USD-BRL, EUR-BRL, BTC-BRL, GBP-BRL"
        except Exception as e:
            return f"❌ Erro ao buscar cotação: {e}"

    async def _tool_research_search(self, query: str, max_results: int = 5) -> str:
        """
        Smart web search with automatic provider routing:
        1. Brave Search API (primary) — real web results, 1000/month free
        2. DuckDuckGo Instant Answer (fallback) — free, limited to summaries
        """
        from src.core.config import settings
        import httpx

        # ── 1. Brave Search API (primary) ──────────────────────────────
        if settings.BRAVE_SEARCH_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(
                        "https://api.search.brave.com/res/v1/web/search",
                        params={
                            "q": query,
                            "count": max_results,
                            "search_lang": "pt",
                            "country": "br",
                            "safesearch": "moderate",
                            "freshness": "pw",  # past week for recency
                        },
                        headers={
                            "Accept": "application/json",
                            "Accept-Encoding": "gzip",
                            "X-Subscription-Token": settings.BRAVE_SEARCH_API_KEY,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                results = data.get("web", {}).get("results", [])
                if not results:
                    raise ValueError("No results from Brave")

                lines = [f"🔍 **Brave Search** — '{query}'\n"]
                for r in results[:max_results]:
                    title = r.get("title", "")
                    desc = r.get("description", "")[:200]
                    url_r = r.get("url", "")
                    age = r.get("age", "")
                    age_str = f" _{age}_" if age else ""
                    lines.append(f"**{title}**{age_str}")
                    lines.append(f"{desc}")
                    lines.append(f"({url_r})\n")

                return "\n".join(lines)

            except Exception as e:
                logger.warning(f"Brave search failed: {e} — falling back to DuckDuckGo")

        # ── 2. DuckDuckGo Instant Answer (free fallback) ───────────────
        try:
            async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
                    headers={"User-Agent": "AgentOptimus/1.0"},
                )
                data = resp.json()

            lines = []
            if data.get("AbstractText"):
                lines.append(f"**Resumo:** {data['AbstractText']}")
                if data.get("AbstractURL"):
                    lines.append(f"Fonte: {data['AbstractURL']}")
            for topic in data.get("RelatedTopics", [])[:3]:
                if isinstance(topic, dict) and topic.get("Text"):
                    lines.append(f"- {topic['Text'][:200]}")

            if lines:
                return "🔍 **DuckDuckGo** (resumo)\n\n" + "\n".join(lines)

            return (
                f"🔍 Busca por '{query}': nenhum resultado instantâneo disponível. "
                f"Para resultados completos, configure BRAVE_SEARCH_API_KEY no servidor."
            )
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return f"❌ Busca por '{query}' falhou: {e}"

    async def _tool_research_fetch_url(self, url: str) -> str:
        """
        Read the content of any URL as clean markdown.
        Uses Jina Reader (r.jina.ai) — free, no API key, handles JS pages.
        Falls back to raw httpx if Jina fails.
        """
        import httpx

        # ── Jina Reader (free, converts any URL to clean markdown) ─────
        jina_url = f"https://r.jina.ai/{url}"
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(
                    jina_url,
                    headers={
                        "Accept": "text/plain",
                        "User-Agent": "AgentOptimus/1.0",
                    },
                )
                if resp.status_code == 200:
                    content = resp.text.strip()
                    if content and len(content) > 100:
                        return content[:12_000]
        except Exception as e:
            logger.warning(f"Jina Reader failed for {url}: {e} — falling back to raw fetch")

        # ── Raw httpx fallback ─────────────────────────────────────────
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "AgentOptimus/1.0"},
                )
                return resp.text[:10_000]
        except Exception as e:
            return f"❌ Não foi possível acessar {url}: {e}"

    async def _tool_memory_search(self, agent_name: str, query: str) -> str:
        """Search long-term memory."""
        from src.memory.long_term import long_term_memory
        results = await long_term_memory.search_local(agent_name, query)
        return "\n---\n".join(results) if results else "Nenhum resultado encontrado."

    async def _tool_memory_learn(self, agent_name: str, category: str, learning: str) -> str:
        """Add learning to memory."""
        from src.memory.long_term import long_term_memory
        await long_term_memory.add_learning(agent_name, category, learning)
        return f"Learning adicionado para {agent_name}: {category}"

    # ── Browser Tool Handlers (FASE 2B) ──────────────────────────────────────

    async def _tool_browser_navigate(self, url: str) -> str:
        """Navigate to URL, return title + content preview."""
        from src.core.browser_service import browser_service
        try:
            result = await browser_service.navigate(url)
            return (
                f"**URL:** {result['url']}\n"
                f"**Título:** {result['title']}\n"
                f"**Status HTTP:** {result['status']}\n\n"
                f"**Conteúdo (preview):**\n{result['content_preview']}"
            )
        except ValueError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ Erro ao navegar para {url}: {e}"

    async def _tool_browser_extract(self, url: str, selector: str = "body") -> str:
        """Extract text from CSS selector on a page."""
        from src.core.browser_service import browser_service
        try:
            text = await browser_service.extract(url, selector)
            return text or f"Nenhum conteúdo encontrado com seletor '{selector}' em {url}"
        except ValueError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ Erro ao extrair de {url}: {e}"

    async def _tool_browser_search(self, url: str, query: str) -> str:
        """Search within a website and extract results."""
        from src.core.browser_service import browser_service
        try:
            text = await browser_service.search_and_extract(url, query)
            return f"**Resultados da busca por '{query}' em {url}:**\n\n{text}"
        except ValueError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ Erro ao buscar '{query}' em {url}: {e}"

    async def _tool_browser_screenshot(self, url: str) -> str:
        """Take a screenshot, returns base64 PNG."""
        from src.core.browser_service import browser_service
        try:
            b64 = await browser_service.screenshot(url)
            return f"screenshot:{b64}"
        except ValueError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ Erro ao capturar screenshot de {url}: {e}"

    async def _tool_browser_pdf(self, url: str) -> str:
        """Generate a PDF of a page, returns base64."""
        from src.core.browser_service import browser_service
        try:
            b64 = await browser_service.pdf(url)
            return f"pdf:{b64}"
        except ValueError as e:
            return f"❌ {e}"
        except Exception as e:
            return f"❌ Erro ao gerar PDF de {url}: {e}"

    # ============================================
    # Google Workspace Handlers (FASE 4)
    # ============================================

    async def _tool_gmail_read(self, query: str = "", max_results: int = 10) -> str:
        """List Gmail emails matching query."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.gmail_list(user_id, query=query, max_results=max_results)

    async def _tool_gmail_get(self, message_id: str) -> str:
        """Get full content of a Gmail message."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.gmail_get(user_id, message_id=message_id)

    async def _tool_calendar_list(self, days_ahead: int = 7) -> str:
        """List upcoming Google Calendar events."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.calendar_list(user_id, days_ahead=days_ahead)

    async def _tool_calendar_search(self, query: str) -> str:
        """Search Google Calendar events by keyword."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.calendar_search(user_id, query=query)

    async def _tool_drive_search(self, query: str, max_results: int = 10) -> str:
        """Search Google Drive files."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.drive_search(user_id, query=query, max_results=max_results)

    async def _tool_drive_read(self, file_id: str) -> str:
        """Read content of a Google Drive file."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.drive_read(user_id, file_id=file_id)

    async def _tool_gmail_send(self, to: str, subject: str, body: str, cc: str = "") -> str:
        """Send an email via Gmail (requires prior user approval)."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.gmail_send(
            user_id, to=to, subject=subject, body=body, cc=cc
        )

    async def _tool_gmail_mark_read(self, message_id: str) -> str:
        """Mark a Gmail message as read."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.gmail_mark_read(user_id, message_id=message_id)

    async def _tool_gmail_archive(self, message_id: str) -> str:
        """Archive a Gmail message."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.gmail_archive(user_id, message_id=message_id)

    async def _tool_gmail_trash(self, message_id: str) -> str:
        """Move a Gmail message to trash (requires user approval)."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.gmail_trash(user_id, message_id=message_id)

    async def _tool_gmail_add_label(self, message_id: str, label_name: str) -> str:
        """Add a label to a Gmail message."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.gmail_add_label(user_id, message_id=message_id, label_name=label_name)

    async def _tool_calendar_create_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        description: str = "",
        location: str = "",
        attendees: str = "",
        timezone: str = "America/Sao_Paulo",
    ) -> str:
        """Create a Google Calendar event (requires user approval)."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.calendar_create_event(
            user_id, title=title, start_time=start_time, end_time=end_time,
            description=description, location=location, attendees=attendees, timezone=timezone,
        )

    async def _tool_calendar_update_event(
        self,
        event_id: str,
        title: str = "",
        start_time: str = "",
        end_time: str = "",
        description: str = "",
        location: str = "",
        timezone: str = "America/Sao_Paulo",
    ) -> str:
        """Update a Google Calendar event (requires user approval)."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.calendar_update_event(
            user_id, event_id=event_id, title=title, start_time=start_time, end_time=end_time,
            description=description, location=location, timezone=timezone,
        )

    async def _tool_calendar_delete_event(self, event_id: str) -> str:
        """Delete a Google Calendar event (requires user approval)."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.calendar_delete_event(user_id, event_id=event_id)

    async def _tool_drive_upload_text(self, filename: str, content: str, folder_id: str = "") -> str:
        """Upload a text file to Google Drive (requires user approval)."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.drive_upload_text(
            user_id, filename=filename, content=content, folder_id=folder_id
        )

    async def _tool_drive_create_folder(self, folder_name: str, parent_id: str = "") -> str:
        """Create a folder in Google Drive."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.drive_create_folder(
            user_id, folder_name=folder_name, parent_id=parent_id
        )

    async def _tool_contacts_search(self, query: str, max_results: int = 10) -> str:
        """Search Google Contacts."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.contacts_search(user_id, query=query, max_results=max_results)

    async def _tool_contacts_list(self, max_results: int = 20) -> str:
        """List Google Contacts."""
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()
        return await google_oauth_service.contacts_list(user_id, max_results=max_results)

    # ============================================
    # IMAP/SMTP Email Handlers (FASE 4C)
    # ============================================

    async def _tool_email_read(self, query: str = "", account_email: str = "", max_results: int = 10) -> str:
        """Read emails from IMAP account."""
        from src.core.imap_service import imap_service
        user_id = self._current_user_id()
        return await imap_service.read_emails(
            user_id, query=query, account_email=account_email, max_results=max_results
        )

    async def _tool_email_get(self, message_id: str, account_email: str = "") -> str:
        """Get full body of an IMAP email."""
        from src.core.imap_service import imap_service
        user_id = self._current_user_id()
        return await imap_service.get_email_body(
            user_id, message_id=message_id, account_email=account_email
        )

    async def _tool_email_send(self, to: str, subject: str, body: str, from_account: str = "", cc: str = "") -> str:
        """Send email via SMTP (requires prior user approval)."""
        from src.core.imap_service import imap_service
        user_id = self._current_user_id()
        return await imap_service.send_email(
            user_id, to=to, subject=subject, body=body, from_account=from_account, cc=cc
        )

    async def _tool_email_list_accounts(self) -> str:
        """List configured IMAP accounts."""
        from src.core.imap_service import imap_service
        user_id = self._current_user_id()
        accounts = await imap_service.list_accounts(user_id)
        if not accounts:
            return (
                "📭 Nenhuma conta de email IMAP/SMTP configurada.\n"
                "Acesse /settings.html → Emails (IMAP/SMTP) para adicionar.\n"
                "⚠️ Lembre: Gmail (Google OAuth) é um sistema separado — use gmail_read para Gmail."
            )
        lines = [f"📮 **{len(accounts)} conta(s) IMAP/SMTP configurada(s):**\n"]
        for acc in accounts:
            lines.append(
                f"- **{acc['email']}** ({acc['provider']})\n"
                f"  IMAP: {acc['imap_host']}:{acc['imap_port']} | "
                f"Use: email_read com account_email=\"{acc['email']}\""
            )
        lines.append("\n⚠️ Gmail (Google OAuth) é sistema separado — use gmail_read para Gmail.")
        return "\n".join(lines)

    async def _tool_email_accounts_overview(self) -> str:
        """Return a complete map of ALL email accounts (Gmail + IMAP) with routing instructions."""
        from src.core.imap_service import imap_service
        from src.core.google_oauth_service import google_oauth_service
        user_id = self._current_user_id()

        lines = ["# 📧 MAPA COMPLETO DE CONTAS DE EMAIL\n"]

        # --- Gmail (Google OAuth) ---
        try:
            g_status = await google_oauth_service.get_connection_status(user_id)
            if g_status.get("connected") and g_status.get("google_email"):
                gmail_addr = g_status["google_email"]
                lines.append(
                    f"## 🔵 GMAIL (Google OAuth)\n"
                    f"- Conta: **{gmail_addr}**\n"
                    f"- Para ler: `gmail_read` (query='is:unread', 'from:x', etc.)\n"
                    f"- Para enviar: `gmail_send`\n"
                    f"- Outras ações: gmail_mark_read, gmail_archive, gmail_trash\n"
                )
            else:
                lines.append(
                    "## 🔵 GMAIL (Google OAuth)\n"
                    "- ❌ Não conectado. Acesse /settings.html → Google para conectar.\n"
                )
        except Exception:
            lines.append("## 🔵 GMAIL (Google OAuth)\n- ⚠️ Status indisponível.\n")

        # --- IMAP/SMTP accounts ---
        try:
            imap_accounts = await imap_service.list_accounts(user_id)
            if imap_accounts:
                lines.append(f"## 📮 IMAP/SMTP ({len(imap_accounts)} conta(s))")
                for acc in imap_accounts:
                    lines.append(
                        f"- Conta: **{acc['email']}** ({acc['provider']})\n"
                        f"  IMAP: {acc['imap_host']}:{acc['imap_port']}\n"
                        f"  Para ler: `email_read` com `account_email=\"{acc['email']}\"`\n"
                        f"  Para enviar: `email_send` com `from_account=\"{acc['email']}\"`"
                    )
            else:
                lines.append(
                    "## 📮 IMAP/SMTP\n"
                    "- ❌ Nenhuma conta configurada. Acesse /settings.html → Emails (IMAP/SMTP).\n"
                )
        except Exception:
            lines.append("## 📮 IMAP/SMTP\n- ⚠️ Status indisponível.\n")

        lines.append(
            "\n## ⚠️ REGRA DE ROTEAMENTO\n"
            "- Gmail → SEMPRE use `gmail_*` tools\n"
            "- Qualquer outro endereço → SEMPRE use `email_*` tools com `account_email=` correto\n"
            "- NUNCA misture os dois sistemas"
        )
        return "\n".join(lines)

    # ──────────────────────────────────────────
    # Apple iCloud Handlers (FASE 8)
    # ──────────────────────────────────────────

    async def _tool_apple_calendar_list(self, days_ahead: int = 7) -> str:
        from src.core.apple_service import apple_service
        return await apple_service.calendar_list(self._current_user_id(), days_ahead=days_ahead)

    async def _tool_apple_calendar_search(self, query: str) -> str:
        from src.core.apple_service import apple_service
        return await apple_service.calendar_search(self._current_user_id(), query)

    async def _tool_apple_calendar_create(
        self,
        title: str,
        start: str,
        end: str,
        notes: str = "",
        calendar_name: str = "",
    ) -> str:
        from src.core.apple_service import apple_service
        return await apple_service.calendar_create_event(
            self._current_user_id(), title, start, end, notes, calendar_name
        )

    async def _tool_apple_reminders_list(self, completed: bool = False) -> str:
        from src.core.apple_service import apple_service
        return await apple_service.reminders_list(self._current_user_id(), completed=completed)

    async def _tool_apple_reminders_create(self, title: str, due_date: str = "") -> str:
        from src.core.apple_service import apple_service
        return await apple_service.reminders_create(self._current_user_id(), title, due_date)

    async def _tool_apple_contacts_search(self, query: str) -> str:
        from src.core.apple_service import apple_service
        return await apple_service.contacts_search(self._current_user_id(), query)

    async def _tool_apple_contacts_list(self, limit: int = 20) -> str:
        from src.core.apple_service import apple_service
        return await apple_service.contacts_list(self._current_user_id(), limit=limit)

    async def _tool_speak(self, text: str) -> dict:
        """Convert text to audio via TTS and return audio_base64 for the frontend."""
        import base64
        try:
            from src.channels.voice_interface import voice_interface
            # Strip uncertainty markers before TTS (same as voice_command endpoint)
            clean_text = text.split("\n---\n")[0].strip()
            audio_bytes = await voice_interface.speak(clean_text)
            audio_b64 = base64.b64encode(audio_bytes).decode()
            return {
                "success": True,
                "_audio_base64": audio_b64,  # Picked up by react_loop to include in result
                "message": f"🔊 Áudio gerado ({len(audio_bytes)} bytes).",
            }
        except Exception as e:
            return {"success": False, "error": f"TTS falhou: {e}"}

    def _current_user_id(self) -> str:
        """Get current user_id from execution context (set by ReAct loop)."""
        return getattr(self, "_user_id", "00000000-0000-0000-0000-000000000001")


# Singleton
mcp_tools = MCPToolRegistry()
