from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
def _to_base_messages(history):
    """[(user, ai)] / [("human", ...), ("ai", ...)] / BaseMessage[] / [{"role":..,"content":..}] をBaseMessage[]に正規化"""
    if not history:
        return []
    msgs = []
    for item in history:
        if isinstance(item, tuple) and len(item) == 2:
            a, b = item
            if a in ("human", "user"):
                msgs.append(HumanMessage(content=str(b)))
            elif a in ("ai", "assistant"):
                msgs.append(AIMessage(content=str(b)))
            elif a == "system":
                msgs.append(SystemMessage(content=str(b)))
            else:
                # 旧形式 (user, ai) を検出したら分解
                msgs.append(HumanMessage(content=str(a)))
                msgs.append(AIMessage(content=str(b)))
        elif isinstance(item, dict) and "role" in item and "content" in item:
            role = item["role"]
            content = item["content"]
            if role in ("human", "user"):
                msgs.append(HumanMessage(content=str(content)))
            elif role in ("ai", "assistant"):
                msgs.append(AIMessage(content=str(content)))
            elif role == "system":
                msgs.append(SystemMessage(content=str(content)))
        else:
            try:
                _ = item.type; _ = item.content
                msgs.append(item)
            except Exception:
                msgs.append(HumanMessage(content=str(item)))
    return msgs
"""
このファイルは、画面表示以外の様々な関数定義のファイルです。
"""

############################################################
# ライブラリの読み込み
############################################################
import os
from dotenv import load_dotenv
import streamlit as st
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
import constants as ct


############################################################
# 設定関連
############################################################
# 「.env」ファイルで定義した環境変数の読み込み
load_dotenv()


############################################################
# 関数定義
############################################################

def get_source_icon(source):
    """
    メッセージと一緒に表示するアイコンの種類を取得

    Args:
        source: 参照元のありか

    Returns:
        メッセージと一緒に表示するアイコンの種類
    """
    # 参照元がWebページの場合とファイルの場合で、取得するアイコンの種類を変える
    if source.startswith("http"):
        icon = ct.LINK_SOURCE_ICON
    else:
        icon = ct.DOC_SOURCE_ICON
    
    return icon


def build_error_message(message):
    """
    エラーメッセージと管理者問い合わせテンプレートの連結

    Args:
        message: 画面上に表示するエラーメッセージ

    Returns:
        エラーメッセージと管理者問い合わせテンプレートの連結テキスト
    """
    return "\n".join([message, ct.COMMON_ERROR_MESSAGE])


def get_llm_response(chat_message):
    """
    LLMからの回答取得

    Args:
        chat_message: ユーザー入力値

    Returns:
        LLMからの回答
    """
    # LLMのオブジェクトを用意
    llm = ChatOpenAI(model_name=ct.MODEL, temperature=ct.TEMPERATURE)

    # 会話履歴なしでもLLMに理解してもらえる、独立した入力テキストを取得するためのプロンプトテンプレートを作成
    question_generator_template = ct.SYSTEM_PROMPT_CREATE_INDEPENDENT_TEXT
    question_generator_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", question_generator_template),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ]
    )

    # モードによってLLMから回答を取得する用のプロンプトを変更
    if st.session_state.mode == ct.ANSWER_MODE_1:
        # モードが「社内文書検索」の場合のプロンプト
        question_answer_template = ct.SYSTEM_PROMPT_DOC_SEARCH
    else:
        # モードが「社内問い合わせ」の場合のプロンプト
        question_answer_template = ct.SYSTEM_PROMPT_INQUIRY
    # LLMから回答を取得する用のプロンプトテンプレートを作成
    question_answer_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", question_answer_template),
            MessagesPlaceholder("chat_history"),
            ("human", "{input}")
        ]
    )

    # 会話履歴なしでもLLMに理解してもらえる、独立した入力テキストを取得するためのRetrieverを作成
    history_aware_retriever = create_history_aware_retriever(
        llm, st.session_state.retriever, question_generator_prompt
    )

    # LLMから回答を取得する用のChainを作成
    question_answer_chain = create_stuff_documents_chain(llm, question_answer_prompt)
    # 「RAG x 会話履歴の記憶機能」を実現するためのChainを作成
    chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    # LLMへのリクエストとレスポンス取得
    history = st.session_state.get("chat_history", [])
    history = _to_base_messages(history)
    llm_response = chain.invoke({"input": chat_message, "chat_history": history})
    # LLMレスポンスを会話履歴に追加
    # （ここでのextendは不要なので削除）
    return llm_response