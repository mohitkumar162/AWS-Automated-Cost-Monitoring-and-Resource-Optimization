# AWS-Automated-Cost-Monitoring-and-Resource-Optimization
A serverless AWS project that monitors budget alerts, processes notifications, evaluates spending thresholds, and generates cost-optimization recommendations using AWS Budgets, Amazon SNS, AWS Lambda, and Amazon CloudWatch.

## 1. Project Overview

Cloud resources can generate unexpected costs when spending is not monitored regularly. This project demonstrates an event-driven approach to AWS cost monitoring by connecting a budget alert to a notification system and a Lambda function.

When a budget notification is received, the Lambda function extracts the available cost and threshold information, calculates the threshold amount, evaluates whether the threshold has been reached, and records the result in CloudWatch Logs.

The project uses **dry-run mode** to safely demonstrate the evaluation process without making changes to AWS resources.

### Objectives

- Configure a monthly AWS cost budget and alert threshold.
- Send budget notifications using Amazon SNS.
- Trigger AWS Lambda through an SNS subscription.
- Parse notification data and evaluate spending thresholds.
- Generate cost-optimization recommendations.
- Monitor execution and troubleshoot using CloudWatch Logs.
- Validate both above-threshold and below-threshold scenarios.

## 2. AWS Services Used

| AWS service            | Purpose                                                                       |
| ---------------------- | ----------------------------------------------------------------------------- |
| AWS Budgets            | Defines the monthly budget and spending alerts.                               |
| Amazon SNS             | Distributes notifications to the email subscriber and Lambda function.        |
| AWS Lambda             | Processes notification data and evaluates the budget threshold.               |
| Amazon CloudWatch Logs | Stores Lambda execution logs, evaluation results, and diagnostic information. |
| AWS IAM                | Controls permissions required for service interactions and Lambda execution.  |

## 3. Architecture Diagram

Save the final, corrected dark-mode architecture diagram as `architecture.png` inside the `screenshots/` directory.



### Architecture workflow

1. **AWS Budgets:** Monitors spending against the configured monthly budget and generates alerts when a threshold is reached.
2. **Amazon SNS:** Receives the published notification and distributes it to confirmed subscribers, including email and Lambda.
3. **AWS Lambda:** Parses the notification, extracts recognized values, and evaluates the cost against the configured threshold.
4. **Threshold evaluation:** Calculates the threshold amount and determines whether spending has reached it.
5. **Amazon CloudWatch Logs:** Records execution details, notification data, evaluation results, and warnings.
6. **Email notification:** The SNS email subscription receives budget notification messages.

**Important:** EC2 stopping or modification is not implemented by the current Lambda code. The project currently evaluates conditions and generates recommendations in dry-run mode.

## 4. AWS Configuration

| Configuration               | Value                        |
| --------------------------- | ---------------------------- |
| AWS Region                  | Asia Pacific (Mumbai)        |
| Region code                 | `ap-south-1`                 |
| Budget name                 | `AWS-Cost-Monitoring-Budget` |
| Monthly budget              | `$10.00`                     |
| Actual-cost alert threshold | `80%`                        |
| Threshold amount            | `$8.00`                      |
| SNS topic                   | `aws-cost-alerts`            |
| Lambda function             | `aws-cost-optimizer-dry-run` |
| Lambda runtime              | Python 3.x                   |
| Execution mode              | Dry-run                      |
| Logging service             | Amazon CloudWatch Logs       |

### Threshold calculation

The function calculates the threshold amount using:

```text
Threshold Amount = Budget Amount × Threshold Percentage / 100

Threshold Amount = $10.00 × 80 / 100
                 = $8.00
```

The actual cost is compared with the calculated threshold:

- `$5.50 < $8.00` — threshold not reached.
- `$8.50 >= $8.00` — threshold reached.

These values demonstrate the evaluation logic; they are test inputs, not claims about live AWS spending.

## 5. Project Structure

```text
aws-automated-cost-monitoring/
├── lambda_function.py
├── README.md
└── screenshots/
    ├── architecture.png
    ├── budget-overview.png
    ├── budget-alert-configuration.png
    ├── budget-review-configuration.png
    ├── sns-topic-and-subscriptions.png
    ├── sns-access-policy.png
    ├── sns-subscription-confirmed.png
    ├── sns-email-subscription-confirmation.png
    ├── lambda-function-overview.png
    ├── lambda-sns-trigger.png
    ├── lambda-test-below-threshold.png
    ├── lambda-test-above-threshold.png
    ├── cloudwatch-log-group.png
    ├── cloudwatch-test-logs.png
    ├── cloudwatch-budget-notification-logs.png
    └── sns-budget-alert-email.png
```

Use these names when organizing your screenshots. Include only files that you actually save in the repository.

## 6. Complete Lambda Source Code

Create a file named `lambda_function.py` and add the following code.

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

## 7. How the Lambda Function Works

1. **Receives an event:** Accepts a direct Lambda test event or an SNS event.
2. **Extracts the message:** Attempts to decode JSON and supports plain-text notifications.
3. **Reads the values:** Identifies the budget amount, actual cost, and threshold percentage from supported fields or recognized text labels.
4. **Validates the values:** Checks for missing data, invalid numeric values, and out-of-range budget or percentage values.
5. **Calculates the threshold:** Computes the dollar value associated with the configured percentage.
6. **Evaluates the condition:** Determines whether the actual cost is greater than or equal to the threshold amount.
7. **Generates a recommendation:** Returns a recommendation based on the evaluation.
8. **Records the result:** Writes execution information and the result to CloudWatch Logs.

The function returns `action_taken: false` and uses dry-run mode. It does not call EC2 APIs or perform resource-control actions.

## 8. Testing and Validation

The project was tested with simulated cost values to validate both threshold outcomes.

### Test 1: Threshold reached

**Input:**

```json
{
  "source": "manual-test",
  "budget_name": "AWS-Cost-Monitoring-Budget",
  "budget_amount_usd": 10.0,
  "actual_cost_usd": 8.5,
  "threshold_percent": 80
}
```

**Expected result:**

```json
{
  "status": "success",
  "mode": "dry-run",
  "budget_amount_usd": 10.0,
  "actual_cost_usd": 8.5,
  "threshold_percent": 80,
  "threshold_amount_usd": 8.0,
  "threshold_reached": true,
  "action_taken": false,
  "recommendation": "Budget threshold reached. Review eligible development resources for possible cost optimization."
}
```

### Test 2: Threshold not reached

**Input:**

```json
{
  "source": "manual-test",
  "budget_name": "AWS-Cost-Monitoring-Budget",
  "budget_amount_usd": 10.0,
  "actual_cost_usd": 5.5,
  "threshold_percent": 80
}
```

**Expected result:**

```json
{
  "status": "success",
  "mode": "dry-run",
  "budget_amount_usd": 10.0,
  "actual_cost_usd": 5.5,
  "threshold_percent": 80,
  "threshold_amount_usd": 8.0,
  "threshold_reached": false,
  "action_taken": false,
  "recommendation": "Budget threshold not reached. No cost-control action is recommended."
}
```

### Test 3: SNS notification delivery

The SNS topic has an email subscription and a Lambda subscription. The email subscription was confirmed, and the Lambda subscription was also shown as confirmed in the SNS console.

A simulated notification was published to the SNS topic, and the notification email was received.

### Test 4: CloudWatch log validation

CloudWatch Logs showed Lambda invocation messages, dry-run mode, received notification data, evaluation results, and a warning for a notification whose cost and threshold data could not be recognized.

This demonstrates why notification parsing and input validation matter: receiving an alert does not guarantee that every notification format contains fields the function can evaluate.

**Testing scope:** The above-threshold and below-threshold results were verified with test inputs. The SNS-to-Lambda integration and notification email were also tested. The screenshots should distinguish these tests from live AWS billing events.

## 9. Security and Cost Considerations

- **Dry-run safety:** Keep `DRY_RUN = True` during testing. The current implementation does not modify resources.
- **Least privilege:** Give the Lambda execution role only the permissions needed for logging and service integration.
- **SNS access policy:** Restrict publishing permissions to the intended AWS service and account conditions.
- **Credentials:** Never commit AWS access keys, secrets, or sensitive account information to the repository.
- **Cost awareness:** AWS Budgets alerts are not a hard spending cap. Actual AWS charges may continue after an alert is generated.
- **Resource cleanup:** Review and remove unused development resources to avoid unnecessary charges.
- **Notification parsing:** Validate the actual notification format before relying on the function for automated decisions.

## 10. Learning Outcomes

Through this project, I gained practical experience with:

- AWS Budgets and spending thresholds.
- Amazon SNS topics, subscriptions, and notifications.
- AWS Lambda event processing with Python.
- Event-driven serverless architecture.
- Threshold calculations and input validation.
- CloudWatch Logs for debugging and monitoring.
- AWS IAM permissions and service integration.
- Testing different budget scenarios safely in dry-run mode.

## Conclusion

This project demonstrates a serverless workflow for AWS budget notifications, cost-threshold evaluation, email delivery, and execution monitoring. It connects AWS Budgets, Amazon SNS, AWS Lambda, and CloudWatch Logs in a practical cloud-finance use case.

The current implementation focuses on **safe evaluation and cost-optimization recommendations**. Resource stopping or modification is not performed by the existing Lambda code.
