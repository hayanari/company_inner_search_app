import sys
sys.modules["sqlite3"] = __import__("pysqlite3")

import streamlit as st
st.set_page_config(
    page_title="Company Inner Search"
)

"""
このファイルは、Webアプリのメイン処理が記述されたファイルです。
"""

import sys
sys.modules["sqlite3"] = __import__("pysqlite3")

############################################################
# 1. 標準ライブラリの読み込み
############################################################
import sys
import sqlite3
import os
import logging
import traceback
from dotenv import load_dotenv

# Python と SQLite の情報を表示（確認用）
st.write("Python executable:", sys.executable)
st.write("SQLite version:", sqlite3.sqlite_version)

############################################################
# 2. 環境変数・ディレクトリ準備
############################################################
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.makedirs(".chroma", exist_ok=True)

load_dotenv()
# OPENAI_API_KEY2があればOPENAI_API_KEYにコピー
if "OPENAI_API_KEY2" in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY2"]
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.makedirs(".chroma", exist_ok=True)

############################################################
# 3. 自作モジュールの import
############################################################
import utils
import components as cn
from initialize import initialize
import constants as ct

############################################################
# 4. ログ設定
############################################################
logger = logging.getLogger(ct.LOGGER_NAME)

############################################################
# 5. st.session_state 初期化
############################################################
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mode" not in st.session_state:
    st.session_state.mode = ct.ANSWER_MODE_1
if "initialized" not in st.session_state:
    st.session_state.initialized = False

############################################################
# 6. 初期化処理
############################################################
try:
    initialize()
except Exception as e:
    tb_str = traceback.format_exc()
    error_message = f"{ct.INITIALIZE_ERROR_MESSAGE}\n\n例外内容: {e}\n\n発生場所:\n{tb_str}"
    st.error(utils.build_error_message(error_message), icon=ct.ERROR_ICON)
    st.stop()

if not st.session_state.initialized:
    st.session_state.initialized = True
    logger.info(ct.APP_BOOT_MESSAGE)

############################################################
# 7. 初期表示
############################################################
cn.display_app_title()
st.session_state.mode = cn.display_select_mode(key_prefix="main_mode_unique")
cn.display_initial_ai_message()

############################################################
# 8. 会話ログの表示
############################################################
try:
    cn.display_conversation_log()
except Exception as e:
    logger.error(f"{ct.CONVERSATION_LOG_ERROR_MESSAGE}\n{e}")
    st.error(utils.build_error_message(ct.CONVERSATION_LOG_ERROR_MESSAGE), icon=ct.ERROR_ICON)
    st.stop()

############################################################
# 9. チャット入力の受付（※このブロックは削除し、下の1箇所に統一）
############################################################
# （ここは削除）

    # 10-2. LLMからの回答取得
    res_box = st.empty()
    with st.spinner(ct.SPINNER_TEXT):
        try:
            llm_response = utils.get_llm_response(chat_message)
        except Exception as e:
            logger.error(f"{ct.GET_LLM_RESPONSE_ERROR_MESSAGE}\n{e}")
            st.error(utils.build_error_message(ct.GET_LLM_RESPONSE_ERROR_MESSAGE), icon=ct.ERROR_ICON)
            st.stop()

    # 10-3. LLMからの回答表示
    with st.chat_message("assistant"):
        try:
            if st.session_state.mode == ct.ANSWER_MODE_1:
                content = cn.display_search_llm_response(llm_response)
            elif st.session_state.mode == ct.ANSWER_MODE_2:
                content = cn.display_contact_llm_response(llm_response)
            logger.info({"message": content, "application_mode": st.session_state.mode})
        except Exception as e:
            logger.error(f"{ct.DISP_ANSWER_ERROR_MESSAGE}\n{e}")
            st.error(utils.build_error_message(ct.DISP_ANSWER_ERROR_MESSAGE), icon=ct.ERROR_ICON)
            st.stop()

    # 10-4. 会話ログに追加
    st.session_state.messages.append({"role": "user", "content": chat_message})
    st.session_state.messages.append({"role": "assistant", "content": content})
import sys
import sqlite3
import streamlit as st
"""
このファイルは、Webアプリのメイン処理が記述されたファイルです。
"""

############################################################
# 1. ライブラリの読み込み
############################################################
# 「.env」ファイルから環境変数を読み込むための関数
from dotenv import load_dotenv
# LangSmithトレース無効化、ChromaDB用ディレクトリ作成
import os
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.makedirs(".chroma", exist_ok=True)
# ログ出力を行うためのモジュール
import logging
# streamlitアプリの表示を担当するモジュール
import streamlit as st
# （自作）画面表示以外の様々な関数が定義されているモジュール
import utils
# （自作）アプリ起動時に実行される初期化処理が記述された関数
from initialize import initialize
# （自作）画面表示系の関数が定義されているモジュール
import components as cn
# （自作）変数（定数）がまとめて定義・管理されているモジュール
import constants as ct


############################################################
# 2. 設定関連
############################################################


st.write("Python executable:", sys.executable)
st.write("SQLite version:", sqlite3.sqlite_version)

# ログ出力を行うためのロガーの設定
logger = logging.getLogger(ct.LOGGER_NAME)

# st.session_stateの初期化
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mode" not in st.session_state:
    st.session_state.mode = ct.ANSWER_MODE_1  # デフォルト値は適宜

############################################################
# 3. 初期化処理
############################################################
import traceback
try:
    # 初期化処理（initialize.pyのinitialize関数を実行）
    initialize()
except Exception as e:
    # トレースバック情報を取得
    tb_str = traceback.format_exc()
    # 画面表示用メッセージを作成
    error_message = f"{ct.INITIALIZE_ERROR_MESSAGE}\n\n例外内容: {e}\n\n発生場所:\n{tb_str}"
    # エラーを1回だけ表示（アイコンも付けられる）
    st.error(utils.build_error_message(error_message), icon=ct.ERROR_ICON)
    # 後続処理を中断
    st.stop()

# アプリ起動時のログファイルへの出力
if not "initialized" in st.session_state:
    st.session_state.initialized = True
    logger.info(ct.APP_BOOT_MESSAGE)


############################################################
# 4. 初期表示
############################################################
# タイトル表示
cn.display_app_title()

# モード表示
cn.display_select_mode(key_prefix="init_mode_unique")

# AIメッセージの初期表示
cn.display_initial_ai_message()


############################################################
# 5. 会話ログの表示
############################################################
try:
    # 会話ログの表示
    cn.display_conversation_log()
except Exception as e:
    # エラーログの出力
    logger.error(f"{ct.CONVERSATION_LOG_ERROR_MESSAGE}\n{e}")
    # エラーメッセージの画面表示
    st.error(utils.build_error_message(ct.CONVERSATION_LOG_ERROR_MESSAGE), icon=ct.ERROR_ICON)
    # 後続の処理を中断
    st.stop()


############################################################
# 6. チャット入力の受け付け
############################################################
chat_message = st.chat_input(ct.CHAT_INPUT_HELPER_TEXT)


############################################################
# 7. チャット送信時の処理
############################################################
if chat_message:
    # ==========================================
    # 7-1. ユーザーメッセージの表示
    # ==========================================
    # ユーザーメッセージのログ出力
    logger.info({"message": chat_message, "application_mode": st.session_state.mode})

    # ユーザーメッセージを表示
    with st.chat_message("user"):
        st.markdown(chat_message)

    # ==========================================
    # 7-2. LLMからの回答取得
    # ==========================================
    # 「st.spinner」でグルグル回っている間、表示の不具合が発生しないよう空のエリアを表示
    res_box = st.empty()
    # LLMによる回答生成（回答生成が完了するまでグルグル回す）
    with st.spinner(ct.SPINNER_TEXT):
        try:
            # 画面読み込み時に作成したRetrieverを使い、Chainを実行
            llm_response = utils.get_llm_response(chat_message)
        except Exception as e:
            # エラーログの出力
            logger.error(f"{ct.GET_LLM_RESPONSE_ERROR_MESSAGE}\n{e}")
            # エラーメッセージの画面表示
            st.error(utils.build_error_message(ct.GET_LLM_RESPONSE_ERROR_MESSAGE), icon=ct.ERROR_ICON)
            # 後続の処理を中断
            st.stop()
    
    # ==========================================
    # 7-3. LLMからの回答表示
    # ==========================================
    with st.chat_message("assistant"):
        try:
            # ==========================================
            # モードが「社内文書検索」の場合
            # ==========================================
            if st.session_state.mode == ct.ANSWER_MODE_1:
                # 入力内容と関連性が高い社内文書のありかを表示
                content = cn.display_search_llm_response(llm_response)

            # ==========================================
            # モードが「社内問い合わせ」の場合
            # ==========================================
            elif st.session_state.mode == ct.ANSWER_MODE_2:
                # 入力に対しての回答と、参照した文書のありかを表示
                content = cn.display_contact_llm_response(llm_response)
            
            # AIメッセージのログ出力
            logger.info({"message": content, "application_mode": st.session_state.mode})
        except Exception as e:
            # エラーログの出力
            logger.error(f"{ct.DISP_ANSWER_ERROR_MESSAGE}\n{e}")
            # エラーメッセージの画面表示
            st.error(utils.build_error_message(ct.DISP_ANSWER_ERROR_MESSAGE), icon=ct.ERROR_ICON)
            # 後続の処理を中断
            st.stop()

    # ==========================================
    # 7-4. 会話ログへの追加
    # ==========================================
    # 表示用の会話ログにユーザーメッセージを追加
    st.session_state.messages.append({"role": "user", "content": chat_message})
    # 表示用の会話ログにAIメッセージを追加
    st.session_state.messages.append({"role": "assistant", "content": content})