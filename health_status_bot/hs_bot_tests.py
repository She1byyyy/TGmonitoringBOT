from health_status_checker.heatlh_status_checker import health_status_checker

if __name__ == "__main__":
    checker = health_status_checker(host="localhost", port=8080)
    print("Ожидание запуска сервера...")
    
    if checker.wait_for_server(max_attempts=5, interval=2):
        print("Сервер успешно запущен и отвечает на запросы!")
    else:
        print("Не удалось дождаться запуска сервера.")