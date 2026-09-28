@echo off
chcp 65001 >nul
setlocal

echo ============================================
echo  Graph Maker(グラフ作成ツール) 起動チェック
echo ============================================

where python >nul 2>nul
if errorlevel 1 (
    echo [エラー] Python が見つかりません。
    echo README.md の「2. Pythonのインストール」を確認してインストールしてください。
    pause
    exit /b 1
)

python -c "import streamlit, plotly, kaleido, pandas" >nul 2>nul
if errorlevel 1 (
    echo [エラー] 必要なライブラリが不足しています。
    echo このフォルダで次のコマンドを実行してください:
    echo     pip install -r requirements.txt
    echo 詳しくは README.md の「4. ライブラリのインストール」を確認してください。
    pause
    exit /b 1
)

echo 起動します。ブラウザで http://localhost:8501 が開きます。
echo 終了するには、このウィンドウを閉じてください。
streamlit run app.py

pause
