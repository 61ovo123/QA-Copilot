import pandas as pd
import json

def export_cases(content):

    try:

        cases = json.loads(content)

        df = pd.DataFrame(cases)

        df.columns = [
            "测试编号",
            "测试场景",
            "预期结果"
        ]

        file_name = "test_cases.xlsx"

        df.to_excel(
            file_name,
            index=False
        )

        return file_name

    except Exception as e:

        print("导出失败：", e)
        return None