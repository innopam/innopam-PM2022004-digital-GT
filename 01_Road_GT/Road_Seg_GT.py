import geopandas as gpd
import pandas as pd

def road_seg_gt(input_file_v1, input_file_v2, output_file):

    # 도로종류 매핑
    road_type = {
        'A0023119': '소로',
        'A0023210': '미분류',
        'A0023211': '고속국도',
        'A0023212': '일반국도',
        'A0023213': '지방도',
        'A0023214': '특별시도•광역시도',
        'A0023215': '시도',
        'A0023216': '군도',
        'A0023217': '면리간도로'
    }

    # 도면층 코드를 기반으로 도로종류를 매핑
    def get_road_type(layer_code):
        return road_type.get(layer_code, '기타')

    # ‘Digital_Map_v1.0.shp’과 ‘Digital_Map_v2.0.shp’ 불러오기
    digital_map_v1 = gpd.read_file(input_file_v1)  # 도로 수치지도 v1.0 (라인 레이어)
    digital_map_v2 = gpd.read_file(input_file_v2)  # 도로 수치지도 v2.0 (폴리곤 레이어)

    # 좌표계 설정 (EPSG:5186)
    if digital_map_v1.crs is None:
        digital_map_v1.set_crs(epsg=5186, inplace=True)
    if digital_map_v2.crs is None:
        digital_map_v2.set_crs(epsg=5186, inplace=True)

    # ‘Digital_Map_v1.0.shp’에 ‘도로종류’ 컬럼 추가
    digital_map_v1['도로종류'] = digital_map_v1['도면층'].apply(get_road_type)

    # ‘intersects’ 조건으로 ‘Digital Map_v2.0’과 ‘Digital Map_v1.0’을 공간 조인
    intersect_joined = gpd.sjoin(digital_map_v2, digital_map_v1, how='left', predicate='intersects')

    # ‘crosses’ 조건으로 ‘Digital Map_v2.0’과 ‘Digital Map_v1.0’을 공간 조인
    crosses_joined = gpd.sjoin(digital_map_v2, digital_map_v1, how='left', predicate='crosses')

    # 두 조인 결과를 결합하고 중복된 지오메트리 제거
    combined = pd.concat([intersect_joined, crosses_joined]).drop_duplicates(subset=['geometry'])

    # 매칭되지 않은 경우 도로종류를 ‘NULL’로 설정
    if '도로종류' in combined.columns:
        combined['도로종류'] = combined['도로종류'].fillna('NULL')
    else:
        print("Warning: '도로종류' column not found in combined DataFrame.")

    # 필요한 열만 유지 ('UFID', '도면층', '도로종류')
    if 'UFID' in combined.columns:
        combined = combined[['UFID', '도면층', '도로종류', 'geometry']]
    else:
        combined = combined[['도면층', '도로종류', 'geometry']]

    # 열 이름을 10자 이하로 줄이기
    combined = combined.rename(columns=lambda x: x[:10])

    # 결과 저장 (EUC-KR 인코딩)
    combined.to_file(output_file, encoding='EUC-KR')