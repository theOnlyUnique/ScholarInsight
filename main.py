import csv
import json
from collections import Counter

import requests
from datetime import datetime
from data.data import mentor_url
from typing import List, Dict, Optional
headers = {
   'User-Agent': 'Apifox/1.0.0 (https://apifox.com)',
   'Accept': '*/*',
   'Host': 'orcid.org',
   'Connection': 'keep-alive',
   'Cookie': 'AWSELB=CBD1D7FF1216388FA48838CBCA4774FD22800B8FB548A40EF92BB0994D5B77A8410307CDEAE0987F26953880E03BEBC61E2D483454FC30309233403CE21DC641E9CE0FEC59; AWSELBCORS=CBD1D7FF1216388FA48838CBCA4774FD22800B8FB548A40EF92BB0994D5B77A8410307CDEAE0987F26953880E03BEBC61E2D483454FC30309233403CE21DC641E9CE0FEC59',
   'Referer': mentor_url
}
text = requests.get(mentor_url,headers=headers)

data = text.json()

def clean_orcid_works(data: Dict) -> List[Dict]:
    """
    清洗ORCID返回的works数据，提取关键信息。

    Args:
        data: ORCID API返回的JSON数据（已解析为字典）。

    Returns:
        包含所有清洗后work信息的列表，每个work是一个字典。
    """
    cleaned_works = []

    # 遍历每个group
    for group in data.get("groups", []):
        for work in group.get("works", []):
            # 提取基本信息
            work_type = work.get("workType", {}).get("value", "unknown")
            title = work.get("title", {}).get("value", "No title available")
            access_url = _extract_doi(work)

            # 处理日期字段
            pub_date = _parse_date(work.get("publicationDate"))
            # pub_date = work.get("publicationDate")
            created_date = _parse_date(work.get("createdDate"))
            modified_date = _parse_date(work.get("lastModified"))

            # 提取作者列表
            authors = _extract_authors(work)

            # 构建清洗后的work数据
            cleaned_work = {
                "type": work_type,
                "title": title,
                "access_url": access_url,
                "publication_date": pub_date,
                "created_date": created_date,
                "last_modified": modified_date,
                "authors": authors,
                "journal": work.get("journalTitle", {}).get("value", " "),
                "put_code": work.get("putCode", {}).get("value", " "),
                "source": work.get("sourceName", " ")
            }
            cleaned_works.append(cleaned_work)
    return cleaned_works

def _extract_doi(work: Dict) -> Optional[str]:
    """从work中提取DOI（优先从normalizedUrl获取）"""
    # for ext_id in work.get("workExternalIdentifiers", []):
    #     if ext_id.get("externalIdentifierType", {}).get("value") == "doi":
    #         return ext_id.get("normalizedUrl", {}).get("value") or ext_id.get("url", {}).get("value")
    # 获取最后一个元素的链接 实在不行 获取url字典的链接
    work_list = work.get("workExternalIdentifiers", [])
    if len(work_list):
        # print("ok")
        try:
            return work_list[len(work_list) - 1].get("normalizedUrl",{}).get("value"," ") or work_list[len(work_list) - 1].get("url", {}).get("value"," ")
        except Exception as e:
            print("ERROR:",work_list[len(work_list) - 1])
    return " "

def _extract_authors(work: Dict) -> List[str]:
    """提取作者姓名列表"""
    authors = []
    for contributor in work.get("contributorsGroupedByOrcid", []):
        if "creditName" in contributor and "content" in contributor["creditName"]:
            authors.append(contributor["creditName"]["content"])
    return authors if authors else ["No authors listed"]

def _parse_date(date_dict: Optional[Dict]) -> Optional[str]:
    """将ORCID的日期字典格式化为YYYY-MM-DD字符串"""
    if not date_dict:
        return None

    year = date_dict.get("year")
    # month = date_dict.get("month", "01").zfill(2)  # 默认1月
    # day = date_dict.get("day", "01").zfill(2)  # 默认1日
    month = date_dict.get("month")
    day = date_dict.get("day")
    month = "-" + str(month).zfill(2) if month is not None else ""
    day = "-" + str(day).zfill(2) if day is not None else ""

    if not year:
        return None

    try:
        return f"{year}{month}{day}"
    except:
        return None

def save_to_json(data: List[Dict], filename: str) -> None:
    """保存清洗后的数据到JSON文件"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def print_sample_data(cleaned_data: List[Dict], sample_size: int = 3) -> None:
    """打印示例数据"""
    print("===== 清洗后的前{}条数据 =====".format(sample_size))
    for i, work in enumerate(cleaned_data[:sample_size], 1):
        print(f"#{i}: {work['title']} ({work['type']})")
        print(f"    DOI: {work['access_url']}")
        print(f"    发布日期: {work['publication_date']}")
        print(f"    最后修改: {work['last_modified']}")
        print(f"    作者: {', '.join(work['authors'][:3])}等{len(work['authors'])}人\n")


def count_journal_types(cleaned_works):
    '''统计cleaned_works当中又多少种类的journal'''
    # 提取所有 journal 名称
    journals = [work["journal"].strip() for work in cleaned_works if work["journal"]]

    # 使用 Counter 统计每种 journal 的数量
    journal_counts = Counter(journals)

    # 返回统计结果（按期刊名排序）
    return sorted(journal_counts.items(), key=lambda x: x[1], reverse=True)
def save_to_csv(data: List[Dict], filename: str) -> None:
    """保存清洗后的数据到CSV文件"""
    if not data:
        print("警告：没有数据可保存")
        return
    # 定义CSV文件头
    fieldnames = [
        'type', 'title', 'access_url', 'publication_date',
        'created_date', 'last_modified', 'authors',
        'journal', 'put_code', 'source'
    ]
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for work in data:
                # 处理authors列表为字符串
                work_copy = work.copy()
                work_copy['authors'] = ', '.join(work['authors'])
                writer.writerow(work_copy)
        print(f"成功保存数据到 {filename}")
    except Exception as e:
        print(f"保存CSV文件时出错: {str(e)}")

if __name__ == "__main__":
    cleaned_data = clean_orcid_works(data)
    # 打印示例数据
    print_sample_data(cleaned_data)
    # 保存完整数据
    # save_to_json(cleaned_data, "data/orcid_works_cleaned.json")
    # print(f"已保存清洗后的数据到 orcid_works_cleaned.json (共 {len(cleaned_data)} 条)")
    # 新增：保存为CSV
    save_to_csv(cleaned_data, "data/orcid_works_cleaned.csv")
    print(f"已保存清洗后的数据到 'data/orcid_works_cleaned.csv' (共 {len(cleaned_data)} 条)")
    journal_stats = count_journal_types(cleaned_data)
    for journal, count in journal_stats:
        print(f"{count}：{journal}")