"""
读取相对路径“doc/phone”的文件内容，并将数据导入到数据库的 customers 表中。
写入的内容为：
1、电话号码，字段名为 phone。
2、标签，字段名为 tag，默认为 "second_import"。
"""

import sys
import os

# 动态添加项目根目录到 sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)


def import_phone():
    import time
    from app.core.db import get_session_factory
    from app.models.customer import Customer

    phone_file_path = os.path.join(project_root, "doc", "phone")

    session_factory = get_session_factory()
    with session_factory() as session:
        with open(phone_file_path, "r") as f:
            batch = []
            for line in f:
                phone = line.strip()
                if not phone:  # 跳过空行
                    continue

                # 检查 phone 是否已存在
                exists = session.query(Customer).filter_by(phone=phone).first()
                if exists:
                    continue

                # 添加到批处理
                batch.append(Customer(phone=phone, tag="second_import"))

                # 每200条记录插入一次
                if len(batch) >= 200:
                    session.bulk_save_objects(batch)
                    session.commit()
                    batch.clear()
                    time.sleep(0.1)  # 缓解数据库压力

            # 插入剩余的记录
            if batch:
                session.bulk_save_objects(batch)
                session.commit()


if __name__ == "__main__":
    import_phone()

