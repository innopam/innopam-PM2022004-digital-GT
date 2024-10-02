import os
import geopandas as gpd
import pandas as pd

# 셰이프 파일을 전처리하고 속성을 부여하는 함수
def preprocess_shapefile(shapefile_path, year):
    gdf = gpd.read_file(shapefile_path)
    gdf = gdf.to_crs(epsg=5186)
    gdf['Area'] = gdf['geometry'].area.round(2)
    gdf[f'{year}_ID'] = [f'{year}_{i + 1}' for i in range(len(gdf))]
    return gdf

# GeoDataFrame을 저장하고 좌표계가 설정되지 않았을 경우 처리하는 함수
def save_gdf(gdf, output_path, description, crs):
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if gdf.crs is None:
        gdf = gdf.set_crs(crs)
    gdf.to_file(output_path)
    print(f"{description} saved: {output_path}")

# 두 지오메트리의 대칭 차집합 면적을 계산하는 함수
def calculate_symmetric_area(geom1, geom2):
    return geom1.symmetric_difference(geom2).area

# 두 지오메트리의 합집합 면적을 계산하는 함수
def calculate_union_area(geom1, geom2):
    return geom1.union(geom2).area

# 객체 매칭 함수 - ID와 지오메트리 교차를 기반으로 매칭
def object_matching(gdf_2020, gdf_2022, output_dir, location, crs):
    # 0:1 (신축된 건물) 처리
    new_buildings = gdf_2022[~gdf_2022.intersects(gdf_2020.geometry.union_all())]
    save_gdf(new_buildings, os.path.join(output_dir, f"{location}_GT_2022_0_1.shp"), "New buildings", crs)

    # 1:0 (소멸된 건물) 처리
    demolished_buildings = gdf_2020[~gdf_2020.intersects(gdf_2022.geometry.union_all())]
    save_gdf(demolished_buildings, os.path.join(output_dir, f"{location}_GT_2020_1_0.shp"), "Demolished buildings", crs)

    # 1:N 및 N:1 매칭 처리
    one_to_n = []
    n_to_one = []

    # 1:N 매칭 처리
    for idx, row_2020 in gdf_2020.iterrows():
        intersecting_2022 = gdf_2022[gdf_2022.intersects(row_2020['geometry'])]
        if len(intersecting_2022) > 1:
            one_to_n.append(intersecting_2022)
            gdf_2022 = gdf_2022.drop(intersecting_2022.index)

    if one_to_n:
        one_to_n_gdf = pd.concat(one_to_n)
        save_gdf(one_to_n_gdf, os.path.join(output_dir, f"{location}_GT_2020_2022_1_N.shp"), "1:N matches", crs)

    # N:1 매칭 처리
    for idx, row_2022 in gdf_2022.iterrows():
        intersecting_2020 = gdf_2020[gdf_2020.intersects(row_2022['geometry'])]
        if len(intersecting_2020) > 1:
            n_to_one.append(row_2022)
            gdf_2020 = gdf_2020.drop(intersecting_2020.index)

    if n_to_one:
        n_to_one_gdf = gpd.GeoDataFrame(n_to_one, columns=gdf_2022.columns, crs=crs).reset_index(drop=True)
        save_gdf(n_to_one_gdf, os.path.join(output_dir, f"{location}_GT_2020_2022_N_1.shp"), "N:1 matches", crs)

    # 1:1 매칭 처리
    same_buildings = []
    changed_buildings = []

    for idx, row_2020 in gdf_2020.iterrows():
        intersecting_2022 = gdf_2022[gdf_2022.intersects(row_2020['geometry'])]

        if len(intersecting_2022) == 1:
            row_2022 = intersecting_2022.iloc[0]
            symmetric_area = calculate_symmetric_area(row_2020['geometry'], row_2022['geometry'])

            if symmetric_area <= 1:  # 대칭 차집합 면적이 1m² 이하인 경우
                row_2022_cleaned = row_2022.drop(labels=['Sym_Area', 'Chg_Rate'], errors='ignore')
                same_buildings.append(row_2022_cleaned)
            else:  # 대칭 차집합 면적이 1m²를 초과하는 경우
                union_area = calculate_union_area(row_2020['geometry'], row_2022['geometry'])
                change_rate = (symmetric_area / union_area) * 100

                # gdf_2022의 원본에 안전하게 값 할당
                gdf_2022.at[row_2022.name, 'Sym_Area'] = round(symmetric_area, 2)
                gdf_2022.at[row_2022.name, 'Chg_Rate'] = round(change_rate, 2)

                changed_buildings.append(gdf_2022.loc[row_2022.name])  # 원본에서 해당 row 추가

    # 동일 건물 저장
    if same_buildings:
        same_buildings_gdf = gpd.GeoDataFrame(same_buildings, columns=gdf_2022.columns.drop(['Sym_Area', 'Chg_Rate'], errors='ignore'), crs=crs)
        save_gdf(same_buildings_gdf, os.path.join(output_dir, f"{location}_GT_2022_1_1.shp"), "Same buildings", crs)

    # 변경된 건물 저장
    if changed_buildings:
        changed_buildings_gdf = gpd.GeoDataFrame(changed_buildings, columns=gdf_2022.columns, crs=crs)
        save_gdf(changed_buildings_gdf, os.path.join(output_dir, f"{location}_GT_2020_2022_1_1_Diff.shp"), "Changed buildings", crs)


# 메인 워크플로우
if __name__ == "__main__":
    base_path = "E:/01. 업무/02. 서울시립대학교/02. 연구과제/03. Workflow/02. Ground_Truth/04. Building_GT"
    output_path = "03. Building_CD_GT/{location}"

    # 여러 지역을 리스트로 정의
    locations = ["Jungnang-gu", "Mapo-gu", "Seocho-gu", "Songpa-gu", "Yangcheon-gu", "Gangseo-gu", "Yeongdeungpo-gu", "Gangnam-gu"]

    # 각 지역별로 처리
    for location in locations:
        # 경로 설정
        gt_2020_path = os.path.join(base_path,
                                    f"02. Building_Seg_GT_Post-process/{location}/2020/{location}_GT_2020.shp")
        gt_2022_path = os.path.join(base_path,
                                    f"02. Building_Seg_GT_Post-process/{location}/2022/{location}_GT_2022.shp")
        output_dir = os.path.join(base_path, output_path.format(location=location))

        # 출력 디렉토리가 존재하지 않으면 생성
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 2020년 및 2022년 셰이프 파일 전처리
        gdf_2020 = preprocess_shapefile(gt_2020_path, "2020")
        gdf_2022 = preprocess_shapefile(gt_2022_path, "2022")

        # 2020년 좌표계로 통일
        crs_2020 = gdf_2020.crs

        # 객체 매칭 실행
        object_matching(gdf_2020, gdf_2022, output_dir, location, crs_2020)