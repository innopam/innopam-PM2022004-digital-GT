# Creating road segmentation ground truth

**Step1. Export ‘Digital_Map_v1.0’**
- Export ‘Digital_Map_v1.0’ with property information('도면층', 'X1', 'Y1')
    - DXF → SHP
- AutoCAD의 기능을 Python으로 제어하는 데 한계가 있음. 향후 AutoLISP 고려
**Step2. Add property information**
- Input: Digital_Map_v1.0.shp, Digital_Map_v2.0.shp
- Process (Function)
    - ‘road_seg_gt’ 정의: 수치지도 v1.0과 v2.0을 사용하여 'intersects'와 'crosses' 조건으로 두 번의 공간 조인을 수행하고, 결과를 새로운 shapefile로 저장하는 함수
        - 'intersects' 조건: 두 객체가 겹치거나 만나는 모든 경우를 포함
        - 'crosses’ 조건: 객체들이 서로의 경계를 넘어가며 교차하는 특정한 상호작용을 강조
- Output: Road_Seg_GT_’도엽번호’.shp
- (현재 sample에는 Step2의 output 부터 존재)
**Step3. Target region Merge and Clip**
- Input: Road_Seg_GT_’도엽번호’.shp N개, ‘대상지역’_grid.shp 1개
- Process (Function)
- Output: Road_Seg_GT_’대상지역’.shp