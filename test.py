import requests
import json

# Load JSON data from file
with open('hooks/pipeline-hook.json', 'r') as file:
    json_data = json.load(file)

headers = {
    'Content-Type': 'application/json',
    'X-Gitlab-Event': 'Pipeline Hook'
}

response = requests.post('http://127.0.0.1:8000/api/gitlab-webhook/', json=json_data, headers=headers)

print(response.status_code)
print(response.json())
