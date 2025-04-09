@echo off
echo タスクバーアイコンキャッシュのクリア手順
echo =================================
echo.
echo 1. アプリケーションを一度閉じてください
echo 2. タスクバーからピン留めされていれば右クリックして「タスクバーからピン留めを外す」を選択
echo 3. 以下のコマンドを実行してアイコンキャッシュをクリアします
echo.
echo タスクバーのアイコンをクリアします...

rem エクスプローラーのプロセスを再起動
taskkill /f /im explorer.exe
timeout /t 2

rem アイコンキャッシュを削除
del /a /q %localappdata%\IconCache.db
del /a /f /q %localappdata%\Microsoft\Windows\Explorer\iconcache*
del /a /f /q %localappdata%\Microsoft\Windows\Explorer\thumbcache*

rem シェルのアイコンキャッシュをクリア
ie4uinit.exe -ClearIconCache
ie4uinit.exe -show

rem エクスプローラーを再起動
start explorer.exe

echo.
echo 完了しました！
echo アプリケーションを起動し、必要に応じてタスクバーに再度ピン留めしてください。
echo.
pause 