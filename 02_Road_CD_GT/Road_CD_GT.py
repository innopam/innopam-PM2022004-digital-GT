import os
import argparse
import subprocess
from time import time
from tqdm import tqdm

import geopandas as gpd


def Usage():
    print(
        """
Usage: GT.py 
                (required)
                --shp_dir1      shp파일이 담긴 도엽폴더들의 경로(before)
                --shp_dir2      shp파일이 담긴 도엽폴더들의 경로(after)
                --out_dir       최종 결과물(filtered_diff.gpkg)이 저장될 경로. 경로에 "(" 혹은 ")"가 없도록 할 것
                --type          수치지형도 종류(예: building, road)
                --thres         ratio 기준으로 필터링할 임계값. 소수 첫째자리까지 입력할 것(예: 1.7)
            
                (optional)
                --thres_end     ratio 기준으로 필터링할 임계값 중 가장 큰 값. 소수 첫째자리까지 입력할 것
                                thres값 기준, 0.1씩 증가하며 결과물을 저장(예: 2.0)
                                (예: thres 1.7, thres_end 2.0 지정시 1.7, 1.8, 1.9, 2.0 생성)
"""
    )


def make_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--shp_dir1",
        type=str,
        required=True,
        help="shp파일이 담긴 도엽폴더들의 경로(before)",
    )
    parser.add_argument(
        "--shp_dir2",
        type=str,
        required=True,
        help="shp파일이 담긴 도엽폴더들의 경로(after)",
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        required=True,
        help='최종 결과물(filtered_diff.gpkg)이 저장될 경로. 경로에 "(" 혹은 ")"가 없도록 할 것',
    )
    parser.add_argument(
        "--type", type=str, required=True, help="수치지형도 종류(예: building, road)"
    )
    parser.add_argument(
        "--thres",
        type=float,
        required=True,
        help="ratio 기준으로 필터링할 임계값(예: 1.7)",
    )
    parser.add_argument(
        "--thres_end",
        type=float,
        help="(optional) ratio 기준으로 필터링할 임계값 중 가장 큰 값. thres값 기준으로 0.1씩 증가하며 결과물을 저장(예: 2.0)",
    )

    return parser


# 1. shp -> gpkg
def shp_to_gpkg(shp, gpkg):
    layer = os.path.basename(shp).split(".")[0]
    subprocess.run(args=["ogr2ogr", "-f", "GPKG", "-nlt", "MULTIPOLYGON", gpkg, shp])


# 2. Merge gpkgs
def merge(dir_gpkg, merged_gpkg):
    subprocess.run(
        "ogrmerge.py -single -f GPKG -o %s %s -nln merged"
        % (merged_gpkg, os.path.join(dir_gpkg, "*.gpkg")),
        shell=True,
    )
    return merged_gpkg


# 3. Make geometry valid
def valid_geom(gpkg, valid_gpkg):
    subprocess.run(
        "ogr2ogr -nlt MULTIPOLYGON %s %s -dialect sqlite -sql "
        '"SELECT ST_Buffer(geom,0) FROM merged" '
        "-f GPKG" % (valid_gpkg, gpkg),
        shell=True,
    )
    return valid_gpkg


# 4. Symmetric diff w/o dissolve
def make_symm_diff(before, after, out_diff):
    tmp = out_diff.replace(".", "_tmp.")
    subprocess.run(
        "ogr_layer_algebra.py SymDifference -input_ds %s -method_ds %s -output_ds %s -output_lyr output -f GPKG -nlt MultiPolygon"
        % (before, after, tmp),
        shell=True,
    )

    # Use only MultiPolygon or Polygon
    convert(tmp, out_diff)
    df = gpd.read_file(out_diff)
    counts = len(df)

    return counts


# 5. Filter diff
def filter_diff(gpkg, out_gpkg, *thres):
    df = gpd.read_file(gpkg)
    # df = df.explode(ignore_index=True)
    tmp_path = out_gpkg.replace(".", "_tmp.")

    df["buffer_1.5_area"] = df["geometry"].buffer(1.5).area
    df["buffer_3.0_area"] = df["geometry"].buffer(3.0).area
    df["ratio"] = df["buffer_3.0_area"] / df["buffer_1.5_area"]

    df.to_file(tmp_path, layer="output")
    convert(tmp_path, out_gpkg)
    os.remove(gpkg)

    if len(thres) == 1:
        thres = thres[0]
        new_df = df[df["ratio"] <= thres]
        new_df.to_file(tmp_path.replace(".", "_" + str(thres) + "."), layer="output")
        convert(
            tmp_path.replace(".", "_" + str(thres) + "."),
            out_gpkg.replace(".", "_" + str(thres) + "."),
        )

    elif len(thres) == 2:
        thres_li = []
        interval = 0.1
        counts = int(round((thres[1] - thres[0]) / interval))
        for i in range(counts + 1):
            thres_li.append(thres[0] + interval * i)

        for thres in thres_li:
            thres = round(thres, 1)
            new_df = df[df["ratio"] <= thres]
            new_df.to_file(
                tmp_path.replace(".", "_" + str(thres) + "."), layer="output"
            )
            convert(
                tmp_path.replace(".", "_" + str(thres) + "."),
                out_gpkg.replace(".", "_" + str(thres) + "."),
            )


# 6. Convert LineString, GeometryCollection -> MultiPolygon
def convert(gpkg, out_gpkg):
    subprocess.run(
        "ogr2ogr -nlt MULTIPOLYGON %s %s output" % (out_gpkg, gpkg), shell=True
    )
    os.remove(gpkg)


if __name__ == "__main__":
    start = time()
    args = make_args().parse_args()
    shp_dir1 = args.shp_dir1
    shp_dir2 = args.shp_dir2
    out_dir = args.out_dir
    data_type = args.type
    thres = args.thres
    thres_end = args.thres_end

    if (
        shp_dir1 is None
        or shp_dir2 is None
        or out_dir is None
        or data_type is None
        or thres is None
    ):
        Usage()

    elif data_type not in ["road", "building"]:
        raise Exception("'type' should be 'road' or 'building'.")

    elif (thres_end != None) and thres >= thres_end:
        raise Exception("'thres_end' should be larger than 'thres'.")

    else:
        # output 폴더 생성
        before_gpkg = os.path.join(out_dir, "before_gpkg")
        after_gpkg = os.path.join(out_dir, "after_gpkg")
        for folder in [out_dir, before_gpkg, after_gpkg]:
            os.makedirs(folder, exist_ok=True)

        # 1. shp file -> gpkg
        # 각 folder 이름: (B010)수치지도_37705072_2019_00000019663 등을 권장
        print("1. shp file -> gpkg")
        for dir in [shp_dir1, shp_dir2]:
            folder_li = sorted(os.listdir(dir))
            folder_li = [i for i in folder_li if "." not in i]  # 폴더만(.xml 제외)

            for i, folder in enumerate(tqdm(folder_li)):
                file_li = os.listdir(os.path.join(dir, folder))
                try:  # 도엽번호와 일치: 37705072
                    index_name = str(folder.split("_")[1])
                except:  # 폴더 이름 미존재시 -> 임의로 부여
                    index_name = i + 1

                if data_type == "road":
                    # A0010000.shp, N3A_A0010000.shp 등
                    # N3L_A0010000.shp는 도로가 아님
                    shp_name = [
                        i
                        for i in file_li
                        if (i.endswith("A0010000.shp")) and i != "N3L_A0010000.shp"
                    ][0]

                elif data_type == "building":
                    # B0010000.shp, N3A_B0010000.shp 등
                    shp_name = [
                        i
                        for i in file_li
                        if (i.endswith("B0010000.shp")) and i != "N3L_B0010000.shp"
                    ][0]

                shp = os.path.join(dir, folder, shp_name)

                if dir == shp_dir1:
                    shp_to_gpkg(shp, os.path.join(before_gpkg, index_name + ".gpkg"))
                else:
                    shp_to_gpkg(shp, os.path.join(after_gpkg, index_name + ".gpkg"))

        # 2. merge gpkgs
        print("2. merge gpkgs")
        before = merge(before_gpkg, os.path.join(out_dir, "before_merged.gpkg"))
        after = merge(after_gpkg, os.path.join(out_dir, "after_merged.gpkg"))

        # 3. make geometry valid
        print("3. make geometry valid")
        before = valid_geom(before, os.path.join(out_dir, "before_merged_valid.gpkg"))
        after = valid_geom(after, os.path.join(out_dir, "after_merged_valid.gpkg"))

        # 4. symmetric diff
        print("4. symmetric diff")
        diff = os.path.join(out_dir, "diff.gpkg")
        diff_counts = make_symm_diff(before, after, diff)

        # 5. filter diff
        print("5. filter diff")
        filtered = os.path.join(out_dir, "filtered_diff.gpkg")
        if thres_end == None:
            filter_diff(diff, filtered, thres)
        else:
            filter_diff(diff, filtered, thres, thres_end)

        print(f"Make GT Ended. Total time eplased: {time()-start}")
        print(f"Saved output to {filtered}")
