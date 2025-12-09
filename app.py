import streamlit as st
import ezdxf
import io
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

# --- 設定：ページレイアウトを広めに ---
st.set_page_config(layout="wide", page_title="🧩 Living Hinge Generator v5")

def clip_line_to_height(p1, p2, height):
    """
    線分(p1-p2)がy=0またはy=heightの境界を超える場合、境界線で切り取った新しい座標を返す。
    完全に範囲外の場合は None を返す。
    """
    x1, y1 = p1
    x2, y2 = p2

    # 完全に範囲外
    if (y1 < 0 and y2 < 0) or (y1 > height and y2 > height):
        return None, None

    # y1のクリッピング
    if y1 < 0:
        if y2 != y1: x1 = x1 + (x2 - x1) * (0 - y1) / (y2 - y1)
        y1 = 0
    elif y1 > height:
        if y2 != y1: x1 = x1 + (x2 - x1) * (height - y1) / (y2 - y1)
        y1 = height

    # y2のクリッピング
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
    
    # 1. 外枠
    if include_frame:
        msp.add_lwpolyline([(0, 0), (width, 0), (width, height), (0, height), (0, 0)])
    
    # 2. パターン生成
    current_x = separation
    row_count = 0
    
    # ループ回数の安全装置（無限ループ防止）
    max_cols = int(width / separation) + 2
    
    for _ in range(max_cols):
        if current_x > width - separation:
            break

        # 偶数行・奇数行のYシフト
        if row_count % 2 == 0:
            y_shift = 0
        else:
            y_shift = -(cut_length + gap) / 2
            
        current_y = y_shift
        
        # Y方向のループ（安全装置付き）
        max_rows = int(height / (cut_length + gap)) + 3
        
        for _ in range(max_rows):
            if current_y > height:
                break

            p_start_y = current_y + gap
            p_mid_y = p_start_y + cut_length / 2
            p_end_y = p_start_y + cut_length

            # 描画対象チェック
            if p_end_y > 0:
                lines_to_draw = []

                if pattern_type == "直線 (Basic Straight)":
                    lines_to_draw.append(((current_x, p_start_y), (current_x, p_end_y)))

                elif pattern_type == "ひし形 (Chevron/V-cut)":
                    # V字の頂点計算
                    # current_x を中心として、左右に cut_width / 2 ずつ振る
                    P_top_L = (current_x - cut_width / 2, p_start_y)
                    P_top_R = (current_x + cut_width / 2, p_start_y)
                    P_mid   = (current_x, p_mid_y)
                    P_btm_L = (current_x - cut_width / 2, p_end_y)
                    P_btm_R = (current_x + cut_width / 2, p_end_y)
                    
                    lines_to_draw = [
                        (P_top_L, P_mid), # 上V 左
                        (P_top_R, P_mid), # 上V 右
                        (P_btm_L, P_mid), # 下V 左
                        (P_btm_R, P_mid)  # 下V 右
                    ]
                
                # 線分のクリッピングと描画
                for p1, p2 in lines_to_draw:
                    cp1, cp2 = clip_line_to_height(p1, p2, height)
                    if cp1 is not None and cp2 is not None:
                        # 長さがほぼ0のゴミデータを除外
                        if (cp1[0]-cp2[0])**2 + (cp1[1]-cp2[1])**2 > 0.001:
                            msp.add_line(cp1, cp2)

            current_y += cut_length + gap
            
        current_x += separation
        row_count += 1
        
    return doc

def draw_preview(doc):
    fig, ax = plt.subplots(figsize=(10, 6)) 
    ax.set_aspect('equal') 
    ax.axis('on')
    ax.set_title("プレビュー", fontsize=10)
    
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    frontend = Frontend(ctx, out)
    frontend.draw_layout(doc.modelspace(), finalize=True)
    ax.autoscale_view() 
    return fig

# --- Streamlit UI ---
st.title("🧩 リビングヒンジ DXFジェネレーター")
st.markdown("ダイヤモンドパターンでもバラバラにならないよう、パラメータの安全範囲を確認できます。")

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🛠️ パラメータ設定")
    
    pattern_type = st.selectbox(
        "スリット形状",
        ["直線 (Basic Straight)", "ひし形 (Chevron/V-cut)"],
        index=1
    )
    
    st.markdown("---")
    
    st.markdown("#### 📐 全体サイズ")
    w = st.number_input("全体の幅 (mm)", value=100.0, step=1.0)
    h = st.number_input("全体の高さ (mm)", value=50.0, step=1.0)
    include_frame = st.checkbox("外枠を含める", value=True)
    
    st.markdown("#### 📏 パターン詳細")
    
    # 1. 最初に「列の間隔」を決める（これが基準になるため）
    separation = st.number_input("列の間隔 (Pitch X) (mm)", value=3.0, step=0.5, min_value=1.0, help="列と列の中心距離。これが広いほど強度が上がり、狭いほど柔軟になります。")

    # 2. V字幅の計算と制限表示
    # 安全のため、V字幅は「列間隔 × 1.8」程度以内に抑えないと、隣のV字と重なりすぎて強度が落ちる
    safe_max_width = separation * 1.8
    warning_msg = ""
    
    cut_width = 0.0
    if pattern_type == "ひし形 (Chevron/V-cut)":
        st.markdown(f"**推奨V字幅:** {safe_max_width:.1f} mm 以下")
        cut_width = st.number_input(
            "V字の横幅 (mm)", 
            value=min(2.0, safe_max_width), # 初期値も安全圏に
            step=0.1, 
            min_value=0.1
        )
        
        # 警告ロジック
        if cut_width > separation * 2.0:
            st.error("⚠️ **危険:** V字幅が広すぎます！カット線が交差し、素材が脱落する可能性があります。")
        elif cut_width > safe_max_width:
            st.warning("⚠️ **注意:** V字幅が広めです。隣の列と近接しています。")
        else:
            st.success("✅ 強度的に安全な範囲です。")
    
    cut_len = st.number_input("カット長 (Length) (mm)", value=30.0, step=0.5)
    gap = st.number_input("ブリッジ幅 (Gap Y) (mm)", value=3.0, step=0.1, min_value=0.5, help="縦方向のつなぎ目。これが小さすぎると切れてしまいます。")

    # 生成処理
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
        st.error(f"エラー: {e}")
        doc = None

with col2:
    st.markdown("### 🖼️ プレビュー")
    if doc:
        try:
            fig = draw_preview(doc)
            st.pyplot(fig)
            if pattern_type == "ひし形 (Chevron/V-cut)":
                st.caption(f"ℹ️ ヒント: プレビューで線が密集して黒くなっている場合は、V字幅を小さくするか、列の間隔を広げてください。")
        except Exception as e:
            st.error(f"プレビュー描画エラー: {e}")
