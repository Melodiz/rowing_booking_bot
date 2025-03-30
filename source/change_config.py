import json

def is_admin(user_id):
    try:
        with open('data/config.json', 'r') as config_file:
            config = json.load(config_file)
        admin_ids = config.get('admin_ids', [])
        return user_id in admin_ids
    except Exception as e:
        print(f"Ошибка проверки статуса администратора: {str(e)}")
        return False

def set_new_password(user_id, new_password):
    if not is_admin(user_id):
        return False, "У вас нет прав для смены пароля."

    try:
        with open('data/config.json', 'r') as config_file:
            config = json.load(config_file)
        
        config['verification_password'] = new_password
        
        with open('data/config.json', 'w') as config_file:
            json.dump(config, config_file, indent=2)
        
        return True, "Пароль успешно обнавлен."
    except Exception as e:
        return False, f"Ошибка обнавления пароля: {str(e)}"

def get_current_password():
    try:
        with open('data/config.json', 'r') as config_file:
            config = json.load(config_file)
        return config.get('verification_password', '')
    except Exception as e:
        return None

def set_number_of_concepts(user_id, new_number):
    if not is_admin(user_id):
        return False, "У вас нет прав для изменения количества концептов."

    try:
        with open('data/config.json', 'r') as config_file:
            config = json.load(config_file)
        
        config['number_of_concepts'] = new_number
        
        with open('data/config.json', 'w') as config_file:
            json.dump(config, config_file, indent=2)
        
        return True, f"Количество концептов успешно обновлено на {new_number}."
    except Exception as e:
        return False, f"Ошибка обновления количества концептов: {str(e)}"

def get_number_of_concepts():
    try:
        with open('data/config.json', 'r') as config_file:
            config = json.load(config_file)
        return config.get('number_of_concepts', 6)  # Default to 6 if not set
    except Exception as e:
        print(f"Ошибка получения количества концептов: {str(e)}")
        return None
    

def set_gym_closed_period(user_id, start_datetime, end_datetime):
    if not is_admin(user_id):
        return False, "У вас нет прав для изменения периода закрытия зала."

    try:
        with open('data/config.json', 'r') as config_file:
            config = json.load(config_file)

        config['close_GYM_from'] = start_datetime.isoformat().replace('T',' ')
        config['close_GYM_until'] = end_datetime.isoformat().replace('T',' ')

        with open('data/config.json', 'w') as config_file:
            json.dump(config, config_file, indent=2)

        return True, "Период закрытия зала успешно обновлен."
    except Exception as e:
        return False, f"Произошла ошибка при обновлении периода закрытия зала: {str(e)}"


def cancel_gym_closed_period(user_id):
    if not is_admin(user_id):
        return False, "У вас нет прав для отмены периода закрытия зала."

    try:
        with open('data/config.json', 'r') as config_file:
            config = json.load(config_file)

        config['close_GYM_from'] = "NaN"
        config['close_GYM_until'] = "Nan"

        with open('data/config.json', 'w') as config_file:
            json.dump(config, config_file, indent=2)

        return True, "Период закрытия зала успешно отменен."
    except Exception as e:
        return False, f"Произошла ошибка при отмене периода закрытия зала: {str(e)}"
    
def get_gym_closed_periods():
    try:
        with open('data/config.json', 'r') as config_file:
            config = json.load(config_file)
        start_datetime = config.get('close_GYM_from', "NaN")
        end_datetime = config.get('close_GYM_until', "NaN")
        return start_datetime, end_datetime
    except Exception as e:
        print(f"Ошибка получения периода закрытия зала: {str(e)}")
        return None, None