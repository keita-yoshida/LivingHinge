import streamlit as st
import ezdxf
import io
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

# --- 設定：ページレイアウトを広めに ---
st.set_page_config(layout="wide", page_title="🧩 Living Hinge Generator")

def clip_line_to_height(p1, p2, height):
    """
    線分(p1-p2)がy=0またはy=heightの境界を超える場合、境界線で切り取った新しい座標を返す。
    完全に範囲外の場合は None を返す。
    """
    x1, y1 = p1
    x2, y2 = p2

    # 完全に範囲外（両方の端点が上すぎるか、下すぎる）
    if (y1 < 0 and y2 < 0) or (y1 > height and y2 > height):
        return None, None

    # y1が範囲外の場合のクリッピング
    if y1 < 0:
        x1 = x1 + (x2 - x1) * (0 - y1) / (y2 - y1)
        y1 = 0
    elif y1 > height:
        x1 = x1 + (x2 - x1) * (height - y1) / (y2 - y1)
        y1 = height

    # y2が範囲外の場合のクリッピング
    if y2 < 0:
        x2 = x1 + (x2 - x1) * (0 - y1) / (y2 - y1)
        y2 = 0
    elif y2 > height:
        x2 = x1 + (x2 - x1) * (height - y1) / (y2 - y1)
        y2 = height
        
    return (x1, y1), (x2, y2)


def generate_hinge_dxf(width, height, cut_length, gap, separation, cut_width, include_frame, pattern_type):
    """
    DXFドキュメントを生成する関数
    """
    doc = ezdxf.new()
    msp = doc.modelspace()
    
    # --- 1. 外枠の描画 (オン/オフ機能) ---
    if include_frame:
        msp.add_lwpolyline([(0, 0), (width, 0), (width, height), (0, height), (0, 0)])
    
    # --- 2. ヒンジパターンの生成 ---
    current_x = separation
    row_count = 0
    
    while current_x < width - separation:
        if row_count % 2 == 0:
            y_shift = 0
        else:
            y_shift = -(cut_length + gap) / 2
            
        current_y = y_shift
            
        while current_y < height:
            p_start_y = current_y + gap
            p_mid_y = p_start_y + cut_length / 2
            p_end_y = p_start_y + cut_length

            # 基本的な範囲チェック（完全に上すぎるものはスキップ）
            if p_end_y > 0:
                
                if pattern_type == "直線 (Basic Straight)":
                    # ------------------------------------
                    # A. 直線パターン (Y軸方向の単純クリッピング)
                    # ------------------------------------
                    sy = max(0, p_start_y)
                    ey = min(height, p_end_y)
                    
                    if sy < ey:
                        msp.add_line((current_x, sy), (current_x, ey))

                elif pattern_type == "ひし形 (Chevron/V-cut)":
                    # ------------------------------------
                    # B. ひし形パターン (斜め線のクリッピング)
                    # ------------------------------------
                    # 頂点の定義
                    P_top_L = (current_x - cut_width / 2, p_start_y)
                    P_top_R = (current_x + cut_width / 2, p_start_y)
                    P_mid = (current_x, p_mid_y)
                    P_btm_L = (current_x - cut_width / 2, p_end_y)
                    P_btm_R = (current_x + cut_width / 2, p_end_y)
                    
                    # 4本の斜線それぞれについて、はみ出しを計算して描画
                    lines_to_draw = [
                        (P_top_L, P_mid), # 上向きV 左
                        (P_top_R, P_mid), # 上向きV 右
                        (P_btm_L, P_mid), # 下向きV 左
                        (P_btm_R, P_mid)  # 下向きV 右
                    ]
                    
                    for p1, p2 in lines_to_draw:
                        # クリッピング関数を呼び出す
                        clipped_p1, clipped_p2 = clip_line_to_height(p1, p2, height)
                        # 有効な線分が返ってきたら描画
                        if clipped_p1 is not None and clipped_p2 is not None:
                            # ゼロ除算防止等のため、念のため長さチェック
                            if abs(clipped_p1[0] - clipped_p2[0]) > 1e-6 or abs(clipped_p1[1] - clipped_p2[1]) > 1e-6:
                                msp.add_line(clipped_p1, clipped_p2)

            current_y += cut_length + gap
            
        current_x += separation
        row_count += 1
        
    return doc

def draw_preview(doc):
    """
    ezdxfのデータをmatplotlibの図として描画する関数
    """
    # グラフの設定 (サイズを少し大きくしました)
    fig, ax = plt.subplots(figsize=(10, 6)) 
    
    ax.set_aspect('equal') 
    ax.axis('on')
    ax.set_title("プレビュー (寸法は目安)", fontsize=10)
    # Y軸の範囲を少し広げて、はみ出しがないか確認しやすくする
    # ax.set_ylim(ymin=-5, ymax=height+5) # 必要に応じてコメントアウト解除
    
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    frontend = Frontend(ctx, out)
    
    frontend.draw_layout(doc.modelspace(), finalize=True)
    ax.autoscale_view() 
    
    return fig

# --- Streamlit UI ---
st.title("🧩 リビングヒンジ DXFジェネレーター")

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🛠️ パラメータ設定")
    
    # --- 形状選択 ---
    pattern_type = st.selectbox(
        "スリット形状の選択",
        ["直線 (Basic Straight)", "ひし形 (Chevron/V-cut)"],
        index=1 # デフォルトをひし形に変更
    )
    
    st.markdown("---")
    
    # --- 全体サイズ ---
    st.markdown("#### 📐 全体サイズ")
    w = st.number_input("全体の幅 (mm)", value=100.0, step=1.0)
    h = st.number_input("全体の高さ (mm)", value=50.0, step=1.0)
    
    include_frame = st.checkbox("外枠のカットラインを含める", value=True)
    
    st.markdown("#### 📏 パターン詳細")
    
    # --- パターン共通 ---
    cut_len = st.number_input("カット長 (mm)", value=30.0, step=0.5)
    gap = st.number_input("ブリッジ幅 (mm)", value=3.0, step=0.1)
    separation = st.number_input("列の間隔 (mm)", value=1.5, step=0.1)
    
    # --- ひし形専用パラメータ ---
    cut_width = 0.0
    if pattern_type == "ひし形 (Chevron/V-cut)":
        cut_width = st.number_input("V字の横幅 (mm)", value=3.0, step=0.1) # デフォルト値を少し大きく
    
    
    # --- リアルタイム生成とダウンロード ---
    # エラーハンドリングを追加
    try:
        doc = generate_hinge_dxf(w, h, cut_len, gap, separation, cut_width, include_frame, pattern_type)
        
        out = io.StringIO()
        doc.write(out)
        st.download_button(
            label="📥 DXFをダウンロード",
            data=out.getvalue(),
            file_name=f"living_hinge_{pattern_type.split(' ')[0]}.dxf",
            mime="application/dxf",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"DXF生成エラー: {e}")
        doc = None # プレビュー用にNoneにする

with col2:
    st.markdown("### 🖼️ プレビュー")
    if doc:
        try:
            fig = draw_preview(doc)
            st.pyplot(fig)
            st.caption(f"描画サイズ: {w}mm x {h}mm")
        except Exception as e:
            st.error(f"プレビュー描画エラー: {e}")
