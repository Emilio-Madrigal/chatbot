def process_button_interaction(button_data):
    try:
        return {
            'id': button_data['button_reply']['id'],
            'title': button_data['button_reply']['title']
        }
    except KeyError as e:
        print(f"error procesando botón: {e}")
        return None

def process_list_interaction(list_data):

    try:
        return {
            'id': list_data['list_reply']['id'],
            'title': list_data['list_reply']['title'],
            'description': list_data['list_reply'].get('description', '')
        }
    except KeyError as e:
        print(f"error procesando lista: {e}")
        return None