import os
import geopandas as gpd
import pandas as pd

def road_seg_gt_merge_clip(road_map_files, grid_file, output_file):

    # 수치지도 파일 로드 및 병합
    road_gdfs = [gpd.read_file(file).to_crs(epsg=5186) for file in road_map_files]
    merged_road_gdf = pd.concat(road_gdfs, ignore_index=True)
    merged_road_gdf = gpd.GeoDataFrame(merged_road_gdf, crs=road_gdfs[0].crs)

    # 대상지역 grid 파일 로드
    grid_gdf = gpd.read_file(grid_file).to_crs(epsg=5186)

    # 병합된 수치지도를 grid 범위로 클립
    clipped_road_gdf = gpd.clip(merged_road_gdf, grid_gdf)

    # 결과 저장 (EUC-KR 인코딩)
    clipped_road_gdf.to_file(output_file, encoding='EUC-KR')