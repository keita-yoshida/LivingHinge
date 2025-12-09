import streamlit as st
import ezdxf
import io
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

# --- 設定：ページレイアウトを広めに ---
st.set_page_config(layout="wide", page_title="🧩 Living Hinge Generator")

def generate_hinge_dxf(width, height, cut_length, gap, separation, cut_width, include_frame, pattern_type):
    """
    DXFドキュメントを生成する関数
    """
    doc = ezdxf.new()
    msp = doc.modelspace()
    
    # --- 1. 外枠の描画 (オン/オフ機能) ---
    if include_frame:
        # 外枠のカットラインを追加
        msp.add_lwpolyline([(0, 0), (width, 0), (width, height), (0, height), (0, 0)])
    
    # --- 2. ヒンジパターンの生成 ---
    current_x = separation
    row_count = 0
    
    while current_x < width - separation:
        # 偶数行と奇数行でYの開始位置をずらす（互い違いにするため）
        if row_count % 2 == 0:
            y_shift = 0
        else:
            y_shift = -(cut_length + gap) / 2
            
        current_y = y_shift
            
        while current_y < height:
            
            # Y軸のブリッジ開始点を基準に、カットの開始/中間/終了点を計算
            p_start_y = current_y + gap
            p_mid_y = p_start_y + cut_length / 2
            p_end_y = p_start_y + cut_length

            # Y座標が描画範囲内にあるかチェック
            if p_mid_y > 0 and p_start_y < height:
                
                if pattern_type == "直線 (Basic Straight)":
                    # ------------------------------------
                    # A. 直線パターン
                    # ------------------------------------
                    start_point = (current_x, max(0, p_start_y))
                    end_point = (current_x, min(height, p_end_y))
                    
                    if start_point[1] < end_point[1]:
                        msp.add_line(start_point, end_point)

                elif pattern_type == "ひし形 (Chevron/V-cut)":
                    # ------------------------------------
                    # B. V字形パターン (上向きVと下向きVの組み合わせでひし形に)
                    # ------------------------------------
                    
                    # 1. 上向きV (^)
                    P_V1 = (current_x - cut_width / 2, p_start_y)
                    P_V2 = (current_x, p_mid_y)
                    P_V3 = (current_x + cut_width / 2, p_start_y)
                    
                    # 2. 下向きV (v)
                    P_V4 = (current_x - cut_width / 2, p_end_y)
                    P_V5 = (current_x, p_mid_y)
                    P_V6 = (current_x + cut_width / 2, p_end_y)
                    
                    # 上向きVのカット
                    if 0 <= P_V2[1] <= height:
                         msp.add_line(P_V1, P_V2) # 左斜め上
                         msp.add_line(P_V2, P_V3) # 右斜め上
                         
                    # 下向きVのカット
                    if 0 <= P_V5[1] <= height:
                         msp.add_line(P_V4, P_V5) # 左斜め下
                         msp.add_line(P_V5, P_V6) # 右斜め下
                    
            current_y += cut_length + gap
            
        current_x += separation
        row_count += 1
        
    return doc

def draw_preview(doc):
    """
    ezdxfのデータをmatplotlibの図として描画する関数
    """
    # グラフの設定
    fig, ax = plt.subplots(figsize=(8, 4)) # サイズ調整
    
    # アスペクト比を固定し、軸を表示
    ax.set_aspect('equal') 
    ax.axis('on')
    ax.set_title("プレビュー (寸法は目安)", fontsize=10)
    
    # ezdxfの描画バックエンドをセットアップ
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    frontend = Frontend(ctx, out)
    
    # 描画実行
    frontend.draw_layout(doc.modelspace(), finalize=True)
    
    # 描画範囲をデータ全体に合わせる
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
        index=0
    )
    
    st.markdown("---")
    
    # --- 全体サイズ ---
    st.markdown("#### 📐 全体サイズ")
    w = st.number_input("全体の幅 (mm)", value=100.0, step=1.0)
    h = st.number_input("全体の高さ (mm)", value=50.0, step=1.0)
    
    include_frame = st.checkbox("外枠のカットラインを含める", value=True, help="板の境界線（0,0からW,H）をカットするかどうか")
    
    st.markdown("#### 📏 パターン詳細")
    
    # --- パターン共通 ---
    cut_len = st.number_input("カット長 (mm)", value=30.0, step=0.5, help="切れ込みの長さ（Y軸方向）")
    gap = st.number_input("ブリッジ幅 (mm)", value=3.0, step=0.1, help="切れ込み同士の繋ぎ目（残る部分）")
    separation = st.number_input("列の間隔 (mm)", value=1.5, step=0.1, help="隣の列の中心までのX軸方向の間隔。狭いほど高密度に")
    
    # --- ひし形専用パラメータ ---
    cut_width = 0.0
    if pattern_type == "ひし形 (Chevron/V-cut)":
        cut_width = st.number_input("V字の横幅 (mm)", value=1.0, step=0.1, help="ひし形/V字カットのX軸方向の幅。これが狭いと角度が急になります。")
    
    
    # --- リアルタイム生成とダウンロード ---
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

with col2:
    st.markdown("### 🖼️ プレビュー")
    # プレビュー描画
    try:
        fig = draw_preview(doc)
        st.pyplot(fig)
        st.caption(f"描画サイズ: {w}mm x {h}mm")
    except Exception as e:
        st.error(f"プレビュー描画エラー: パラメータを確認してください。（エラー: {e}）")
