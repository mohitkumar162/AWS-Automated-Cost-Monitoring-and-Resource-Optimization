## Complete Lambda Source Code
  
```python
import json
import logging
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Safety switch: keep True while testing.
DRY_RUN = True

DEFAULT_BUDGET_USD = 10.0


def extract_notification(event):
    """Extract JSON or plain-text notifications from SNS or test events."""
    records = event.get("Records", [])

    if records and records[0].get("Sns"):
        message = records[0]["Sns"].get("Message", "")
        try:
            return json.loads(message)
        except (json.JSONDecodeError, TypeError):
            return {"message": str(message)}

    return event


def parse_amount(text, label):
    """Extract a dollar amount following a text label."""
    pattern = rf"{label}\s*:\s*\$?\s*([0-9]+(?:\.[0-9]+)?)"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return float(match.group(1))

    return None


def parse_percentage(text, label):
    """Extract a percentage following a text label."""
    pattern = rf"{label}\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*%?"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return float(match.group(1))

    return None


def lambda_handler(event, context):
    logger.info("Cost optimizer invoked.")
    logger.info("Dry-run mode: %s", DRY_RUN)

    notification = extract_notification(event)

    logger.info(
        "Received notification: %s",
        json.dumps(notification, default=str)
    )

    budget_amount = DEFAULT_BUDGET_USD
    actual_cost = None
    threshold_percent = None

    # Support JSON test events.
    if "budget_amount_usd" in notification:
        budget_amount = float(notification["budget_amount_usd"])

    actual_cost = notification.get("actual_cost_usd")
    threshold_percent = notification.get("threshold_percent")

    # Support common AWS Budgets JSON notification fields.
    if actual_cost is None:
        actual_spend = notification.get("actualSpend")
        if isinstance(actual_spend, dict):
            actual_cost = actual_spend.get("amount")

    if threshold_percent is None:
        threshold_percent = notification.get("threshold")

    # Support plain-text SNS notifications.
    message = notification.get("message", "")

    if isinstance(message, str) and message:
        parsed_budget = parse_amount(message, "Budgeted Amount")
        parsed_cost = parse_amount(message, "Actual Cost")
        parsed_threshold = parse_percentage(message, "Alert Threshold")

        if parsed_budget is not None:
            budget_amount = parsed_budget

        if actual_cost is None:
            actual_cost = parsed_cost

        if threshold_percent is None:
            threshold_percent = parsed_threshold

    # Do not evaluate if required information is missing.
    if actual_cost is None or threshold_percent is None:
        result = {
            "status": "received",
            "mode": "dry-run",
            "action_taken": False,
            "message": (
                "Notification received, but cost or threshold data "
                "was not recognized. No action recommended."
            )
        }
        logger.warning("Insufficient data for threshold evaluation.")
        logger.info("Result: %s", json.dumps(result))
        return result

    try:
        budget_amount = float(budget_amount)
        actual_cost = float(actual_cost)
        threshold_percent = float(threshold_percent)
    except (TypeError, ValueError):
        result = {
            "status": "error",
            "mode": "dry-run",
            "action_taken": False,
            "message": "Cost or threshold values were invalid."
        }
        logger.warning("Invalid cost or threshold values.")
        logger.info("Result: %s", json.dumps(result))
        return result

    if budget_amount <= 0 or not 0 <= threshold_percent <= 100:
        result = {
            "status": "error",
            "mode": "dry-run",
            "action_taken": False,
            "message": "Budget amount or threshold is out of range."
        }
        logger.warning("Budget amount or threshold out of range.")
        logger.info("Result: %s", json.dumps(result))
        return result

    threshold_amount = budget_amount * threshold_percent / 100
    threshold_reached = actual_cost >= threshold_amount

    if threshold_reached:
        recommendation = (
            "Budget threshold reached. Review eligible development "
            "resources for possible cost optimization."
        )
    else:
        recommendation = (
            "Budget threshold not reached. No cost-control action "
            "is recommended."
        )

    result = {
        "status": "success",
        "mode": "dry-run",
        "budget_amount_usd": budget_amount,
        "actual_cost_usd": actual_cost,
        "threshold_percent": threshold_percent,
        "threshold_amount_usd": round(threshold_amount, 2),
        "threshold_reached": threshold_reached,
        "action_taken": False,
        "recommendation": recommendation
    }

    logger.info("Result: %s", json.dumps(result))
    return result
```
