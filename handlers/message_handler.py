import json

def extract_message_data(webhook_data):
    messages = []
    
    try:
        if 'entry' in webhook_data:
            for entry in webhook_data['entry']:
                if 'changes' in entry:
                    for change in entry['changes']:
                        if 'value' in change and 'messages' in change['value']:
                            for message in change['value']['messages']:
                                messages.append({
                                    'from': message['from'],
                                    'type': message['type'],
                                    'timestamp': message['timestamp'],
                                    'content': message
                                })
    except Exception as e:
        print(f"error extrayendo mensajes: {e}")
    
    return messages