import requests
import time

class health_status_checker:
    def __init__(self, host, port=8080, endpoint="/health-check", timeout=5):
        """
        Инициализация чекера состояния сервера
        
        :param host: адрес сервера (без http://)
        :param port: порт HTTP-сервера
        :param endpoint: эндпоинт для проверки состояния
        :param timeout: таймаут запроса в секундах
        """
        self.url = f"http://{host}:{port}{endpoint}"
        self.timeout = timeout
    
    def is_alive(self):
        """
        Проверка состояния сервера
        
        :return: True если сервер отвечает и возвращает статус 200, иначе False
        """
        try:
            response = requests.get(self.url, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "alive":
                    return True
            return False
        except (requests.RequestException, ValueError):
            return False
    
    def wait_for_server(self, max_attempts=30, interval=5):
        """
        Ожидание доступности сервера
        
        :param max_attempts: максимальное количество попыток
        :param interval: интервал между попытками в секундах
        :return: True если сервер стал доступен, False если превышено число попыток
        """
        for _ in range(max_attempts):
            if self.is_alive():
                return True
            time.sleep(interval)
        return False
        
    def get_ping_delay(self):
        """
        Измерение задержки ответа сервера
        
        :return: задержка в миллисекундах, если сервер отвечает, иначе -1
        """
        try:
            start_time = time.time()
            response = requests.get(self.url, timeout=self.timeout)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "alive":
                    delay = (time.time() - start_time) * 1000
                    return delay
            return -1
        except (requests.RequestException, ValueError):
            return -1
