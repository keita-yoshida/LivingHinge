import streamlit as st
import ezdxf
import io
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

# --- 設定：ページレイアウトを広めに ---
st.set_page_config(layout="wide", page_title="Living Hinge Generator")

def generate_hinge_dxf(width, height, cut_length, gap, separation):
    """
    DXFドキュメントを生成する関数
    """
    doc = ezdxf.new()
    msp = doc.modelspace()
    
    # --- 外枠を描画 ---
    # レーザー加工用に色を変える場合は dxfattribs={'color': 1} (赤) などを追加可能
    msp.add_lwpolyline([(0, 0), (width, 0), (width, height), (0, height), (0, 0)])
    
    # --- ヒンジパターンの生成 ---
    current_x = separation
    row_count = 0
    
    while current_x < width - separation:
        if row_count % 2 == 0:
            current_y = 0
        else:
            current_y = -(cut_length + gap) / 2
            
        while current_y < height:
            start_point = (current_x, max(0, current_y))
            end_point = (current_x, min(height, current_y + cut_length))
            
            if start_point[1] < end_point[1]:
                msp.add_line(start_point, end_point)
            
            current_y += cut_length + gap
            
        current_x += separation
        row_count += 1
        
    return doc

def draw_preview(doc):
    """
    ezdxfのデータをmatplotlibの図として描画する関数
    """
    msp = doc.modelspace()
    
    # グラフの設定
    fig, ax = plt.subplots()
    
    # 背景色や軸の設定（CADっぽく黒背景にするか、白背景にするか）
    ax.set_aspect('equal') # アスペクト比を固定（歪まないように）
    ax.axis('on') # 軸（目盛り）を表示してサイズ感を確認しやすくする
    
    # ezdxfの描画バックエンドをセットアップ
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    frontend = Frontend(ctx, out)
    
    # 描画実行
    frontend.draw_layout(msp, finalize=True)
    
    return fig

# --- Streamlit UI ---
st.title("🧩 Living Hinge Generator")

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### パラメータ設定")
    w = st.number_input("全体の幅 (mm)", value=100.0, step=1.0)
    h = st.number_input("全体の高さ (mm)", value=50.0, step=1.0)
    
    st.markdown("---")
    cut_len = st.number_input("カット長 (mm)", value=30.0, step=0.5, help="直線の切れ込みの長さ")
    gap_len = st.number_input("ブリッジ幅 (mm)", value=3.0, step=0.1, help="切れ込み同士の繋ぎ目（残る部分）")
    sep_len = st.number_input("列の間隔 (mm)", value=1.5, step
