# GitLab Event Bot

A Django application that receives GitLab webhook events and forwards them to a Telegram supergroup topic.

## Features

- Receives GitLab webhook events via a REST API
- Supports three specific GitLab event types:
  - Push events
  - Merge Request events
  - Pipeline events
- Parses and formats these events into readable messages
- Sends formatted messages to a specific topic in a Telegram supergroup
- Stores events in a database for reference

## Setup

### Prerequisites

- Python 3.8+
- A Telegram Bot token (create one using [@BotFather](https://t.me/botfather))
- A Telegram supergroup with topics enabled
- A GitLab account with webhook configuration permissions

### Installation

1. Clone the repository:

### GitLab Webhook Configuration

1. Go to your GitLab project or group settings
2. Navigate to "Webhooks"
3. Add a new webhook with the following settings:
   - URL: `https://your-domain.com/api/gitlab/webhook/`
   - Select only these events:
     - Push events
     - Merge request events
     - Pipeline events
   - Check "Enable SSL verification" if your server has a valid SSL certificate

