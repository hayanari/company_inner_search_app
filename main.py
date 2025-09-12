import os, streamlit as st
import sys
# pysqlite3 を sqlite3 として使う（Chroma 等の互換用）
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

# Streamlit CloudのSecretsを環境変数に反映
os.environ.update(st.secrets)

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
# 念のため：常に存在する形で chat_message を用意（旧コード参照防止）
st.session_state.setdefault("last_user_text", "")

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
# ここで必ず chat_message（ローカル変数）を定義し、空文字も許容しない
user_text = st.chat_input(ct.CHAT_INPUT_HELPER_TEXT)
chat_message = user_text  # 旧コードが chat_message を参照しても NameError にならないよう橋渡し
# 参照用に保持
if user_text is not None:
    st.session_state.last_user_text = user_text

############################################################
# 10. チャット送信時の処理
############################################################
if user_text is not None and str(user_text).strip() != "":
    # 10-1. ユーザーメッセージの表示
    logger.info({"message": user_text, "application_mode": st.session_state.mode})
    with st.chat_message("user"):
        st.markdown(user_text)

     # 10-2. LLMからの回答取得
    res_box = st.empty()
    with st.spinner(ct.SPINNER_TEXT):
        try:
            llm_response = utils.get_llm_response(user_text)
        except Exception as e:
            # 例外の中身を表示（デバッグ用）
            import traceback, os
            logger.exception(e)
            tb_str = traceback.format_exc()
            debug_on = os.getenv("APP_DEBUG", "0") == "1"

            if debug_on:
                with st.expander("エラー詳細（開発者向け）", expanded=True):
                    st.code(f"{type(e).__name__}: {e}\n\n{tb_str}")
                    key = os.getenv("OPENAI_API_KEY", "")
                    masked = (key[:5] + "..." + key[-4:]) if key else "(未設定)"
                    st.write("OPENAI_API_KEY:", masked)
                    st.write("OPENAI_API_KEY2 存在:", "OPENAI_API_KEY2" in os.environ)
                    try:
                        import openai
                        st.write("openai.__version__:", getattr(openai, "__version__", "unknown"))
                    except Exception as imp_err:
                        st.write("openai import error:", str(imp_err))

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
                content = cn.display_search_llm_response(llm_response)

            logger.info({"message": content, "application_mode": st.session_state.mode})
        except Exception as e:
            logger.error(f"{ct.DISP_ANSWER_ERROR_MESSAGE}\n{e}")
            st.error(utils.build_error_message(ct.DISP_ANSWER_ERROR_MESSAGE), icon=ct.ERROR_ICON)
            st.stop()

    # 10-4. 会話ログに追加
    st.session_state.messages.append({"role": "user", "content": user_text})
    st.session_state.messages.append({"role": "assistant", "content": content})
