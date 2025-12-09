import streamlit as st
import ezdxf
import io

def generate_hinge_dxf(width, height, cut_length, gap, separation):
    """
    width: 全体の幅
    height: 全体の高さ
    cut_length: カット線の長さ
    gap: 同じ列のカット線同士の隙間（ブリッジ）
    separation: 列と列の間隔
    """
    doc = ezdxf.new()
    msp = doc.modelspace()
    
    # 外枠を描画
    msp.add_lwpolyline([(0, 0), (width, 0), (width, height), (0, height), (0, 0)])
    
    # ヒンジパターンの生成
    current_x = separation
    row_count = 0
    
    while current_x < width - separation:
        # 偶数行と奇数行でYの開始位置をずらす（互い違いにするため）
        if row_count % 2 == 0:
            current_y = 0
        else:
            current_y = -(cut_length + gap) / 2 # 半分ずらす
            
        while current_y < height:
            # カット線を描画（Y軸方向に線を引く場合）
            start_point = (current_x, max(0, current_y)) # 0未満にならないように
            end_point = (current_x, min(height, current_y + cut_length)) # 高さ超えないように
            
            # 有効な長さがある場合のみ線を追加
            if start_point[1] < end_point[1]:
                msp.add_line(start_point, end_point)
            
            current_y += cut_length + gap
            
        current_x += separation
        row_count += 1
        
    return doc

# --- Streamlit UI ---
st.title("リビングヒンジ DXFジェネレーター")

# ユーザー入力
w = st.number_input("幅 (mm)", value=100.0)
h = st.number_input("高さ (mm)", value=50.0)
cut_len = st.number_input("カット長 (mm)", value=30.0)
gap_len = st.number_input("ブリッジ幅 (mm)", value=3.0)
sep_len = st.number_input("列の間隔 (mm)", value=1.5)

if st.button("DXFを生成"):
    doc = generate_hinge_dxf(w, h, cut_len, gap_len, sep_len)
    
    # メモリバッファに保存してダウンロードボタンを表示
    out = io.StringIO()
    doc.write(out)
    st.download_button(
        label="DXFをダウンロード",
        data=out.getvalue(),
        file_name="living_hinge.dxf",
        mime="application/dxf"
    )
