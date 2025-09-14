import glob
import pandas as pd
import streamlit as st
def load_all_staff_csv():
    dfs = []
    for path in glob.glob("./data/社員について/*.csv"):
        try:
            df = pd.read_csv(path)
            df["__source"] = path
            dfs.append(df)
        except Exception:
            pass
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

def render_hr_list_fixed():
    df_all = load_all_staff_csv()
    if df_all.empty:
        st.warning("社員名簿CSVを読み込めませんでした。パスや権限を確認してください。")
        return None

    rename_map = {
        "氏名（フルネーム）": "氏名",
        "メールアドレス": "メール",
    }
    df_all = df_all.rename(columns=rename_map)

    candidates = [c for c in df_all.columns if "部署" in c]
    dept_col = candidates[0] if candidates else None
    if not dept_col:
        st.warning("CSVに『部署』列が見つかりませんでした。列名をご確認ください。")
        return None

    df_hr = (
        df_all[df_all[dept_col] == "人事部"]
        .copy()
    )

    cols = [c for c in ["社員ID", "氏名", "部署", "役職", "メール", "__source"] if c in df_hr.columns]
    df_hr = df_hr[cols].drop_duplicates()

    st.write("### 人事部に所属している従業員一覧（フォールバック抽出）")
    if df_hr.empty:
        st.info("人事部のレコードが見つかりませんでした。CSVの内容をご確認ください。")
    else:
        st.dataframe(df_hr, use_container_width=True)
        st.download_button(
            "CSVをダウンロード",
            df_hr.to_csv(index=False),
            "hr_members.csv",
            "text/csv"
        )
    return df_hr
def crash_report(label, fn):
    import streamlit as st, traceback
    st.write(f"checkpoint: {label}")
    try:
        return fn()
    except Exception as e:
        st.error(f"[{label}] で例外発生")
        st.code(str(e))
        st.code("".join(traceback.format_exc()))
        raise
from typing import List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
def search_documents_by_keyword(keyword, docs_all, max_results=10):
    """
    指定キーワードで全ドキュメントから部分一致検索し、ヒットしたものを返す
    Args:
        keyword: 検索キーワード
        docs_all: 全ドキュメントリスト（Document型）
        max_results: 最大返却件数
    Returns:
        ヒットしたDocumentのリスト
    """
    results = []
    for doc in docs_all:
        if keyword in doc.page_content:
            results.append(doc)
            if len(results) >= max_results:
                break
    return results
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
    def get_chat_history_from_session() -> List[BaseMessage]:
        raw_hist = st.session_state.get("chat_history", [])
        hist: List[BaseMessage] = []
        for role, content in raw_hist:
            if role == "user":
                hist.append(HumanMessage(content=content))
            else:
                hist.append(AIMessage(content=content))
        return hist

    chat_history = get_chat_history_from_session()
    st.write(f"chat_history len: {len(chat_history)}")
    st.write(f"chat_history sample: {chat_history[:2]}")
    """
    LLMからの回答取得

    Args:
        chat_message: ユーザー入力値

    Returns:
        LLMからの回答
    """
    st.write("[get_llm_response] start")
    st.write("get_llm_response called")
    st.write("before llm init")
    llm = ChatOpenAI(model_name=ct.MODEL, temperature=ct.TEMPERATURE)
    st.write("after llm init")
    st.write("checkpoint: after llm init")

    # 会話履歴なしでもLLMに理解してもらえる、独立した入力テキストを取得するためのプロンプトテンプレートを作成
    # LangChain公式推奨の配線でプロンプトを作成
    from langchain_core.prompts import ChatPromptTemplate
    question_generator_prompt = crash_report(
        "question_generator_prompt",
        lambda: ChatPromptTemplate.from_messages([
            ("system", ct.SYSTEM_PROMPT_CREATE_INDEPENDENT_TEXT),
            ("human", "履歴: {chat_history}\n質問: {input}\n人事関連の同義語も考慮して検索クエリを作成してください。")
        ])
    )
    if st.session_state.mode == ct.ANSWER_MODE_1:
        question_answer_template = ct.SYSTEM_PROMPT_DOC_SEARCH
    else:
        question_answer_template = ct.SYSTEM_PROMPT_INQUIRY
    question_answer_prompt = crash_report(
        "question_answer_prompt",
        lambda: ChatPromptTemplate.from_messages([
            ("system", question_answer_template),
            ("human", "履歴: {chat_history}\n質問: {input}")
        ])
    )

    # 会話履歴なしでもLLMに理解してもらえる、独立した入力テキストを取得するためのRetrieverを作成
    st.write("before history_aware_retriever init")
    print("before history_aware_retriever init")
    st.write(f"llm is None: {llm is None}")
    print(f"llm is None: {llm is None}")
    try:
        st.write(f"retriever is None: {st.session_state.retriever is None}")
        print(f"retriever is None: {st.session_state.retriever is None}")
    except Exception as e:
        st.write(f"retrieverチェック例外: {e}")
        print(f"retrieverチェック例外: {e}")
    try:
        st.write(f"question_generator_prompt is None: {question_generator_prompt is None}")
        print(f"question_generator_prompt is None: {question_generator_prompt is None}")
    except Exception as e:
        st.write(f"promptチェック例外: {e}")
        print(f"promptチェック例外: {e}")
    # create_history_aware_retriever呼び出しを一時的にコメントアウト
    # デバッグ出力はここまで、本処理を有効化
    st.write(f"retriever type: {type(st.session_state.retriever)}")
    st.write(f"retriever sample: {str(st.session_state.retriever)[:300]}")
    st.write(f"question_generator_prompt type: {type(question_generator_prompt)}")
    st.write(f"question_generator_prompt sample: {str(question_generator_prompt)[:300]}")
    history_aware_retriever = create_history_aware_retriever(
        llm, st.session_state.retriever, question_generator_prompt
    )
    st.write("after history_aware_retriever init")

    # --- LangChain公式推奨の配線 ---
    from langchain_core.prompts import ChatPromptTemplate
    llm = crash_report("llm init", lambda: ChatOpenAI(model="gpt-4o-mini", temperature=0))
    question_generator_prompt = crash_report(
        "question_generator_prompt",
        lambda: ChatPromptTemplate.from_messages([
            ("system", "あなたは検索クエリを改善するアシスタントです。"),
            ("human", "履歴: {chat_history}\n質問: {input}\n人事関連の同義語も考慮して検索クエリを作成してください。")
        ])
    )
    history_aware_retriever = crash_report(
        "create_history_aware_retriever",
        lambda: create_history_aware_retriever(llm=llm, retriever=st.session_state.retriever, prompt=question_generator_prompt)
    )
    answer_prompt = crash_report(
        "answer_prompt",
        lambda: ChatPromptTemplate.from_messages([
            ("system",
             "あなたは人事データ抽出ボットです。以下の制約でCSVのみを出力：\n"
             "- 列: 社員ID, 氏名, 部署, 役職, メール\n"
             "- 部署が『人事部』のレコードのみ\n"
             "- ヘッダ1行 + データ行\n"
             "- 補完しない（不明は空欄）"),
            ("human", "質問: {input}\n参照コンテキスト:\n{context}")
        ])
    )
    question_answer_chain = crash_report(
        "create_stuff_documents_chain",
        lambda: create_stuff_documents_chain(llm, answer_prompt)
    )
    rag_chain = crash_report(
        "create_retrieval_chain",
        lambda: create_retrieval_chain(history_aware_retriever, question_answer_chain)
    )

    # LLMへのリクエストとレスポンス取得
    st.write("[get_llm_response] before chain.invoke")
    st.write(f"chat_message: {chat_message}")
    st.write(f"chat_history len: {len(chat_history)}")
    st.write(f"chat_history sample: {chat_history[:2]}")
    if hasattr(st.session_state, 'retriever') and hasattr(st.session_state.retriever, 'docs'):
        st.write(f"context docs len: {len(st.session_state.retriever.docs)}")
        st.write(f"context docs sample: {st.session_state.retriever.docs[:1]}")
    import traceback
    llm_response = crash_report(
        "rag_chain.invoke",
        lambda: rag_chain.invoke({"input": chat_message, "chat_history": chat_history})
    )
    st.write(f"[get_llm_response] llm_response: {llm_response}")
    # LLMレスポンスを会話履歴に追加（st.session_state.chat_historyはrole/content形式で管理）
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    st.session_state.chat_history.append(("user", chat_message))
    st.session_state.chat_history.append(("assistant", llm_response["answer"]))
    st.write("[get_llm_response] before return")
    return llm_response