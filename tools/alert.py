#!/usr/bin/env python3
"""Email the owner when a scheduled run goes wrong. Silent on normal days.

  alert.py check premarket|postclose LOGFILE EXITCODE   run after each Mac job; emails only on a problem
  alert.py send "SUBJECT" "BODY"                        alert now (Mac pop-up; email if the keychain entry exists)

Problems it catches: the claude run failed or its login expired, git pull/push failed, or the
run itself wrote an ALERT line to logs/alert-YYYY-MM-DD.txt (circuit breaker, a stop hit, an order that failed).
Missing reports and missed runs are not alerted. A Mac that is off
or asleep runs nothing, including this.

Mail goes out through Gmail SMTP. The sender address and its Gmail app password live in the
macOS keychain under the service name "trading-alert", added by the owner:
  security add-generic-password -s trading-alert -a YOUR_GMAIL_ADDRESS -w
If that entry is missing, it falls back to a macOS notification.
"""
import datetime, json, os, re, smtplib, subprocess, sys
from email.message import EmailMessage

TO = os.environ.get("TRADING_ALERT_TO")  # recipient address
SERVICE = "trading-alert"
HOME = os.path.expanduser("~/trading")

def creds():
    try:
        meta = subprocess.run(["security", "find-generic-password", "-s", SERVICE],
                              capture_output=True, text=True, check=True).stdout
        pw = subprocess.run(["security", "find-generic-password", "-s", SERVICE, "-w"],
                            capture_output=True, text=True, check=True).stdout.strip()
        acct = re.search(r'"acct"<blob>="([^"]+)"', meta).group(1)
        return acct, pw
    except Exception:
        return None

def send(subject, body):
    c = creds()
    if not c or not TO:
        q = lambda x: json.dumps(x, ensure_ascii=False)  # AppleScript strings use the same double-quote escaping
        subprocess.run(["osascript", "-e", f'display notification {q(body[:200])} with title {q("Trading: " + subject)} sound name "Basso"'])
        # A window that stays until clicked. Own session, so the job can exit (and launchd can't kill it) while it waits.
        subprocess.Popen(["osascript", "-e", "activate", "-e", f'display alert {q("Trading: " + subject)} message {q(body[:1500])} giving up after 86400'],
                         start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"no keychain entry '{SERVICE}': showed a notification instead")
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = c[0], TO, f"[Trading] {subject}"
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
        s.login(*c)
        s.send_message(msg)
    print(f"emailed {TO}: {subject}")

def check(kind, logfile, rc):
    today = datetime.date.today()
    log = open(logfile).read() if os.path.exists(logfile) else ""
    problems = []
    if re.search(r"Failed to authenticate|OAuth|session expired|Invalid API key|Please run /login", log):
        problems.append("Claude's login expired, so the run did nothing. Fix: open Claude Code and run /login.")
    elif rc != 0:
        problems.append(f"The claude run exited with code {rc}.")
    if "git pull failed" in log:
        problems.append("git pull failed, so the run may have used a stale research brief.")
    if "git push failed" in log:
        problems.append("git push failed, so the cloud research run won't see today's trades.")
    flag = os.path.join(HOME, "logs", f"alert-{today}.txt")
    if os.path.exists(flag):
        problems.append("The run flagged:\n" + open(flag).read().strip())
        os.rename(flag, flag.replace(".txt", f"-sent-{kind}.txt"))
    if problems:
        tail = "\n".join(log.strip().splitlines()[-15:])
        send(f"{kind} run needs attention ({today})",
             "\n\n".join(problems) + f"\n\nLast lines of {logfile}:\n{tail}")
    else:
        print("no problems; no email")

if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 4 and a[0] == "check" and a[1] in ("premarket", "postclose"):
        check(a[1], a[2], int(a[3]))
    elif len(a) == 3 and a[0] == "send":
        send(a[1], a[2])
    else:
        sys.exit(__doc__)
