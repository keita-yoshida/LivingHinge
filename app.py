import streamlit as st
import ezdxf
import io
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

# --- 設定 ---
st.set_page_config(layout="wide", page_title="Living Hinge Generator v6")

def clip_line_to_height(p1, p2, height):
    """
    線分(p1-p2)が描画範囲（y=0〜height）からはみ出る場合、
    境界線でカットした座標を返す関数。
    """
    x1, y1 = p1
    x2, y2 = p2

    # 1. 完全に範囲外の場合は描画しない
    if (y1 < 0 and y2 < 0) or (y1 > height and y2 > height):
        return None, None

    # 2. 始点(y1)のクリッピング
    if y1 < 0:
        if y2 != y1: x1 = x1 + (x2 - x1) * (0 - y1) / (y2 - y1)
        y1 = 0
    elif y1 > height:
        if y2 != y1: x1 = x1 + (x2 - x1) * (height - y1) / (y2 - y1)
        y1 = height

    # 3. 終点(y2)のクリッピング
    if y2 < 0:
        if y2 != y1: x2 = x1 + (x2 - x1) * (0 - y1) / (y2 - y1)
        y2 = 0
    elif y2 > height:
        if y2 != y1: x2 = x1 + (x2 - x1) * (height - y1) / (y2 - y1)
        y2 = height
        
    return (x1, y1), (x2, y2)

def generate_hinge_dxf(width, height, cut_length, gap, separation, cut_width, include_frame, pattern_type):
    doc = ezdxf.new()
    msp = doc.modelspace()
    
    # --- 外枠 ---
    if include_frame:
        msp.add_lwpolyline([(0, 0), (width, 0), (width, height), (0, height), (0, 0)])
    
    # --- 安全装置：無限ループ防止と範囲チェック ---
    # 列数が極端に多くなるのを防ぐ
    if separation < 0.5: separation = 0.5
    
    current_x = separation
    col_index = 0
    
    while current_x <= width - separation + 0.01: # 浮動小数点誤差対策
        
        # 偶数列・奇数列のYシフト
        if col_index % 2 == 0:
            y_shift = 0
        else:
            y_shift = -(cut_length + gap) / 2
            
        current_y = y_shift
        
        # Y方向ループ
        while current_y < height:
            p_start_y = current_y + gap
            p_mid_y = p_start_y + cut_length / 2
            p_end_y = p_start_y + cut_length

            # Y座標が少しでも描画範囲にかかっていれば処理
            if p_end_y > 0 and p_start_y < height:
                
                lines = []
                if pattern_type == "直線 (Basic Straight)":
                    lines.append(((current_x, p_start_y), (current_x, p_end_y)))

                elif pattern_type == "ひし形 (Chevron/V-cut)":
                    # 中心(current_x)から左右に振る
                    w_half = cut_width / 2
                    
                    # 4本の線分を定義
                    P_top_L = (current_x - w_half, p_start_y)
                    P_top_R = (current_x + w_half, p_start_y)
                    P_mid   = (current_x, p_mid_y)
                    P_btm_L = (current_x - w_half, p_end_y)
                    P_btm_R = (current_x + w_half, p_end_y)
                    
                    lines = [
                        (P_top_L, P_mid), (P_top_R, P_mid),
                        (P_btm_L, P_mid), (P_btm_R, P_mid)
                    ]
                
                # クリッピングと描画
                for p1, p2 in lines:
                    cp1, cp2 = clip_line_to_height(p1, p2, height)
                    if cp1 is not None and cp2 is not None:
                        # ゴミデータ除去
                        if abs(cp1[0]-cp2[0]) > 1e-4 or abs(cp1[1]-cp2[1]) > 1e-4:
                            msp.add_line(cp1, cp2)

            current_y += cut_length + gap
            
        current_x += separation
        col_index += 1
        
    return doc

def draw_preview(doc):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_aspect('equal')
    ax.axis('on')
    # 背景色を少しグレーにして、白線を見やすくする（CAD風）
    ax.set_facecolor('#222222') 
    
    ctx = RenderContext(doc)
    # 線を白く表示する設定
    out = MatplotlibBackend(ax)
    frontend = Frontend(ctx, out)
    frontend.draw_layout(doc.modelspace(), finalize=True)
    
    ax.autoscale_view()
    return fig

# --- UI ---
st.title("🧩 リビングヒンジ DXFジェネレーター")

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🛠️ パラメータ設定")
    
    pattern_type = st.selectbox("スリット形状", ["直線 (Basic Straight)", "ひし形 (Chevron/V-cut)"], index=1)
    
    st.markdown("#### 📐 全体サイズ")
    w = st.number_input("全体の幅 (mm)", value=100.0, step=1.0)
    h = st.number_input("全体の高さ (mm)", value=50.0, step=1.0)
    include_frame = st.checkbox("外枠を含める", value=True)
    
    st.markdown("---")
    st.markdown("#### 📏 パターン詳細")
    
    # 1. 列の間隔（これが基準）
    separation = st.number_input("列の間隔 (Pitch X) (mm)", value=3.0, step=0.5, min_value=1.0)

    # 2. V字幅の設定（厳格なチェック付き）
    cut_width = 0.0
    safe_margin = 0.5 # 最小限残すべき隙間(mm)
    limit_width = separation - 0.2 # 物理的限界（少し余裕を持たせる）

    if pattern_type == "ひし形 (Chevron/V-cut)":
        # ガイドメッセージ
        st.caption(f"推奨: {separation - safe_margin:.2f} mm 以下 （列間隔 {separation}mm より小さくしてください）")
        
        cut_width = st.number_input(
            "V字の横幅 (mm)", 
            value=min(2.5, separation - safe_margin), # 初期値を安全圏に強制
            step=0.1, 
            min_value=0.1
        )
        
        # エラー判定ロジック
        if cut_width >= separation:
            st.error(f"⛔ **エラー:** V字幅({cut_width}mm)が列間隔({separation}mm)以上です。隣の列と重なり、バラバラになります。値を小さくしてください。")
            doc = None # 生成しない
        elif cut_width > separation - safe_margin:
            st.warning(f"⚠️ **注意:** 隙間がほとんどありません。素材によっては焼き切れて繋がってしまう可能性があります。")
            doc = generate_hinge_dxf(w, h, 30.0, 3.0, separation, cut_width, include_frame, pattern_type)
        else:
            st.success("✅ 強度的に安全な範囲です。")
            doc = generate_hinge_dxf(w, h, 30.0, 3.0, separation, cut_width, include_frame, pattern_type)
            
    else:
        # 直線の場合は常に生成
        doc = generate_hinge_dxf(w, h, 30.0, 3.0, separation, 0, include_frame, pattern_type)

    # 共通パラメータ（下部に移動）
    cut_len = st.number_input("カット長 (Length) (mm)", value=30.0, step=0.5)
    gap = st.number_input("ブリッジ幅 (Gap Y) (mm)", value=3.0, step=0.1)
    
    # ダウンロードボタン
    if doc:
        out = io.StringIO()
        doc.write(out)
        st.download_button(
            label="📥 DXFをダウンロード",
            data=out.getvalue(),
            file_name=f"hinge.dxf",
            mime="application/dxf",
            use_container_width=True
        )

with col2:
    st.markdown("### 🖼️ プレビュー")
    if doc:
        try:
            fig = draw_preview(doc)
            st.pyplot(fig)
        except Exception as e:
            st.error(f"描画エラー: {e}")
    else:
        st.info("👈 左側のエラーを解消するとプレビューが表示されます。")
