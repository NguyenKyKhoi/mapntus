"""
Thuật toán Dijkstra tìm đường ngắn nhất trong khuôn viên NTU.

Cách chạy (VS Code: bấm nút ▷ Run, hoặc dùng Terminal):
    python ThuatToan_dijkstra_ntu.py                                  -> chạy ví dụ mặc định
    python ThuatToan_dijkstra_ntu.py "Giảng đường G1" "Thư viện 3"    -> chọn điểm đi / điểm đến theo tên

Cài thư viện (một lần): pip install networkx pandas shapely
"""
import json
import math
import sys
import unicodedata
from pathlib import Path

import networkx as nx
import pandas as pd
from shapely.wkt import loads

# ---- 1. Đường dẫn tính theo VỊ TRÍ FILE .py (không phụ thuộc thư mục đang đứng) ----
BASE = Path(__file__).resolve().parent.parent          # = Bai_Tap_Nhom
CSV_PATH = BASE / "duoi_CSV" / "NTU_DuongDi_WKT.csv"
ROAD_GEOJSON = BASE / "duoi_Geojson" / "NTU_DuongDi.geojson"
BUILDING_GEOJSON = BASE / "duoi_Geojson" / "NTU_ToaNha.geojson"
UTILITY_GEOJSON = BASE / "duoi_Geojson" / "NTU_TienIch.geojson"
OUT_PATH = BASE / "KetQua" / "ket_qua_duong_ngan_nhat.geojson"   # kết quả để riêng, không lẫn dữ liệu gốc

BRIDGE_TOL_M = 3.0      # nối các chỗ hở giữa 2 đoạn đường nếu cách nhau <= 3 mét
WALK_M_PER_MIN = 80     # tốc độ đi bộ ước tính (mét/phút)


# ---- 2. Hàm hình học ----
def dist_m(p1, p2):
    """Khoảng cách theo mét. Nếu toạ độ là kinh/vĩ độ -> Haversine, nếu là hệ mét -> Euclid."""
    x1, y1, x2, y2 = p1[0], p1[1], p2[0], p2[1]
    if abs(x1) <= 180 and abs(y1) <= 90 and abs(x2) <= 180 and abs(y2) <= 90:
        r, rad = 6371000.0, math.pi / 180
        dlat, dlng = (y2 - y1) * rad, (x2 - x1) * rad
        h = math.sin(dlat / 2) ** 2 + math.cos(y1 * rad) * math.cos(y2 * rad) * math.sin(dlng / 2) ** 2
        return 2 * r * math.asin(math.sqrt(h))
    return math.hypot(x2 - x1, y2 - y1)


def project_on_segment(p, a, b):
    """Hình chiếu điểm p lên đoạn a-b (xấp xỉ phẳng cục bộ, đủ chính xác trong khuôn viên)."""
    kx = math.cos(math.radians(p[1]))
    ax, ay, bx, by, px, py = a[0] * kx, a[1], b[0] * kx, b[1], p[0] * kx, p[1]
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0 if l2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / l2))
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def iter_lines(geom):
    """Trả về từng LineString, hỗ trợ cả MultiLineString."""
    if geom.geom_type == "LineString":
        yield geom
    elif geom.geom_type == "MultiLineString":
        yield from geom.geoms


def add_line(G, coords):
    # làm tròn 7 chữ số để các đầu mút trùng nhau thì nối được
    coords = [(round(c[0], 7), round(c[1], 7)) for c in coords]
    for a, b in zip(coords[:-1], coords[1:]):
        if a != b:
            G.add_edge(a, b, weight=dist_m(a, b))


# ---- 3. Dựng đồ thị đường đi ----
def build_graph():
    G = nx.Graph()
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        print(f"[CSV] Đọc {len(df)} dòng từ {CSV_PATH.name}")
        wkt_col = next(
            (c for c in df.columns
             if df[c].astype(str).str.upper().str.contains("LINESTRING", na=False).any()),
            None,
        )
        if wkt_col is None:
            print("[CSV] ⚠ CSV không có cột hình học WKT (LINESTRING). Các cột hiện có:")
            print("      ", list(df.columns))
            print("[CSV] -> chuyển sang đọc GeoJSON (file web đang dùng).")
        else:
            print(f"[CSV] Cột hình học: '{wkt_col}'")
            for s in df[wkt_col].dropna().astype(str):
                if "LINESTRING" not in s.upper():
                    continue
                try:
                    for line in iter_lines(loads(s)):
                        add_line(G, line.coords)
                except Exception as e:
                    print("  bỏ qua dòng lỗi WKT:", e)

    # Không có CSV, hoặc CSV không dùng được -> đọc GeoJSON
    if G.number_of_edges() == 0:
        if not ROAD_GEOJSON.exists():
            raise FileNotFoundError(f"Không tìm thấy dữ liệu đường: {CSV_PATH} hoặc {ROAD_GEOJSON}")
        print(f"[GeoJSON] Đọc {ROAD_GEOJSON.name}")
        data = json.loads(ROAD_GEOJSON.read_text(encoding="utf-8"))
        for f in data["features"]:
            g = f.get("geometry")
            if not g:
                continue
            if g["type"] == "LineString":
                add_line(G, g["coordinates"])
            elif g["type"] == "MultiLineString":
                for part in g["coordinates"]:
                    add_line(G, part)
    return G


def bridge_gaps(G, tol_m=BRIDGE_TOL_M):
    """Nối các chỗ hở nhỏ: đầu một đường chạm gần (nhưng không chung đỉnh với) giữa một đường khác."""
    joined, pad = 0, 0.0001   # pad ~ 11 m, dùng để lọc nhanh theo khung bao
    while True:
        comp_of = {n: i for i, c in enumerate(nx.connected_components(G)) for n in c}
        edges = list(G.edges())
        best = None
        for n in G.nodes:
            for a, b in edges:
                if comp_of[a] == comp_of[n]:
                    continue
                if (n[0] < min(a[0], b[0]) - pad or n[0] > max(a[0], b[0]) + pad
                        or n[1] < min(a[1], b[1]) - pad or n[1] > max(a[1], b[1]) + pad):
                    continue
                q = project_on_segment(n, a, b)
                d = dist_m(n, q)
                if d <= tol_m and (best is None or d < best[0]):
                    best = (d, n, q, a, b)
        if best is None:
            return joined
        d, n, q, a, b = best
        q = (round(q[0], 7), round(q[1], 7))
        if dist_m(q, a) < 0.05:
            target = a
        elif dist_m(q, b) < 0.05:
            target = b
        else:                                   # chia đôi đoạn đường tại điểm chạm
            target = q
            G.remove_edge(a, b)
            G.add_edge(a, q, weight=dist_m(a, q))
            G.add_edge(q, b, weight=dist_m(q, b))
        G.add_edge(n, target, weight=d)
        joined += 1


# ---- 4. Địa điểm (tòa nhà + tiện ích) ----
def norm(s):
    return unicodedata.normalize("NFC", str(s)).casefold().strip()


def centroid(geom):
    pts = []

    def walk(c):
        if isinstance(c[0], (int, float)):
            pts.append(c)
        else:
            for x in c:
                walk(x)

    walk(geom["coordinates"])
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def load_places():
    """Đọc tên + tâm của tòa nhà (cột 'name') và tiện ích (cột 'Ten_TienIch')."""
    places = []
    for path, key in ((BUILDING_GEOJSON, "name"), (UTILITY_GEOJSON, "Ten_TienIch")):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for f in data["features"]:
            name = (f.get("properties") or {}).get(key)
            if name and f.get("geometry"):
                places.append((name, centroid(f["geometry"])))
    return places


def find_place(places, query):
    q = norm(query)
    hits = [p for p in places if norm(p[0]) == q] or [p for p in places if q in norm(p[0])]
    if not hits:
        goi_y = ", ".join(sorted({p[0] for p in places})[:12])
        raise ValueError(f"Không tìm thấy địa điểm '{query}'. Ví dụ tên có sẵn: {goi_y} ...")
    return hits[0]


def nearest_node(G, point):
    return min(G.nodes, key=lambda n: dist_m(n, point))


# ---- 5. Chạy chương trình ----
def main():
    G = build_graph()
    print(f"Đồ thị ban đầu: {G.number_of_nodes()} nút, {G.number_of_edges()} cạnh, "
          f"{nx.number_connected_components(G)} mảnh rời")

    joined = bridge_gaps(G)
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    print(f"Đã nối {joined} chỗ hở nhỏ (<= {BRIDGE_TOL_M} m). Còn {len(comps)} mảnh liên thông"
          + ("  ✔" if len(comps) == 1 else f" (chỉ dùng mảnh lớn nhất {len(comps[0])} nút; "
                                           f"{len(comps) - 1} đoạn rời nhỏ bị bỏ qua)"))
    giant = G.subgraph(comps[0]).copy()

    places = load_places()
    if not places:
        raise FileNotFoundError("Không đọc được NTU_ToaNha.geojson / NTU_TienIch.geojson trong duoi_Geojson")
    q_start, q_end = (sys.argv[1], sys.argv[2]) if len(sys.argv) >= 3 else ("Giảng đường G1", "Thư viện 3")
    s_name, s_pt = find_place(places, q_start)
    e_name, e_pt = find_place(places, q_end)

    s_node, e_node = nearest_node(giant, s_pt), nearest_node(giant, e_pt)
    path = nx.dijkstra_path(giant, s_node, e_node, weight="weight")
    length = nx.dijkstra_path_length(giant, s_node, e_node, weight="weight")
    total = length + dist_m(s_pt, s_node) + dist_m(e_pt, e_node)   # cộng đoạn từ cửa tòa nhà ra đường

    print(f"\n--- KẾT QUẢ DIJKSTRA ---\nTừ: {s_name}\nĐến: {e_name}")
    print(f"Số nút trên tuyến: {len(path)}")
    print(f"Chiều dài: {total:.0f} m (~{math.ceil(total / WALK_M_PER_MIN)} phút đi bộ)")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature",
             "properties": {"from": s_name, "to": e_name, "length_m": round(total, 1)},
             "geometry": {"type": "LineString", "coordinates": [list(p) for p in path]}},
            {"type": "Feature", "properties": {"role": "start", "name": s_name},
             "geometry": {"type": "Point", "coordinates": list(s_pt)}},
            {"type": "Feature", "properties": {"role": "end", "name": e_name},
             "geometry": {"type": "Point", "coordinates": list(e_pt)}},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    print("Đã lưu tuyến vào:", OUT_PATH)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("LỖI:", e)