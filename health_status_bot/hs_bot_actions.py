from telebot import types
import time
import threading
import json
import os
import requests
from health_status_checker.heatlh_status_checker import health_status_checker
from json_db.json_db import load_json, save_json

# Пути к файлам с данными
USERS_FILE = "./health_status_bot/static/json-db/users.json"
CONSUMERS_FILE = "./health_status_bot/static/json-db/consumers.json"
EVENTS_FILE = "./health_status_bot/static/json-db/events.json"

# Глобальные переменные
users = set()
subscribers = set()
stats_data = []
last_event_index = -1
server_checker = health_status_checker(host="localhost", port=8080)

# Функция для проверки статуса сервера и сохранения статистики
def ping_server():
    """Проверяет статус сервера и возвращает словарь с результатами проверки"""
    ping_delay = server_checker.get_ping_delay()
    
    if ping_delay > 0:
        event = 'info'
        event_msg = 'Сервер работает нормально'
    else:
        event = 'alert'
        event_msg = 'Проблемы с сервером'
        ping_delay = None  # Чтобы не показывать -1 в логах
    
    stat = {
        'timestamp': int(time.time()),
        'ping_задержка': ping_delay,
        'event': event,
        'event_msg': event_msg
    }
    return stat

# Функция потока для периодического сбора статистики
def stats_collector():
    """Поток для постоянного сбора статистики"""
    global stats_data
    while True:
        try:
            stat = ping_server()
            stats_data.append(stat)
            
            # Загружаем существующие события
            events_data = load_json(EVENTS_FILE)
            if not isinstance(events_data, list):
                events_data = []
                
            events_data.append(stat)
            
            # Оставляем только последние 1000 записей, чтобы файл не рос бесконечно
            if len(events_data) > 1000:
                events_data = events_data[-1000:]
                
            save_json(EVENTS_FILE, events_data)
            
            # Также ограничиваем размер stats_data в памяти
            if len(stats_data) > 1000:
                stats_data = stats_data[-1000:]
        except Exception as e:
            print(f"Ошибка при сборе статистики: {e}")
        time.sleep(5)

# Функция для отправки уведомлений подписчикам
def notify_subscribers(bot, message):
    """Отправляет сообщение всем подписчикам"""
    consumers_data = load_json(CONSUMERS_FILE)
    subscribers_list = consumers_data.get('subscribers', [])
    
    for user_id in subscribers_list:
        try:
            bot.send_message(user_id, message)
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

# Функция для проверки новых событий и отправки уведомлений
def check_and_notify(bot):
    """Проверяет новые записи статистики и отправляет уведомления при проблемах"""
    global last_event_index, stats_data
    if len(stats_data) == 0:
        return
    
    # Проверяем новые записи в stats_data
    current_index = len(stats_data) - 1
    if last_event_index == current_index:
        return  # Нет новых данных
        
    # Проверяем только новые записи
    new_events = stats_data[last_event_index+1:]
    
    # Ищем события "alert" среди новых записей
    for event in new_events:
        if event['event'] == 'alert':
            ping_info = f"Задержка превышена" if event['ping_задержка'] is None else f"Задержка: {event['ping_задержка']:.2f} мс"
            notify_subscribers(bot, f"❗️ Внимание! {event['event_msg']} ({ping_info})")
    
    # Обновляем индекс последнего проверенного события
    last_event_index = current_index

# Функция потока для периодической проверки и уведомления
def notification_loop(bot):
    """Поток для периодической проверки новых событий и отправки уведомлений"""
    while True:
        try:
            check_and_notify(bot)
        except Exception as e:
            print(f"Ошибка в цикле уведомлений: {e}")
        time.sleep(10)  # Проверка для уведомлений каждые 10 секунд

def register_handlers(bot):
    """Регистрирует обработчики команд для бота"""
    global users, subscribers
    
    # Загружаем данные о пользователях и подписчиках
    users_data = load_json(USERS_FILE)
    consumers_data = load_json(CONSUMERS_FILE)
    subscribers = set(consumers_data.get('subscribers', []))
    
    # Запускаем потоки для сбора статистики и отправки уведомлений
    threading.Thread(target=stats_collector, daemon=True).start()
    threading.Thread(target=notification_loop, args=(bot,), daemon=True).start()
    
    @bot.message_handler(commands=['start'])
    def start(message):
        user_id = str(message.from_user.id)
        users.add(user_id)
        
        if user_id not in users_data:
            users_data[user_id] = {'subscribed': False}
            save_json(USERS_FILE, users_data)
        
        # Создаем клавиатуру для перехода на сайт
        inline_markup = types.InlineKeyboardMarkup()
        btn_site = types.InlineKeyboardButton(text='Наш сайт', url='https://www.google.com')
        inline_markup.add(btn_site)
        
        # Создаем клавиатуру с основными командами
        reply_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = [
            types.KeyboardButton('📊 Статистика'),
            types.KeyboardButton('🔄 Статус сервера'),
            types.KeyboardButton('🔔 Подписаться'),
            types.KeyboardButton('🔕 Отписаться')
        ]
        reply_markup.add(buttons[0], buttons[1])
        reply_markup.add(buttons[2], buttons[3])
        
        # Отправляем приветственное сообщение с информацией о командах
        welcome_text = (
            "👋 Добро пожаловать в Health Status Bot!\n\n"
            "Доступные команды:\n"
            "📌 /start - начать работу с ботом\n"
            "📌 /subscribe - подписаться на рассылку о статусе сервера\n"
            "📌 /statistics - вывести статистику сервера\n"
            "📌 /get_status - получить текущий статус сервера\n"
            "📌 /unsubscribe - отписаться от рассылки о статусе сервера"
        )
        
        # Сначала отправляем основное сообщение с клавиатурой команд
        bot.send_message(message.chat.id, welcome_text, reply_markup=reply_markup)
        
        # Затем отправляем сообщение с кнопкой для перехода на сайт
        bot.send_message(
            message.chat.id, 
            'По кнопке ниже можно перейти на наш сайт',
            reply_markup=inline_markup
        )
    
    @bot.message_handler(commands=['subscribe'])
    def subscribe(message):
        user_id = str(message.from_user.id)
        
        # Проверяем, есть ли пользователь в базе
        if user_id not in users_data:
            users_data[user_id] = {'subscribed': False}
        
        # Проверяем, не подписан ли уже пользователь
        if users_data[user_id]['subscribed']:
            bot.reply_to(message, "✅ Вы уже подписаны на рассылку о статусе сервера.")
            return
        
        # Подписываем пользователя
        users_data[user_id]['subscribed'] = True
        save_json(USERS_FILE, users_data)
        
        # Обновляем список подписчиков
        if 'subscribers' not in consumers_data:
            consumers_data['subscribers'] = []
        
        if user_id not in consumers_data['subscribers']:
            consumers_data['subscribers'].append(user_id)
            save_json(CONSUMERS_FILE, consumers_data)
        
        subscribers.add(user_id)
        bot.reply_to(message, "✅ Вы успешно подписались на рассылку о статусе сервера!")
    
    @bot.message_handler(commands=['unsubscribe'])
    def unsubscribe(message):
        user_id = str(message.from_user.id)
        
        # Проверяем, есть ли пользователь в базе и подписан ли он
        if user_id not in users_data or not users_data[user_id]['subscribed']:
            bot.reply_to(message, "❌ Вы не подписаны на рассылку о статусе сервера.")
            return
        
        # Отписываем пользователя
        users_data[user_id]['subscribed'] = False
        save_json(USERS_FILE, users_data)
        
        # Обновляем список подписчиков
        if 'subscribers' in consumers_data and user_id in consumers_data['subscribers']:
            consumers_data['subscribers'].remove(user_id)
            save_json(CONSUMERS_FILE, consumers_data)
        
        if user_id in subscribers:
            subscribers.remove(user_id)
        
        bot.reply_to(message, "✅ Вы успешно отписались от рассылки о статусе сервера.")
    
    @bot.message_handler(commands=['get_status'])
    def get_status(message):
        try:
            ping_delay = server_checker.get_ping_delay()
            
            if ping_delay > 0:
                status_text = f"✅ Сервер работает нормально\nЗадержка: {ping_delay:.2f} мс"
            else:
                status_text = "❌ Сервер недоступен или возникли проблемы"
            
            bot.reply_to(message, status_text)
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка при проверке статуса сервера: {str(e)}")
    
    @bot.message_handler(commands=['statistics'])
    def statistics(message):
        try:
            # Загружаем события из файла
            events_data = load_json(EVENTS_FILE)
            
            # Проверяем наличие данных
            if not events_data:
                bot.reply_to(message, "📊 Статистика еще не собрана.")
                return
            
            # Получаем последние 5 записей
            last_records = events_data[-5:] if len(events_data) >= 5 else events_data
            
            # Формируем сообщение со статистикой
            stats_text = "📊 *Последние данные о состоянии сервера:*\n\n"
            
            for record in last_records:
                timestamp = time.strftime('%H:%M:%S', time.localtime(record['timestamp']))
                status = "✅" if record['event'] == 'info' else "❌"
                
                if record['ping_задержка'] is not None:
                    delay = f"{record['ping_задержка']:.2f} мс"
                else:
                    delay = "Н/Д"
                
                stats_text += f"*{timestamp}* {status} {record['event_msg']} (Задержка: {delay})\n"
            
            # Считаем процент доступности
            total_records = len(events_data)
            info_records = sum(1 for record in events_data if record['event'] == 'info')
            availability = (info_records / total_records * 100) if total_records > 0 else 0
            
            stats_text += f"\n*Общая доступность:* {availability:.2f}%"
            stats_text += f"\n*Всего проверок:* {total_records}"
            
            bot.reply_to(message, stats_text, parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"❌ Ошибка при получении статистики: {str(e)}")
    
    @bot.message_handler(content_types=['text'])
    def handle_text(message):
        if message.text == '📊 Статистика':
            statistics(message)
        elif message.text == '🔄 Статус сервера':
            get_status(message)
        elif message.text == '🔔 Подписаться':
            subscribe(message)
        elif message.text == '🔕 Отписаться':
            unsubscribe(message)
    
    return users, subscribers
