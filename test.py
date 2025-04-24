import requests

bot_token = '6408363442:AAF5uLREzdhR--YLK_bocO-aMKRdAZYKgJ4'
chat_id = '-1002585594120'  # Replace with the group chat ID or username
url = f"https://api.telegram.org/bot{bot_token}/getChatMembers"

params = {
    'chat_id': chat_id
}

response = requests.get(url, params=params)

if response.status_code == 200:
    members = response.json()
    for member in members['result']:
        print(f"User: {member['user']['username']}, ID: {member['user']['id']}")
else:
    print(response)
    print(f"Failed to fetch members. Status code: {response.status_code}")
