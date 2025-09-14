# feedback.py
import os
import smtplib
import ssl
import mimetypes
from email.message import EmailMessage
from typing import Callable, Optional
from datetime import datetime

import streamlit as st

# ===============================
# Configurazione SMTP
# ===============================
# Consigliato: usa st.secrets
# In .streamlit/secrets.toml metti:
# [smtp]
# host = "smtp.example.com"
# port = 587              # 465 (SSL) o 587 (STARTTLS)
# username = "apikey_o_user"
# password = "supersecret"
# from_email = "noreply@tuodominio.com"
# to_email = "developer@tuodominio.com"


def _smtp_cfg():
    """
    Reads the config from st.secrets, with fallback to environment variables.

    Returns:
        dict: The SMTP configuration
    ------
    Note:
    """
    if "smtp" in st.secrets:
        s = st.secrets["smtp"]
        return {
            "host": s.get("host"),
            "port": int(s.get("port", 587)),
            "username": s.get("username"),
            "password": s.get("password"),
            "from_email": s.get("from_email"),
            "to_email": s.get("to_email"),
        }
    # Fallback ENV
    return {
        "host": os.getenv("SMTP_HOST"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME"),
        "password": os.getenv("SMTP_PASSWORD"),
        "from_email": os.getenv("SMTP_FROM_EMAIL"),
        "to_email": os.getenv("SMTP_TO_EMAIL"),
    }


# ===============================
# Funzione invio email
# ===============================
def send_feedback_email(
    name: str,
    email: str,
    category: str,
    subject: str,
    message: str,
    file_bytes: Optional[bytes],
    file_name: Optional[str],
) -> bool:
    """
    Sends an email to the developer with the form data and (optionally) an attachment.

    Args:
        name (str): The name of the sender
        email (str): The email of the sender
        category (str): The category of the feedback
        subject (str): The subject of the email
        message (str): The message content
        file_bytes (Optional[bytes]): The file bytes for attachment
        file_name (Optional[str]): The file name for attachment

    Returns:
        bool: True if the sending is successful, False otherwise
    ------
    Note:
    """
    cfg = _smtp_cfg()
    mandatory = ["host", "port", "username", "password", "from_email", "to_email"]
    if not all(cfg.get(k) for k in mandatory):
        st.error(
            "SMTP config mancante. Controlla st.secrets['smtp'] o le variabili ambiente."
        )
        return False

    # Corpo email (testo semplice)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plain_body = (
        f"New feedback from your app\n"
        f"--------------------------\n"
        f"Date: {now}\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Category: {category}\n"
        f"Subject: {subject}\n\n"
        f"Message:\n{message}\n"
    )

    # Prepara il messaggio
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from_email"]
    msg["To"] = cfg["to_email"]
    # Imposta Reply-To sull'email dell’utente per rispondere facilmente
    if email:
        msg["Reply-To"] = email

    msg.set_content(plain_body)

    # Allegato (se presente)
    if file_bytes and file_name:
        maintype, subtype = ("application", "octet-stream")
        guessed, _ = mimetypes.guess_type(file_name)
        if guessed:
            mt, _, stype = guessed.partition("/")
            if mt and stype:
                maintype, subtype = mt, stype
        msg.add_attachment(
            file_bytes, maintype=maintype, subtype=subtype, filename=file_name
        )

    # Invio
    try:
        port = int(cfg["port"])
        if port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(cfg["host"], port, context=context) as server:
                server.login(cfg["username"], cfg["password"])
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg["host"], port) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.login(cfg["username"], cfg["password"])
                server.send_message(msg)
        return True
    except Exception as e:
        # Log minimale; in produzione usa un logger
        print("Error sending feedback email:", repr(e))
        return False


# ===============================
# UI del form (modal o inline)
# ===============================
def feedback_form_ui(
    send_fn: Callable[[str, str, str, str, str, Optional[bytes], Optional[str]], bool],
) -> None:
    """
    Render of the feedback form; calls send_fn on send.

    Args:
        send_fn (Callable): The function to send the feedback

    Returns:
        None
    ------
    Note:
    """
    st.markdown(
        """
        <style>
            .fb-row {display: grid; gap: 12px;}
            @media (min-width: 768px){
              .fb-row {grid-template-columns: 1fr 1fr;}
            }
            .fb-badge{
              display:inline-flex;align-items:center;gap:.5rem;
              background:rgba(125,125,255,.08);border:1px solid rgba(125,125,255,.25);
              padding:.35rem .6rem;border-radius:999px;font-size:.85rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # st.markdown('<span class="fb-badge">💡 Your ideas power this app</span>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="fb-row">', unsafe_allow_html=True)
        a, b = st.columns(2)
        name = a.text_input("Your name", placeholder="e.g. Alex Bianchi")
        email = b.text_input("Email", placeholder="e.g. alex@example.com")
        st.markdown("</div>", unsafe_allow_html=True)
    c, d = st.columns(2)
    category = c.selectbox(
        "Category",
        [
            "Feature request",
            "Bug report",
            "UX/Design",
            "Performance",
            "Docs/Content",
            "Other",
        ],
        index=0,
    )

    subject = d.text_input("Subject", placeholder="Short and sweet…")

    max_chars = 2000
    message = st.text_area(
        "Message",
        height=160,
        placeholder="Tell me what's working great, what’s not, or what you’d love to see next…",
    )
    st.caption(f"{len(message)}/{max_chars} characters")

    file = st.file_uploader("Optional attachment (screenshot, log, etc.)", type=None)
    file_bytes = file.getvalue() if file is not None else None
    file_name = file.name if file is not None else None

    cols = st.columns([1, 1, 1.3])
    with cols[0]:
        allow_contact = st.toggle("Can I reply to you?", value=True)
    with cols[1]:
        urgent = st.toggle("Mark as urgent", value=False)
    with cols[2]:
        valid = (
            len(message.strip()) > 4
            # and len(subject.strip()) > 2
            and ("@" in email and "." in email)
            and len(name.strip()) > 1
            and len(message) <= max_chars
        )
        send_label = "🚀 Send feedback" + (" (urgent)" if urgent else "")
        sent = st.button(send_label, type="primary", disabled=not valid)

    if sent:
        final_subject = ("[URGENT] " if urgent else "") + "PVAPP: " + subject.strip()
        # Nota: allow_contact è gestito via Reply-To (vedi send_feedback_email).
        ok = send_fn(
            name.strip(),
            email.strip(),
            category,
            final_subject,
            message.strip(),
            file_bytes,
            file_name,
        )
        if ok:
            st.toast("Thanks! Your message was sent ✅", icon="🎉")
            st.session_state.pop("show_feedback", None)
            st.rerun()
        else:
            st.error(
                "Oops, something went wrong while sending. Please check SMTP config and try again."
            )


def write_to_developer(
    send_fn: Callable[
        [str, str, str, str, str, Optional[bytes], Optional[str]], bool
    ] = send_feedback_email,
) -> None:
    """
    Adds a button that opens the form (modal if available).

    Args:
        send_fn (Callable): The function to send the feedback

    Returns:
        None
    ------
    Note:
    """
    if "show_feedback" not in st.session_state:
        st.session_state.show_feedback = False

    if st.button("✍️ Write to developer", type="secondary"):
        # st.session_state.show_feedback = True
        st.error("The feedback form is not included in this distribution. Please, contact pepa.lorenzo.01@gmail.com")
        

    if hasattr(st, "dialog"):

        @st.dialog("Write to developer")
        def _open_dialog():
            feedback_form_ui(send_fn)

        if st.session_state.show_feedback:
            _open_dialog()
    else:
        if st.session_state.show_feedback:
            with st.container(border=True):
                st.subheader("Write to developer", anchor=False)
                feedback_form_ui(send_fn)
