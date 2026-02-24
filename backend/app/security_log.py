import logging
from datetime import datetime

security_logger = logging.getLogger("homematrix.security")
security_logger.setLevel(logging.INFO)

handler = logging.FileHandler("/var/log/homematrix_security.log")
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
security_logger.addHandler(handler)

def log_login_ok(email: str, ip: str):
    security_logger.info(f"LOGIN_OK email={email} ip={ip}")

def log_login_fail(email: str, ip: str):
    security_logger.warning(f"LOGIN_FAIL email={email} ip={ip}")

def log_register(email: str, ip: str):
    security_logger.info(f"REGISTER email={email} ip={ip}")

def log_admin_action(admin_email: str, action: str, target: str):
    security_logger.info(f"ADMIN_ACTION admin={admin_email} action={action} target={target}")

def log_password_change(email: str, ip: str):
    security_logger.info(f"PASSWORD_CHANGE email={email} ip={ip}")
