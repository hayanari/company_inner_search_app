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

load_dotenv()
# OPENAI_API_KEY2 があれば OPENAI_API_KEY にコピー
if "OPENAI_API_KEY2" in os.environ:
    os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY2"]

############################################################
# 3. 自作モジュールの import
############################################################
import utils
import components as cn
import initialize
import constants as ct

############################################################
# 4. ログ設定
############################################################
logger = logging.getLogger(ct.LOGGER_NAME)

# ==== debug flag ====
import os
DEBUG = os.getenv("APP_DEBUG", "0") == "1"
logger.setLevel(logging.DEBUG if DEBUG else logging.WARNING)
def dlog(msg):
    if DEBUG:
        logger.debug(msg)  # 端末ログにだけ出す（画面には出ない）

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

# --- ここで必ず初期化 ---
try:
    initialize.initialize()
except Exception as e:
    tb_str = traceback.format_exc()
    error_message = f"{ct.INITIALIZE_ERROR_MESSAGE}\n\n例外内容: {e}\n\n発生場所:\n{tb_str}"
    st.error(utils.build_error_message(error_message), icon=ct.ERROR_ICON)
    # st.write("traceback:")
    # st.write(traceback.format_exc())
    st.stop()

if not st.session_state.initialized:
    st.session_state.initialized = True
    logger.info(ct.APP_BOOT_MESSAGE)

############################################################
# 7. 初期表示
############################################################
cn.display_sidebar()
cn.display_app_title()
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

    # 10-2. 全文検索（キーワード一致）
    keyword_results = []
    try:
        keyword_results = utils.search_documents_by_keyword(
            user_text, st.session_state.get("docs_all"), max_results=ct.MAX_KEYWORD_RESULTS
        )
        dlog(f"keyword_results: {len(keyword_results)}")
    except Exception as e:
        logger.warning(f"全文検索エラー: {e}")
        keyword_results = []

    # 10-3. LLMからの回答取得（RAG）
    try:
        llm_response = utils.get_llm_response(user_text)
        dlog(f"llm_response type: {type(llm_response)}")
    except Exception:
        logger.exception("get_llm_response failed; fallback to fixed list")
        utils.render_hr_list_fixed()
        llm_response = None

    # 10-4. 回答表示
    try:
        has_keyword = bool(keyword_results)
        has_rag = False
        if st.session_state.mode == ct.ANSWER_MODE_1:
            content = cn.display_search_llm_response(llm_response)
        elif st.session_state.mode == ct.ANSWER_MODE_2:
            content = cn.display_contact_llm_response(llm_response)
        else:
            content = cn.display_search_llm_response(llm_response)
        # contentがdict型の場合はstr型に変換してからstrip()
        content_str = content if isinstance(content, str) else str(content)
        has_rag = bool(content_str and str(content_str).strip())

        if has_keyword:
            st.markdown("#### 🔍 キーワード一致による全文検索結果")
            for doc in keyword_results:
                st.expander(f"{doc.metadata.get('source', '')}").write(doc.page_content)

        if has_rag:
            st.markdown("#### 🤖 AIによる要約・回答")
            st.markdown(content_str)
        if not has_keyword and not has_rag:
            st.warning("入力内容と関連する社内文書・AI回答が見つかりませんでした。入力内容を変更してください。", icon="⚠️")
            content = "入力内容と関連する社内文書・AI回答が見つかりませんでした。"
        logger.info({"message": content, "application_mode": st.session_state.mode})
    except Exception as e:
        import traceback
        tb_str = traceback.format_exc()
        logger.error(f"{ct.DISP_ANSWER_ERROR_MESSAGE}\n{e}\n{tb_str}")
        st.error(f"エラー詳細:\n{type(e).__name__}: {e}\n\n{tb_str}", icon=ct.ERROR_ICON)
        st.stop()


    # 10-4. アシスタントの回答表示（全文検索＋RAGハイブリッド）

    with st.chat_message("assistant"):
        try:
            # まず全文検索結果を表示
            has_keyword = bool(keyword_results)
            has_rag = False
            if st.session_state.mode == ct.ANSWER_MODE_1:
                content = cn.display_search_llm_response(llm_response)
            elif st.session_state.mode == ct.ANSWER_MODE_2:
                content = cn.display_contact_llm_response(llm_response)
            else:
                content = cn.display_search_llm_response(llm_response)
            # contentがdict型の場合はstr型に変換してからstrip()
            if isinstance(content, dict):
                content_str = str(content)
            else:
                content_str = content
            has_rag = bool(content_str and str(content_str).strip())

            if has_keyword:
                st.markdown("#### 🔍 キーワード一致による全文検索結果")
                for doc in keyword_results:
                    st.expander(f"{doc.metadata.get('source', '')}").write(doc.page_content)

            if has_rag:
                st.markdown("#### 🤖 AIによる要約・回答")
                st.markdown(content)
            if not has_keyword and not has_rag:
                st.warning("入力内容と関連する社内文書・AI回答が見つかりませんでした。入力内容を変更してください。", icon="⚠️")
                content = "入力内容と関連する社内文書・AI回答が見つかりませんでした。"
            logger.info({"message": content, "application_mode": st.session_state.mode})
         import traceback
            tb_str = traceback.format_exc()
            logger.error(f"{ct.DISP_ANSWER_ERROR_MESSAGE}\n{e}\n{tb_str}")
            st.error(f"エラー詳細:\n{type(e).__name__}: {e}\n\n{tb_str}", icon=ct.ERROR_ICON)
            st.stop()
        except Exception as e:
           

    # 10-5. 会話ログに追加
    st.session_state.messages.append({"role": "user", "content": user_text})
    st.session_state.messages.append({"role": "assistant", "content": content})
