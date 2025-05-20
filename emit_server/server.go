package main

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"time" // Добавляем импорт пакета для работы с временем
)

var port string // Делаем порт глобальной переменной

func healthCheckHandler(w http.ResponseWriter, r *http.Request) {
	// Получаем текущее время и форматируем его
	currentTime := time.Now()
	formattedTime := currentTime.Format("15:04:05") // Формат "часы:минуты:секунды"

	// Выводим сообщение с временем и портом
	fmt.Printf("[%s] received ping on port %s...\n", formattedTime, port)

	// Устанавливаем заголовок Content-Type перед записью статуса
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	// Отправляем простой JSON-ответ
	io.WriteString(w, `{"status": "alive"}`)
}

func main() {
	// Получаем порт из аргументов командной строки или используем 8080 по умолчанию
	port = "8080" // Используем глобальную переменную
	if len(os.Args) > 1 {
		port = os.Args[1]
	}

	// Регистрируем обработчик для эндпоинта health-check
	http.HandleFunc("/health-check", healthCheckHandler)

	fmt.Printf("Сервер запущен на порту %s...\n", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		fmt.Printf("Ошибка запуска сервера: %v\n", err)
		os.Exit(1)
	}
}
