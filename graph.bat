@echo off
chcp 65001 >nul
setlocal

rem どこから実行しても、この bat があるフォルダで動かす
cd /d "%~dp0"

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
rem streamlit コマンドが PATH にない PC でも起動できるよう、python 経由で起動する
python -m streamlit run app.py

pause
