from Road_Seg_GT import road_seg_gt
from Road_Seg_GT_MergeClip import road_seg_gt_merge_clip

"""
Parameters:
- input_file_v1 (str): 도로 수치지도 v1.0 (라인 레이어) 파일 경로
- input_file_v2 (str): 도로 수치지도 v2.0 (폴리곤 레이어) 파일 경로
- output_file (str): 결과 shapefile을 저장할 파일 경로
"""

if __name__ == "__main__":
    base_path = "E:/01. 업무/02. 서울시립대학교/02. 연구과제/03. Workflow/06. Road_Change_Detection/02. Evaluate and analyze road segmentation/"

    # input_v1 = f"{base_path}02. Digital_Map_v1.0.shp/2022/GT1_37709005.shp"
    # input_v2 = f"{base_path}03. Digital_Map_v2.0.shp/2022/(B010)수치지도_37709005_2022_00000348196593/N3A_A0010000.shp"
    # output = f"{base_path}04. Road_Seg_GT/2022/Road_Seg_GT_37709005.shp"
    #
    # road_seg_gt(input_v1, input_v2, output)

    road_seg_gt_outputs = [
        f"{base_path}04. Road_Seg_GT/2022/Road_Seg_GT_37709004.shp",
        f"{base_path}04. Road_Seg_GT/2022/Road_Seg_GT_37709005.shp"
    ]
    grid_file = f"{base_path}04. Road_Seg_GT/suseo_grid.shp"
    output_file = f"{base_path}04. Road_Seg_GT/2022/Road_Seg_GT_Suseo.shp"

    road_seg_gt_merge_clip(road_seg_gt_outputs, grid_file, output_file)