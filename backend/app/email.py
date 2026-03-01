import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

def send_email(to_email: str, subject: str, html: str):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = "HomeMatrix <seriole47@gmail.com>"
        msg["To"] = to_email
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")

def send_welcome_email(to_email: str):
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;background:#111318;color:#e8eaf0;padding:32px;border-radius:12px">
      <h2 style="color:#00e5c0;margin-bottom:8px">Benvenuto su HomeMatrix 🏠</h2>
      <p>Il tuo account è stato <strong>approvato</strong>.</p>
      <p>Puoi ora accedere all'applicazione con le tue credenziali.</p>
      <a href="https://homematrix.iotzator.com" 
         style="display:inline-block;margin-top:16px;padding:12px 24px;background:#00e5c0;color:#0a0c10;border-radius:8px;text-decoration:none;font-weight:700">
        Accedi a HomeMatrix
      </a>
      <p style="color:#5a5f72;font-size:12px;margin-top:24px">Se non hai richiesto questo account, ignora questa email.</p>
    </div>
    """
    send_email(to_email, "Account approvato - HomeMatrix", html)
