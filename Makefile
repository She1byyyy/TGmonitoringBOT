build_server: 
	go build -o ./emit_server/server_app.exe ./emit_server/server.go

run_server: build_server
	start "Go Server" powershell -NoExit -Command "Set-Location '$(CURDIR)'; Write-Host 'Run server...' -ForegroundColor Green; ./emit_server/server_app.exe"


# Предварительно надо писать
# .venv/Scripts/Activate.ps1
run_bot:


clean:
	rm ./emit_server/server_app.exe