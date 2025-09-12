import sys
# pysqlite3 を sqlite3 として使う（Chroma 等で必要な環境向け）
sys.modules["sqlite3"] = __import__("pysqlite3")

import streamlit as st
st.set_page_config(page_title="Company Inner Search")

"""
このファイルは、Webアプリのメイン処理が記述されたファイルです。
"""

############################################################
# 1. 標準ライブラリの読み込み
############################################################
import os
import logging
import traceback
from dotenv import load_dotenv

############################################################
# 2. 環境変数・ディレクトリ準備
############################################################
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.makedirs(".chroma", exist_ok=True)

load_dotenv()
# OPENAI_API_KEY2 があれば OPENAI_API_KEY にコピー
if "OPENAI_API_KEY2" in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY2"]

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
# 9. チャット入力の受付
############################################################
chat_message = st.chat_input(ct.CHAT_INPUT_HELPER_TEXT)

############################################################
# 10. チャット送信時の処理
############################################################
if chat_message:
    # 10-1. ユーザーメッセージの表示
    logger.info({"message": chat_message, "application_mode": st.session_state.mode})
    with st.chat_message("user"):
        st.markdown(chat_message)

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
            else:
                # 念のため未定義モード対策
                content = cn.display_search_llm_response(llm_response)

            logger.info({"message": content, "application_mode": st.session_state.mode})
        except Exception as e:
            logger.error(f"{ct.DISP_ANSWER_ERROR_MESSAGE}\n{e}")
            st.error(utils.build_error_message(ct.DISP_ANSWER_ERROR_MESSAGE), icon=ct.ERROR_ICON)
            st.stop()

    # 10-4. 会話ログに追加
    st.session_state.messages.append({"role": "user", "content": chat_message})
    st.session_state.messages.append({"role": "assistant", "content": content})
