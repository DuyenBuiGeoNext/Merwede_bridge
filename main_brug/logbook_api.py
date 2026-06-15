# logbook_api.py
# A small Flask web server that receives trigger threshold values submitted from the
# Grafana Business Forms panel and stores them in the MySQL database.
# The stored values can be read back by any Python script or displayed in Grafana.
#
# Run with:  python main_brug/logbook_api.py
# Listens on port 5050.
#
# Endpoints:
#   POST /trigger_values       - save/update trigger thresholds from Business Forms
#   GET  /trigger_values       - fetch all current trigger thresholds
#   POST /event_log            - insert a new event (threshold change, alarm, maintenance, ...)
#   GET  /event_log            - fetch last 200 events

from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import time
import threading
import pandas as pd
from datetime import datetime, timezone, timedelta
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Load database credentials from the .env file
load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow requests from Grafana (different port = cross-origin)

# Build the database connection using credentials from .env.
# pool_pre_ping: tests the connection before each use and reconnects if MySQL dropped it.
# pool_recycle:  replaces connections older than 1 hour to avoid silent timeouts.
engine = create_engine(
    f"mysql+mysqlconnector://{os.getenv('GRAFANA_DB_USER')}:{os.getenv('GRAFANA_DB_PASSWORD')}"
    f"@{os.getenv('GRAFANA_DB_HOST')}:{os.getenv('GRAFANA_DB_PORT')}/{os.getenv('GRAFANA_DB_NAME')}",
    pool_pre_ping=True,
    pool_recycle=3600,
)


def create_tables():
    # Creates all required tables if they do not exist yet.
    with engine.connect() as conn:
        # trigger_values: alert thresholds per measurement category
        #   id         (int)      - auto-incremented primary key
        #   updated_at (datetime) - UTC time when the thresholds were last changed
        #   category   (str)      - measurement group, e.g. "piles_x", "approaching_z"
        #   unit       (str)      - physical unit, e.g. "mm", "mm/s"
        #   yellow     (float)    - yellow alert threshold
        #   orange     (float)    - orange alert threshold
        #   red        (float)    - red alert threshold
        #   black      (float)    - black alert threshold
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trigger_values (
                id         INT AUTO_INCREMENT PRIMARY KEY,
                updated_at DATETIME NOT NULL,
                category   VARCHAR(100) NOT NULL,
                unit       VARCHAR(20),
                yellow     FLOAT,
                orange     FLOAT,
                red        FLOAT,
                black      FLOAT,
                UNIQUE KEY uq_category (category)
            )
        """))

        # trigger_values_pending: one row per individual value change, waiting for approval
        #   id           (int)      - auto-incremented primary key
        #   submitted_at (datetime) - auto-filled when Python receives the JSON
        #   category     (str)      - type of change: 'trigger_value' or 'conversion_key'
        #   object       (str)      - what specifically changed, e.g. 'piles_x — yellow'
        #   old_value    (float)    - the current live value before the change
        #   new_value    (float)    - the proposed new value
        #   status       (str)      - 'pending', 'approved', or 'rejected'
        #   changed_by   (str)      - name of the user who submitted the change
        #   reviewed_by  (str)      - name of the approver who acted on it (NULL until reviewed)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trigger_values_pending (
                id            INT AUTO_INCREMENT PRIMARY KEY,
                submitted_at  DATETIME NOT NULL,
                category      VARCHAR(100),
                object        VARCHAR(150),
                old_value     FLOAT,
                new_value     FLOAT,
                status        VARCHAR(20) DEFAULT 'pending',
                changed_by       VARCHAR(100),
                changed_by_email VARCHAR(150),
                reviewed_by      VARCHAR(100),
                reason           TEXT,
                reminder_sent    TINYINT(1) DEFAULT 0
            )
        """))
        # Add reminder_sent to the table if it was created before this column existed
        col_exists = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME   = 'trigger_values_pending'
              AND COLUMN_NAME  = 'reminder_sent'
        """)).scalar()
        if col_exists == 0:
            conn.execute(text(
                "ALTER TABLE trigger_values_pending ADD COLUMN reminder_sent TINYINT(1) DEFAULT 0"
            ))
        email_col = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME   = 'trigger_values_pending'
              AND COLUMN_NAME  = 'changed_by_email'
        """)).scalar()
        if email_col == 0:
            conn.execute(text(
                "ALTER TABLE trigger_values_pending ADD COLUMN changed_by_email VARCHAR(150)"
            ))

        # event_log: generic log for any notable activity in the system
        #   id          (int)      - auto-incremented primary key
        #   timestamp   (datetime) - UTC time of the event
        #   source      (str)      - who/what triggered it: user name or "system"
        #   element     (str)      - bridge element, e.g. "Pijler3", "Basculekelder"
        #   metric      (str)      - measurement involved, e.g. "delta_x", "yellow"
        #   unit        (str)      - physical unit, e.g. "mm", "mm/s"
        #   description (text)     - free-text description of the event
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS event_log (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                timestamp   DATETIME NOT NULL,
                source      VARCHAR(100),
                element     VARCHAR(100),
                metric      VARCHAR(100),
                unit        VARCHAR(20),
                description TEXT
            )
        """))

        # request_status: single-row table — tracks the current change-request state
        #   displayed in a Grafana text panel so operators can see at a glance
        #   whether a threshold change is waiting for approval
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS request_status (
                id             INT AUTO_INCREMENT PRIMARY KEY,
                status_message TEXT NOT NULL,
                updated_at     DATETIME NOT NULL
            )
        """))
        count = conn.execute(text("SELECT COUNT(*) FROM request_status")).scalar()
        if count == 0:
            conn.execute(text("""
                INSERT INTO request_status (status_message, updated_at)
                VALUES ('No change requested', :now)
            """), {"now": datetime.now(timezone.utc)})

        conn.commit()


def to_py(val):
    # Converts numpy scalar types to native Python float/None.
    # MySQL connector cannot handle numpy.int64 or numpy.float64 directly.
    if pd.isna(val):
        return None
    return float(val)


def _update_request_status(conn, message):
    conn.execute(text("""
        UPDATE request_status SET status_message = :msg, updated_at = :now WHERE id = 1
    """), {"msg": message, "now": datetime.now(timezone.utc)})


def _check_and_send_reminders(conn):
    # Sends a reminder email for pending rows that have been waiting 24+ hours
    # but have not yet expired (< 48 h) and have not yet received a reminder.
    now         = datetime.now(timezone.utc)
    cutoff_24h  = now - timedelta(hours=24)
    cutoff_48h  = now - timedelta(hours=48)

    result = conn.execute(text("""
        SELECT * FROM trigger_values_pending
        WHERE status        = 'pending'
          AND reminder_sent = 0
          AND submitted_at <= :cutoff_24h
          AND submitted_at  > :cutoff_48h
    """), {"cutoff_24h": cutoff_24h, "cutoff_48h": cutoff_48h})
    rows = [dict(row._mapping) for row in result]

    if not rows:
        return

    print(f"Sending reminder email for {len(rows)} pending row(s) older than 24 hours.")
    change_summary = [
        f"{r['object']}: {r['old_value']} → {r['new_value']}  (submitted by {r['changed_by']} at {r['submitted_at']})"
        for r in rows
    ]
    send_reminder_email(rows[0]["changed_by"], change_summary)

    # Mark reminder as sent so we don't email again for the same rows
    id_list = ", ".join(str(r["id"]) for r in rows)
    conn.execute(text(
        f"UPDATE trigger_values_pending SET reminder_sent = 1 WHERE id IN ({id_list})"
    ))


def _expire_pending_requests(conn):
    # Marks any pending rows older than 48 hours as 'expired', resets the status table,
    # and notifies the requester by email.
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    result = conn.execute(text("""
        SELECT * FROM trigger_values_pending
        WHERE status = 'pending' AND submitted_at < :cutoff
    """), {"cutoff": cutoff})
    rows = [dict(r._mapping) for r in result]

    if not rows:
        return

    id_list = ", ".join(str(r["id"]) for r in rows)
    conn.execute(text(
        f"UPDATE trigger_values_pending SET status = 'expired' WHERE id IN ({id_list})"
    ))
    _update_request_status(conn, "No change requested")
    print(f"Expired {len(rows)} pending request(s) older than 48 hours.")

    change_summary = [f"{r['object']}: {r['old_value']} → {r['new_value']}" for r in rows]
    send_requester_notification(
        rows[0].get("changed_by_email") or "",
        rows[0].get("changed_by") or "unknown",
        "expired",
        change_summary,
    )


def send_reminder_email(changed_by, change_summary):
    # Sends a 24-hour reminder to approvers for pending changes not yet reviewed.
    smtp_host   = (os.getenv("SMTP_HOST") or "").strip()
    smtp_port   = int((os.getenv("SMTP_PORT") or "587").strip())
    smtp_user   = (os.getenv("SMTP_USER") or "").strip()
    smtp_pass   = (os.getenv("SMTP_PASSWORD") or "").strip()
    grafana_url = (os.getenv("GRAFANA_URL") or "your Grafana dashboard").strip()
    recipients  = [e.strip() for e in os.getenv("APPROVER_EMAILS", "").split(",") if e.strip()]

    if not recipients:
        print("No approver emails configured — skipping reminder email.")
        return

    change_lines = "\n".join(f"  - {line}" for line in change_summary)
    body = f"""\
Dear approver,

This is a reminder that the following threshold change request submitted by {changed_by}
has been waiting for approval for more than 24 hours and has not yet been reviewed:

{change_lines}

WARNING: If no action is taken, this request will expire within the next 24 hours.
Please review them by visiting the Grafana dashboard:

  {grafana_url}

This is an automated message from the Merwede Bridge monitoring system.
"""

    msg = MIMEMultipart()
    msg["From"]    = smtp_user
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = f"[Merwedebrug] REMINDER: Threshold change approval still pending — submitted by {changed_by}"
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipients, msg.as_string())
        print(f"Reminder email sent to: {recipients}")
    except Exception as e:
        print(f"Failed to send reminder email: {e}")


def send_approval_email(changed_by, change_summary):
    # Sends an email to all approvers listed in APPROVER_EMAILS.
    # change_summary is a list of strings describing each changed value.
    smtp_host    = (os.getenv("SMTP_HOST") or "").strip()
    smtp_port    = int((os.getenv("SMTP_PORT") or "587").strip())
    smtp_user    = (os.getenv("SMTP_USER") or "").strip()
    smtp_pass    = (os.getenv("SMTP_PASSWORD") or "").strip()
    grafana_url  = (os.getenv("GRAFANA_URL") or "your Grafana dashboard").strip()
    recipients   = [e.strip() for e in os.getenv("APPROVER_EMAILS", "").split(",") if e.strip()]

    if not recipients:
        print("No approver emails configured — skipping email.")
        return

    # Build email body
    change_lines = "\n".join(f"  - {line}" for line in change_summary)
    body = f"""\
Dear approver,

There are changes in the trigger values / thresholds submitted by {changed_by}.

The following values have been changed:

{change_lines}

These changes are currently PENDING and have not been applied yet.
Please review and give your approval by visiting the Grafana dashboard:

  {grafana_url}

If you approve, the new thresholds will be applied to the system.
If you reject, the current thresholds will remain unchanged.

Note: If no action is taken, this request will automatically expire after 48 hours.

This is an automated message from the Merwede Bridge monitoring system.
"""

    msg = MIMEMultipart()
    msg["From"]    = smtp_user
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = f"[Merwedebrug] Threshold change approval requested — submitted by {changed_by}"
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, recipients, msg.as_string())
        print(f"Approval email sent to: {recipients}")
    except Exception as e:
        print(f"Failed to send approval email: {e}")


def send_requester_notification(to_email, changed_by, action, change_summary, reason=""):
    # Emails the person who submitted the change request to inform them of the outcome.
    # action is one of: 'approved', 'rejected', 'expired'
    # If no requester email is stored, falls back to SMTP_USER (the configured sender account).
    smtp_host = (os.getenv("SMTP_HOST") or "").strip()
    smtp_port = int((os.getenv("SMTP_PORT") or "587").strip())
    smtp_user = (os.getenv("SMTP_USER") or "").strip()
    smtp_pass = (os.getenv("SMTP_PASSWORD") or "").strip()

    to_email = (to_email or "").strip() or smtp_user  # fall back to SMTP_USER when empty

    print(f"[notify] action={action}, to='{to_email}', changed_by='{changed_by}'")

    if not smtp_host or not smtp_user or not smtp_pass:
        print(f"[notify] SKIPPED — SMTP not configured in .env "
              f"(SMTP_HOST='{smtp_host}', SMTP_USER='{smtp_user}', SMTP_PASSWORD={'set' if smtp_pass else 'MISSING'})")
        return

    print(f"[notify] Connecting to {smtp_host}:{smtp_port} as {smtp_user} ...")

    outcomes = {
        "approved": "Your threshold change request has been APPROVED. The new values are now active.",
        "rejected": "Your threshold change request has been REJECTED. No changes have been applied.",
        "expired":  "Your threshold change request has EXPIRED after 48 hours with no action taken. No changes have been applied.",
    }
    outcome_message = outcomes.get(action, f"Your threshold change request status: {action}.")
    change_lines = "\n".join(f"  - {line}" for line in change_summary)
    reason_line  = f"\nReason given: {reason}" if reason else ""

    body = f"""\
Dear {changed_by},

{outcome_message}

The following changes were requested:

{change_lines}{reason_line}

This is an automated message from the Merwede Bridge monitoring system.
"""

    msg = MIMEMultipart()
    msg["From"]    = smtp_user
    msg["To"]      = to_email
    msg["Subject"] = f"[Merwedebrug] Your threshold change request has been {action} — {changed_by}"
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_email], msg.as_string())
        print(f"[notify] Email sent to {to_email}")
    except Exception as e:
        print(f"[notify] SMTP error: {e}")


@app.route("/trigger_values", methods=["POST"])
def save_trigger_values():
    # Receives a JSON POST from the Grafana Business Forms panel.
    # All 5 categories are submitted in one request using flat named keys.
    # Expected JSON body (set the field Id in Business Forms to match these keys):
    #   {
    #       "changed_by":            str   - name of the user making the change
    #       "piles_x_yellow":        float,  "piles_x_orange":        float,
    #       "piles_x_red":           float,  "piles_x_black":         float,
    #       "piles_y_yellow":        float,  "piles_y_orange":        float,
    #       "piles_y_red":           float,  "piles_y_black":         float,
    #       "approaching_z_yellow":  float,  "approaching_z_orange":  float,
    #       "approaching_z_red":     float,  "approaching_z_black":   float,
    #       "approaching_uy_rx_yellow": float, ...
    #       "approaching_duz_ry_yellow": float, ...
    #   }
    # Each category is upserted as its own row in trigger_values.
    # Changes are detected by comparing a fleeting DataFrame (incoming JSON)
    # against the current DB DataFrame, then written to event_log.
    CATEGORIES = [
        ("piles_x",            "mm"),
        ("piles_y",            "mm"),
        ("approaching_z",      "mm"),
        ("approaching_uy_rx",  "mm"),
        ("approaching_duz_ry", "mm"),
    ]
    LEVELS = ["yellow", "orange", "red", "black"]

    data = request.get_json()
    print(f"Trigger values received: {data}")
    now              = datetime.now(timezone.utc)
    changed_by       = data.get("changed_by", "unknown")
    changed_by_email = data.get("changed_by_email", "")

    with engine.connect() as conn:
        # Expire rows older than 48 h and send reminder for rows older than 24 h
        _expire_pending_requests(conn)
        _check_and_send_reminders(conn)

        # Reject if a pending request already exists
        pending_count = conn.execute(text(
            "SELECT COUNT(*) FROM trigger_values_pending WHERE status = 'pending'"
        )).scalar()
        if pending_count > 0:
            _update_request_status(conn, "Not possible to request another change, one change requested in pending")
            conn.commit()
            print("Change request rejected — a pending request already exists.")
            return jsonify({
                "status":  "rejected",
                "message": "Not possible to request another change, one change requested in pending.",
            }), 409

        # Step 1 — build fleeting DataFrame from the incoming JSON
        #   One row per category, columns: category, unit, yellow, orange, red, black
        df_incoming = pd.DataFrame([
            {
                "category": category,
                "unit":     unit,
                "yellow":   data.get(f"{category}_yellow"),
                "orange":   data.get(f"{category}_orange"),
                "red":      data.get(f"{category}_red"),
                "black":    data.get(f"{category}_black"),
            }
            for category, unit in CATEGORIES
        ]).set_index("category")
        print("Incoming (fleeting) table:")
        print(df_incoming)

        # Step 2 — read current DB values into a DataFrame for comparison
        result = conn.execute(text(
            "SELECT category, unit, yellow, orange, red, black FROM trigger_values"
        ))
        rows = [dict(row._mapping) for row in result]
        df_current = pd.DataFrame(rows).set_index("category") if rows else pd.DataFrame(
            columns=["unit"] + LEVELS
        )
        print("Current DB table:")
        print(df_current)

        # Step 3 — compare: align both DataFrames on category index, find changed cells
        df_current_aligned = df_current.reindex(df_incoming.index)
        diff_mask = df_incoming[LEVELS].ne(df_current_aligned[LEVELS])
        changed_categories = diff_mask.any(axis=1)
        print(f"Categories with changes: {list(changed_categories[changed_categories].index)}")

        # Step 4 — if no changes at all, return early
        if not changed_categories.any():
            print("No changes detected — nothing to do.")
            return jsonify({"status": "no_change", "message": "No values were changed."})

        # Step 5 — insert one row per individual changed value into trigger_values_pending
        change_summary = []
        for category in changed_categories[changed_categories].index:
            unit = df_incoming.loc[category, "unit"]
            for level in LEVELS:
                if diff_mask.loc[category, level]:
                    old_val = df_current_aligned.loc[category, level]
                    new_val = df_incoming.loc[category, level]
                    obj     = f"{category} — {level}"
                    conn.execute(text("""
                        INSERT INTO trigger_values_pending
                            (submitted_at, category, object, old_value, new_value, status, changed_by, changed_by_email)
                        VALUES
                            (:submitted_at, :category, :object, :old_value, :new_value, 'pending', :changed_by, :changed_by_email)
                    """), {
                        "submitted_at":    now,
                        "category":        "trigger_value",
                        "object":          obj,
                        "old_value":       to_py(old_val),
                        "new_value":       to_py(new_val),
                        "changed_by":      changed_by,
                        "changed_by_email": changed_by_email,
                    })
                    summary_line = f"{obj}: {old_val} → {new_val} {unit}"
                    change_summary.append(summary_line)
                    print(f"Pending change saved: {summary_line}")

        _update_request_status(conn, "Change requested in pending")
        conn.commit()

    # Step 6 — send approval email to configured approvers
    send_approval_email(changed_by, change_summary)

    return jsonify({
        "status":  "pending",
        "message": "Changes submitted for approval. Approvers have been notified by email.",
        "changes": change_summary,
    })


@app.route("/event_log", methods=["POST"])
def add_event():
    # Receives a JSON POST and inserts one event into event_log.
    # Expected JSON body:
    #   {
    #       "source":      str  - who/what triggered it, e.g. "John" or "system"
    #       "element":     str  - bridge element, e.g. "Pijler3"
    #       "metric":      str  - measurement involved, e.g. "delta_x"
    #       "unit":        str  - physical unit, e.g. "mm" (optional)
    #       "description": str  - free-text description of the event
    #   }
    data = request.get_json()
    print(f"Event log received: {data}")
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO event_log (timestamp, source, element, metric, unit, description)
            VALUES (:timestamp, :source, :element, :metric, :unit, :description)
        """), {
            "timestamp":   datetime.now(timezone.utc),
            "source":      data.get("source"),
            "element":     data.get("element"),
            "metric":      data.get("metric"),
            "unit":        data.get("unit", ""),
            "description": data.get("description"),
        })
        conn.commit()
    return jsonify({"status": "ok"})


@app.route("/event_log", methods=["GET"])
def get_events():
    # Returns the 200 most recent event log entries as a JSON array.
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT * FROM event_log ORDER BY timestamp DESC LIMIT 200"
        ))
        rows = [dict(row._mapping) for row in result]
    return jsonify(rows)


@app.route("/trigger_values", methods=["GET"])
def get_trigger_values():
    # Returns all current trigger thresholds as a JSON array, one object per category.
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT * FROM trigger_values ORDER BY category"
        ))
        rows = [dict(row._mapping) for row in result]
    return jsonify(rows)


@app.route("/request_status", methods=["GET"])
def get_request_status():
    # Returns the current change-request status message for display in a Grafana text panel.
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT status_message, updated_at FROM request_status WHERE id = 1"
        ))
        row = result.fetchone()
    if row:
        return jsonify({"status_message": row[0], "updated_at": str(row[1])})
    return jsonify({"status_message": "No change requested"})


@app.route("/review", methods=["POST"])
def review_pending():
    # Receives the approval/rejection from the Grafana Business Forms panel.
    # Processes ALL rows in trigger_values_pending with status = 'pending'.
    # Expected JSON body:
    #   {
    #       "reviewed_by": str - auto-filled from Grafana logged-in user
    #       "action":      str - "approve/approval" or "reject/rejection"
    #       "reason":      str - optional explanation
    #   }
    data        = request.get_json()
    print(f"Raw JSON received at /review: {data}")

    reviewed_by = data.get("reviewed_by", "unknown")
    action      = str(data.get("action", "")).strip().lower()
    reason      = data.get("reason", "")

    print(f"Review received — reviewed_by: {reviewed_by}, action: {action}, reason: {reason}")

    if action.startswith("approv"):
        status = "approved"
    elif action.startswith("reject"):
        status = "rejected"
    else:
        print(f"Invalid action '{action}'")
        return jsonify({"status": "error", "message": "Action must be approve/approval or reject/rejection"}), 400

    print(f"Action resolved to: {status}")
    now          = datetime.now(timezone.utc)
    VALID_LEVELS = {"yellow", "orange", "red", "black"}

    with engine.connect() as conn:
        # Fetch ALL pending rows
        result = conn.execute(text(
            "SELECT * FROM trigger_values_pending WHERE status = 'pending'"
        ))
        pending_rows = [dict(row._mapping) for row in result]

        if not pending_rows:
            print("No pending rows found.")
            return jsonify({"status": "no_change", "message": "No pending changes found."}), 404

        print(f"Found {len(pending_rows)} pending row(s) to process.")

        for pending in pending_rows:
            # If approved — apply new value to trigger_values
            if status == "approved":
                parts = pending["object"].split(" — ")  # "piles_x — yellow"
                if len(parts) == 2:
                    category, level = parts[0].strip(), parts[1].strip()
                    if level in VALID_LEVELS:
                        conn.execute(text(f"""
                            UPDATE trigger_values
                            SET `{level}` = :new_value, updated_at = :updated_at
                            WHERE category = :category
                        """), {
                            "new_value":  pending["new_value"],
                            "updated_at": now,
                            "category":   category,
                        })
                        print(f"Applied to production: {category} {level} = {pending['new_value']}")

            # Update pending row status to approved or rejected
            conn.execute(text("""
                UPDATE trigger_values_pending
                SET status = :status, reviewed_by = :reviewed_by, reason = :reason
                WHERE id = :id
            """), {
                "status":      status,
                "reviewed_by": reviewed_by,
                "reason":      reason,
                "id":          pending["id"],
            })

            # Only log approved changes to event_log
            if status == "approved":
                description = (
                    f"'{pending['object']}' changed from {pending['old_value']} to {pending['new_value']}. "
                    f"Approved by {reviewed_by}. "
                    f"Reason: {reason or 'none'}."
                )
                conn.execute(text("""
                    INSERT INTO event_log (timestamp, source, element, metric, unit, description)
                    VALUES (:timestamp, :source, :element, :metric, :unit, :description)
                """), {
                    "timestamp":   now,
                    "source":      reviewed_by,
                    "element":     pending["object"],
                    "metric":      "trigger_values",
                    "unit":        "",
                    "description": description,
                })

            print(f"Row id={pending['id']} → {status}")

        _update_request_status(conn, "No change requested")
        conn.commit()
        print(f"All pending rows processed → {status} by {reviewed_by}")

    change_summary = [f"{p['object']}: {p['old_value']} → {p['new_value']}" for p in pending_rows]
    send_requester_notification(
        pending_rows[0].get("changed_by_email") or "",
        pending_rows[0].get("changed_by") or "unknown",
        status,
        change_summary,
        reason,
    )

    return jsonify({"status": "ok", "message": f"{len(pending_rows)} change(s) {status} by {reviewed_by}."})


def _background_check_loop():
    # Runs every hour in a daemon thread: sends 24 h reminders and expires 48 h requests.
    while True:
        time.sleep(3600)
        try:
            with engine.connect() as conn:
                _expire_pending_requests(conn)
                _check_and_send_reminders(conn)
                conn.commit()
        except Exception as e:
            print(f"Background check error: {e}")


if __name__ == "__main__":
    create_tables()
    threading.Thread(target=_background_check_loop, daemon=True).start()
    print("Logbook API running on port 5050")
    app.run(host="0.0.0.0", port=5050)
